from __future__ import annotations

import re
import zipfile
from io import BytesIO

import pandas as pd
import streamlit as st


# ============================================================
# SAMPLE DATA
# ============================================================

ROW_COUNT = 240

MONTHS = [
    "2026-06",
    "2026-07",
    "2026-08",
]


@st.cache_data
def create_sample_data() -> pd.DataFrame:
    """Create fictional sample data."""

    warehouses = [
        "WH-KL",
        "WH-PEN",
        "WH-JOH",
        "WH-SAB",
    ]

    outlets = [
        "Outlet KLCC",
        "Outlet Shah Alam",
        "Outlet Penang",
        "Outlet Johor",
        "Outlet Kota Kinabalu",
        "Outlet Ipoh",
        "Outlet Melaka",
        "Outlet Kuching",
    ]

    suppliers = [
        "BrightMart Supply",
        "Nusantara Goods",
        "Everday Essentials",
        "Pacific Wholesale",
        "Sunrise Distribution",
    ]

    department_classes = {
        "Grocery": [
            "Pantry",
            "Frozen",
            "Staples",
        ],
        "Beverages": [
            "Coffee",
            "Tea",
            "Juice",
            "Water",
        ],
        "Household": [
            "Cleaning",
            "Laundry",
            "Kitchen",
        ],
        "Personal Care": [
            "Skincare",
            "Haircare",
            "Oral Care",
        ],
        "Snacks": [
            "Chips",
            "Biscuits",
            "Confectionery",
        ],
    }

    uoms = [
        "PCS",
        "BOX",
        "PACK",
        "BOTTLE",
    ]

    products = []

    sku_number = 1001

    for department, classes in department_classes.items():

        for product_class in classes:

            for product_number in range(1, 3):

                products.append(
                    {
                        "DEPT": department,
                        "CLASS": product_class,
                        "SKU": f"SKU-{sku_number}",
                        "UOM": uoms[
                            (sku_number + product_number)
                            % len(uoms)
                        ],
                        "UNIT_AMT": (
                            4.5
                            + (
                                (sku_number * 7) % 320
                            ) / 10
                        ),
                    }
                )

                sku_number += 1

    rows = []

    for month_index, month in enumerate(MONTHS):

        for row_number in range(ROW_COUNT):

            product = products[
                (row_number * 7 + 2)
                % len(products)
            ]

            quantity = (
                2
                + (
                    row_number * 5
                    + month_index * 3
                )
                % 24
            )

            rows.append(
                {
                    "MONTH": month,
                    "WHOUSE": warehouses[
                        (
                            row_number * 3
                            + month_index
                            + 1
                        )
                        % len(warehouses)
                    ],
                    "OUTLET": outlets[
                        (
                            row_number * 5
                            + month_index
                            + 2
                        )
                        % len(outlets)
                    ],
                    "SUPPLIER": suppliers[
                        (
                            row_number * 2
                            + month_index
                            + 1
                        )
                        % len(suppliers)
                    ],
                    "DEPT": product["DEPT"],
                    "CLASS": product["CLASS"],
                    "SKU": product["SKU"],
                    "UOM": product["UOM"],
                    "QTY": quantity,
                    "AMT": round(
                        quantity
                        * float(
                            product["UNIT_AMT"]
                        ),
                        2,
                    ),
                }
            )

    return pd.DataFrame(rows)


# ============================================================
# HEADER CLEANING
# ============================================================

def clean_column_name(column) -> str:
    """
    Clean Excel column names.

    Handles:
    - tabs
    - multiple spaces
    - non-breaking spaces
    - line breaks
    - accidental leading/trailing spaces
    """

    text = str(column)

    text = (
        text
        .replace("\xa0", " ")
        .replace("\t", " ")
        .replace("\r", " ")
        .replace("\n", " ")
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# FIND MONTH COLUMN
# ============================================================

def find_month_columns(columns):
    """
    Find monthly QTY and AMT columns.

    Supports:

        ~2026-01 QTY
        ~2026-01 AMT

    and also:

        2026-01 QTY
        2026-01 AMT

    Spaces/tabs are tolerated.
    """

    qty_column = None
    amt_column = None

    qty_month = None
    amt_month = None

    for column in columns:

        cleaned = clean_column_name(column)

        # --------------------------------------------
        # QTY
        # --------------------------------------------

        qty_match = re.search(
            r"~?\s*(\d{4}-\d{2})\s+QTY\s*$",
            cleaned,
            re.IGNORECASE,
        )

        if qty_match:

            qty_column = column

            qty_month = (
                qty_match.group(1)
            )

        # --------------------------------------------
        # AMT
        # --------------------------------------------

        amt_match = re.search(
            r"~?\s*(\d{4}-\d{2})\s+AMT\s*$",
            cleaned,
            re.IGNORECASE,
        )

        if amt_match:

            amt_column = column

            amt_month = (
                amt_match.group(1)
            )

    if qty_column is None:

        raise ValueError(
            "Could not find a monthly QTY column. "
            f"Columns found: {list(columns)}"
        )

    if amt_column is None:

        raise ValueError(
            "Could not find a monthly AMT column. "
            f"Columns found: {list(columns)}"
        )

    if qty_month != amt_month:

        raise ValueError(
            "QTY and AMT months do not match: "
            f"{qty_month} vs {amt_month}"
        )

    return (
        qty_column,
        amt_column,
        qty_month,
    )


# ============================================================
# READ MONTH ZIP
# ============================================================

def read_month_zip(uploaded_zip) -> pd.DataFrame:
    """
    Read a monthly ZIP containing Excel files.

    Supports both:

    OLD FORMAT
    ----------
    WH-KL
    Outlet KLCC
    BrightMart Supply
    Grocery
    Staples
    SKU-1001
    PCS
    ~2026-04 QTY
    ~2026-04 AMT

    NEW FORMAT
    ----------
    W02
    1001 - Central Outlet
    1101 - Alpha Supply
    201 - Grocery
    201001 - Infant Milk
    111001453-20-B 0016 LACTOGEN ...
    6
    ~2026-01 QTY
    ~2026-01 AMT
    """

    all_data = []

    zip_filename = uploaded_zip.name

    # ========================================================
    # OPEN ZIP
    # ========================================================

    try:

        with zipfile.ZipFile(
            uploaded_zip
        ) as zip_file:

            excel_files = [
                name
                for name in zip_file.namelist()
                if (
                    name.lower().endswith(
                        (
                            ".xlsx",
                            ".xls",
                        )
                    )
                    and not name.startswith(
                        "__MACOSX"
                    )
                    and not name.startswith(".")
                )
            ]

            if not excel_files:

                raise ValueError(
                    f"No Excel files found inside "
                    f"{zip_filename}"
                )

            # =================================================
            # EACH EXCEL FILE
            # =================================================

            for excel_filename in excel_files:

                with zip_file.open(
                    excel_filename
                ) as excel_file:

                    file_bytes = excel_file.read()

                # ---------------------------------------------
                # Read Excel
                # ---------------------------------------------

                data = pd.read_excel(
                    BytesIO(file_bytes),
                    dtype=str,
                    header=0,
                )

                # ---------------------------------------------
                # Clean ALL headers
                # ---------------------------------------------

                original_columns = list(
                    data.columns
                )

                cleaned_columns = [
                    clean_column_name(
                        column
                    )
                    for column in data.columns
                ]

                data.columns = cleaned_columns

                # ---------------------------------------------
                # Find month columns
                # ---------------------------------------------

                (
                    qty_column,
                    amt_column,
                    month,
                ) = find_month_columns(
                    data.columns
                )

                # =================================================
                # REQUIRED BUSINESS COLUMNS
                # =================================================

                required_columns = [
                    "WHOUSE",
                    "OUTLET",
                    "SUPPLIER",
                    "DEPT",
                    "CLASS",
                    "SKU",
                    "UOM",
                ]

                # Case-insensitive lookup
                column_lookup = {
                    clean_column_name(
                        column
                    ).upper(): column
                    for column in data.columns
                }

                missing_columns = []

                for required in required_columns:

                    if (
                        required.upper()
                        not in column_lookup
                    ):

                        missing_columns.append(
                            required
                        )

                if missing_columns:

                    raise ValueError(
                        f"Missing required columns "
                        f"{missing_columns} in "
                        f"{excel_filename}. "
                        f"Columns found: "
                        f"{list(data.columns)}"
                    )

                # =================================================
                # RENAME BUSINESS COLUMNS
                # =================================================

                rename_map = {}

                for required in required_columns:

                    actual_column = (
                        column_lookup[
                            required.upper()
                        ]
                    )

                    rename_map[
                        actual_column
                    ] = required

                rename_map[
                    qty_column
                ] = "QTY"

                rename_map[
                    amt_column
                ] = "AMT"

                data = data.rename(
                    columns=rename_map
                )

                # =================================================
                # KEEP ONLY NEEDED COLUMNS
                # =================================================

                data = data[
                    [
                        "WHOUSE",
                        "OUTLET",
                        "SUPPLIER",
                        "DEPT",
                        "CLASS",
                        "SKU",
                        "UOM",
                        "QTY",
                        "AMT",
                    ]
                ].copy()

                # =================================================
                # MONTH
                # =================================================

                data["MONTH"] = month

                # =================================================
                # CLEAN TEXT DATA
                # =================================================

                text_columns = [
                    "MONTH",
                    "WHOUSE",
                    "OUTLET",
                    "SUPPLIER",
                    "DEPT",
                    "CLASS",
                    "SKU",
                    "UOM",
                ]

                for column in text_columns:

                    data[column] = (
                        data[column]
                        .fillna("")
                        .astype(str)
                        .str.replace(
                            "\xa0",
                            " ",
                            regex=False,
                        )
                        .str.replace(
                            "\t",
                            " ",
                            regex=False,
                        )
                        .str.replace(
                            r"\s+",
                            " ",
                            regex=True,
                        )
                        .str.strip()
                    )

                # =================================================
                # NUMERIC QTY
                # =================================================

                data["QTY"] = (
                    data["QTY"]
                    .fillna("")
                    .astype(str)
                    .str.replace(
                        ",",
                        "",
                        regex=False,
                    )
                    .str.strip()
                )

                data["QTY"] = pd.to_numeric(
                    data["QTY"],
                    errors="coerce",
                ).fillna(0)

                # =================================================
                # NUMERIC AMT
                # =================================================

                data["AMT"] = (
                    data["AMT"]
                    .fillna("")
                    .astype(str)
                    .str.replace(
                        ",",
                        "",
                        regex=False,
                    )
                    .str.replace(
                        "RM",
                        "",
                        regex=False,
                        case=False,
                    )
                    .str.strip()
                )

                data["AMT"] = pd.to_numeric(
                    data["AMT"],
                    errors="coerce",
                ).fillna(0)

                # =================================================
                # REMOVE EMPTY SKU
                # =================================================

                data = data[
                    data["SKU"].ne("")
                ].copy()

                # =================================================
                # FINAL COLUMN ORDER
                # =================================================

                data = data[
                    [
                        "MONTH",
                        "WHOUSE",
                        "OUTLET",
                        "SUPPLIER",
                        "DEPT",
                        "CLASS",
                        "SKU",
                        "UOM",
                        "QTY",
                        "AMT",
                    ]
                ]

                all_data.append(data)

    except zipfile.BadZipFile as error:

        raise ValueError(
            f"{zip_filename} is not a valid ZIP file."
        ) from error

    # ========================================================
    # COMBINE
    # ========================================================

    if not all_data:

        raise ValueError(
            f"No usable Excel data found inside "
            f"{zip_filename}"
        )

    result = pd.concat(
        all_data,
        ignore_index=True,
    )

    return result


# ============================================================
# RINGGIT
# ============================================================

def ringgit(amount: float) -> str:

    return f"RM {amount:,.2f}"
