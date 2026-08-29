from __future__ import annotations

import re
import zipfile
from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from data_utils import create_sample_data, read_month_zip, ringgit


APP_TITLE = "Retail Sales Dashboard"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📊",
    layout="wide",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def format_month(month: str) -> str:
    """
    Convert YYYY-MM into a friendlier display format.

    Example:
        2026-07 -> Jul 2026
    """
    try:
        return pd.to_datetime(month, format="%Y-%m").strftime("%b %Y")
    except Exception:
        return str(month)


def format_change(amount: float) -> str:
    """
    Format a currency change value.
    """
    if amount > 0:
        return f"+{ringgit(amount)}"
    return ringgit(amount)


def format_percentage(value: float | None) -> str:
    """
    Format percentage values.
    """
    if value is None or pd.isna(value):
        return "N/A"

    return f"{value:+.1f}%"


def create_empty_message() -> None:
    """
    Show a friendly message when filters return no data.
    """
    st.warning(
        "No rows match the current filters. "
        "Please select more values from the sidebar."
    )
    st.stop()


# ============================================================
# LOAD DATA
# ============================================================

def load_application_data() -> pd.DataFrame:
    """
    Load uploaded monthly ZIP files or fallback sample data.

    Expected structure:

        MD-042026.zip
            ├── MD-042026-111.xlsx
            ├── MD-042026-112.xlsx
            └── ...

        MD-052026.zip
            ├── MD-052026-111.xlsx
            └── ...

    The actual month is determined from the ZIP filename.
    """

    with st.sidebar:

        st.subheader("📁 Monthly Data")

        uploaded_files = st.file_uploader(
            "Upload monthly ZIP files",
            type=["zip"],
            accept_multiple_files=True,
            key="monthly_zip_uploader",
            help=(
                "Upload one ZIP file per month. "
                "Example: MR-072026.zip"
            ),
        )

        if uploaded_files:

            monthly_data: list[pd.DataFrame] = []
            uploaded_months: set[str] = set()

            # ====================================================
            # PROCESS EACH ZIP ONCE
            # ====================================================

            for uploaded_file in uploaded_files:

                try:

                    # ------------------------------------------------
                    # Read ZIP
                    # ------------------------------------------------

                    month_data = read_month_zip(
                        uploaded_file
                    )

                    # ------------------------------------------------
                    # Detect month
                    # ------------------------------------------------

                    if "MONTH" not in month_data.columns:

                        raise ValueError(
                            f"No MONTH column found in "
                            f"{uploaded_file.name}"
                        )

                    detected_months = (
                        month_data["MONTH"]
                        .dropna()
                        .astype(str)
                        .str.strip()
                        .unique()
                        .tolist()
                    )

                    if not detected_months:

                        raise ValueError(
                            f"No month detected in "
                            f"{uploaded_file.name}"
                        )

                    if len(detected_months) > 1:

                        raise ValueError(
                            f"Multiple months detected in "
                            f"{uploaded_file.name}: "
                            f"{detected_months}"
                        )

                    uploaded_month = detected_months[0]

                    # ------------------------------------------------
                    # DUPLICATE MONTH CHECK
                    # ------------------------------------------------

                    if uploaded_month in uploaded_months:

                        st.warning(
                            f"⚠️ {format_month(uploaded_month)} "
                            "was uploaded more than once. "
                            "Only one ZIP file per month is allowed."
                        )

                        continue

                    # ------------------------------------------------
                    # ACCEPT THIS MONTH
                    # ------------------------------------------------

                    monthly_data.append(
                        month_data
                    )

                    uploaded_months.add(
                        uploaded_month
                    )

                    # ------------------------------------------------
                    # SUCCESS MESSAGE
                    # ------------------------------------------------

                    st.success(
                        f"✅ {uploaded_file.name} — "
                        f"{format_month(uploaded_month)} — "
                        f"{len(month_data):,} rows"
                    )

                    # ------------------------------------------------
                    # PREVIEW
                    # ------------------------------------------------

                    with st.expander(
                        f"🔎 Preview imported data: "
                        f"{uploaded_file.name}"
                    ):

                        st.write(
                            "Detected columns:"
                        )

                        st.code(
                            ", ".join(
                                month_data.columns.tolist()
                            )
                        )

                        st.write(
                            "Detected month:"
                        )

                        st.write(
                            format_month(
                                uploaded_month
                            )
                        )

                        st.dataframe(
                            month_data.head(10),
                            use_container_width=True,
                            hide_index=True,
                        )

                except Exception as error:

                    st.error(
                        f"❌ Could not load "
                        f"{uploaded_file.name}: {error}"
                    )

            # ====================================================
            # COMBINE VALID MONTHS
            # ====================================================

            if monthly_data:

                data = pd.concat(
                    monthly_data,
                    ignore_index=True,
                )

            else:

                st.warning(
                    "No valid monthly files were loaded."
                )

                st.stop()

        else:

            # ====================================================
            # NO UPLOADS
            # ====================================================

            if "app_data" in st.session_state:

                data = st.session_state[
                    "app_data"
                ]

            else:

                data = create_sample_data()

    # ========================================================
    # STORE CURRENT DATASET
    # ========================================================

    st.session_state["app_data"] = data

    return data


# ============================================================
# SIDEBAR FILTERS
# ============================================================

def apply_sidebar_filters(
    data: pd.DataFrame,
) -> pd.DataFrame:

    # with st.sidebar:

    #     st.divider()

    #     st.subheader("🔎 Filters")

    #     st.caption(
    #         "These filters apply to the dashboard."
    #     )

    #     available_months = sorted(
    #         data["MONTH"]
    #         .dropna()
    #         .astype(str)
    #         .unique()
    #         .tolist()
    #     )

    #     # ----------------------------------------------------
    #     # Detect new dataset
    #     # ----------------------------------------------------

    #     dataset_signature = (
    #         tuple(available_months),
    #         len(data),
    #     )

    #     if (
    #         st.session_state.get("dataset_signature")
    #         != dataset_signature
    #     ):

    #         st.session_state["dataset_signature"] = (
    #             dataset_signature
    #         )

    #         st.session_state.pop(
    #             "selected_months",
    #             None,
    #         )

    #         st.session_state.pop(
    #             "selected_warehouses",
    #             None,
    #         )

    #         st.session_state.pop(
    #             "selected_outlets",
    #             None,
    #         )

    #         st.session_state.pop(
    #             "selected_suppliers",
    #             None,
    #         )

    #         st.session_state.pop(
    #             "selected_departments",
    #             None,
    #         )

    #         st.session_state.pop(
    #             "selected_classes",
    #             None,
    #         )

    #         st.session_state.pop(
    #             "selected_skus",
    #             None,
    #         )

    #         st.session_state["filter_widget_version"] = (
    #             st.session_state.get(
    #                 "filter_widget_version",
    #                 0,
    #             )
    #             + 1
    #         )

    #     filter_version = st.session_state.get(
    #         "filter_widget_version",
    #         0,
    #     )

    #     # ----------------------------------------------------
    #     # Month
    #     # ----------------------------------------------------

    #     selected_months = st.multiselect(
    #         "Month",
    #         available_months,
    #         default=available_months,
    #         format_func=format_month,
    #         key=f"selected_months_{filter_version}",
    #     )

    #     st.session_state["selected_months"] = (
    #         selected_months
    #     )

    #     # ----------------------------------------------------
    #     # Warehouse
    #     # ----------------------------------------------------

    #     warehouse_values = sorted(
    #         data["WHOUSE"]
    #         .dropna()
    #         .astype(str)
    #         .unique()
    #         .tolist()
    #     )

    #     selected_warehouses = st.multiselect(
    #         "Warehouse",
    #         warehouse_values,
    #         default=warehouse_values,
    #         key="selected_warehouses",
    #     )

    #     # ----------------------------------------------------
    #     # Outlet
    #     # ----------------------------------------------------

    #     outlet_values = sorted(
    #         data["OUTLET"]
    #         .dropna()
    #         .astype(str)
    #         .unique()
    #         .tolist()
    #     )

    #     selected_outlets = st.multiselect(
    #         "Outlet",
    #         outlet_values,
    #         default=outlet_values,
    #         key="selected_outlets",
    #     )

    #     # ----------------------------------------------------
    #     # Supplier
    #     # ----------------------------------------------------

    #     supplier_values = sorted(
    #         data["SUPPLIER"]
    #         .dropna()
    #         .astype(str)
    #         .unique()
    #         .tolist()
    #     )

    #     selected_suppliers = st.multiselect(
    #         "Supplier",
    #         supplier_values,
    #         default=supplier_values,
    #         key="selected_suppliers",
    #     )

    #     # ----------------------------------------------------
    #     # Department
    #     # ----------------------------------------------------

    #     department_values = sorted(
    #         data["DEPT"]
    #         .dropna()
    #         .astype(str)
    #         .unique()
    #         .tolist()
    #     )

    #     selected_departments = st.multiselect(
    #         "Department",
    #         department_values,
    #         default=department_values,
    #         key="selected_departments",
    #     )

    #     # ----------------------------------------------------
    #     # Class
    #     # ----------------------------------------------------

    #     class_values = sorted(
    #         data["CLASS"]
    #         .dropna()
    #         .astype(str)
    #         .unique()
    #         .tolist()
    #     )

    #     selected_classes = st.multiselect(
    #         "Class",
    #         class_values,
    #         default=class_values,
    #         key="selected_classes",
    #     )

    #     # ----------------------------------------------------
    #     # SKU
    #     # ----------------------------------------------------

    #     sku_values = sorted(
    #         data["SKU"]
    #         .dropna()
    #         .astype(str)
    #         .unique()
    #         .tolist()
    #     )

    #     selected_skus = st.multiselect(
    #         "SKU",
    #         sku_values,
    #         default=sku_values,
    #         key="selected_skus",
    #     )

    #     # ----------------------------------------------------
    #     # Dataset information
    #     # ----------------------------------------------------

    #     st.divider()

    #     st.caption("Dataset")

    #     st.write(
    #         f"Rows: **{len(data):,}**"
    #     )

    #     st.write(
    #         f"SKUs: **{data['SKU'].nunique():,}**"
    #     )

    #     st.write(
    #         f"Months: **{data['MONTH'].nunique():,}**"
    #     )

    # # --------------------------------------------------------
    # # Apply filters
    # # --------------------------------------------------------

    # filtered_data = data[
    #     data["MONTH"].isin(selected_months)
    #     & data["WHOUSE"].isin(selected_warehouses)
    #     & data["OUTLET"].isin(selected_outlets)
    #     & data["SUPPLIER"].isin(selected_suppliers)
    #     & data["DEPT"].isin(selected_departments)
    #     & data["CLASS"].isin(selected_classes)
    #     & data["SKU"].isin(selected_skus)
    # ].copy()

    # return filtered_data
    return data.copy()


# ============================================================
# MAIN DASHBOARD
# ============================================================

def main() -> None:

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    data = load_application_data()

    # --------------------------------------------------------
    # Apply filters
    # --------------------------------------------------------

    filtered_data = apply_sidebar_filters(data)

    if filtered_data.empty:
        create_empty_message()

    # ========================================================
    # HEADER
    # ========================================================

    st.title("📊 Executive Overview")

    st.caption(
        "High-level view of sales, volume, product, outlet, "
        "and supplier performance."
    )

    # --------------------------------------------------------
    # Current filter context
    # --------------------------------------------------------

    selected_month_values = sorted(
        filtered_data["MONTH"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if selected_month_values:

        if len(selected_month_values) == 1:

            period_text = format_month(
                selected_month_values[0]
            )

        else:

            period_text = (
                f"{format_month(selected_month_values[0])}"
                f" – "
                f"{format_month(selected_month_values[-1])}"
            )

    else:

        period_text = "No period selected"

    st.info(
        f"📅 **Reporting period:** {period_text}  |  "
        f"Showing **{len(filtered_data):,}** filtered rows "
        f"from **{len(data):,}** total rows."
    )

    # ========================================================
    # MONTHLY SUMMARY
    # ========================================================

    monthly_summary = (
        filtered_data
        .groupby("MONTH", as_index=False)
        .agg(
            QTY=("QTY", "sum"),
            AMT=("AMT", "sum"),
        )
        .sort_values("MONTH")
    )

    monthly_summary["Growth %"] = (
        monthly_summary["AMT"]
        .pct_change()
        .mul(100)
    )

    # ========================================================
    # EXECUTIVE KPIs
    # ========================================================

    total_sales = filtered_data["AMT"].sum()

    total_qty = filtered_data["QTY"].sum()

    active_skus = filtered_data["SKU"].nunique()

    active_outlets = filtered_data["OUTLET"].nunique()

    active_suppliers = filtered_data["SUPPLIER"].nunique()

    latest_growth = None

    if len(monthly_summary) >= 2:

        latest_growth = (
            monthly_summary["Growth %"]
            .iloc[-1]
        )

    st.subheader("📌 Key Performance Indicators")

    kpi = st.columns(5)

    kpi[0].metric(
        "Total Sales",
        ringgit(total_sales),
    )

    kpi[1].metric(
        "Units Sold",
        f"{total_qty:,.0f}",
    )

    kpi[2].metric(
        "Active SKUs",
        f"{active_skus:,}",
    )

    kpi[3].metric(
        "Active Outlets",
        f"{active_outlets:,}",
    )

    kpi[4].metric(
        "Latest MoM Growth",
        format_percentage(latest_growth),
    )

    # ========================================================
    # SALES TREND
    # ========================================================

    st.divider()

    st.subheader("📈 Sales Performance")

    if len(monthly_summary) >= 1:

        monthly_chart = px.line(
            monthly_summary,
            x="MONTH",
            y="AMT",
            markers=True,
            labels={
                "MONTH": "Month",
                "AMT": "Sales",
            },
            custom_data=["QTY"],
        )

        monthly_chart.update_traces(
            line=dict(
                color="#2563EB",
                width=3,
            ),
            marker=dict(
                size=9,
                color="#2563EB",
            ),
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Sales: RM %{y:,.2f}<br>"
                "Units: %{customdata[0]:,.0f}"
                "<extra></extra>"
            ),
        )

        monthly_chart.update_layout(
            height=400,
            hovermode="x unified",
            showlegend=False,
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
            xaxis=dict(
                title="",
            ),
            yaxis=dict(
                title="Sales (RM)",
                tickformat=",.0f",
            ),
        )

        st.plotly_chart(
            monthly_chart,
            use_container_width=True,
        )

    # ========================================================
    # MANAGEMENT SUMMARY
    # ========================================================

    if len(monthly_summary) >= 2:

        latest = monthly_summary.iloc[-1]

        previous = monthly_summary.iloc[-2]

        latest_amount = latest["AMT"]

        previous_amount = previous["AMT"]

        change_amount = (
            latest_amount
            - previous_amount
        )

        growth = latest["Growth %"]

        if growth > 0:

            icon = "🟢"

            message = (
                f"Sales increased from "
                f"**{ringgit(previous_amount)}** "
                f"in {format_month(previous['MONTH'])} "
                f"to **{ringgit(latest_amount)}** "
                f"in {format_month(latest['MONTH'])}."
            )

        elif growth < 0:

            icon = "🔴"

            message = (
                f"Sales decreased from "
                f"**{ringgit(previous_amount)}** "
                f"in {format_month(previous['MONTH'])} "
                f"to **{ringgit(latest_amount)}** "
                f"in {format_month(latest['MONTH'])}."
            )

        else:

            icon = "🟡"

            message = (
                f"Sales remained unchanged at "
                f"**{ringgit(latest_amount)}**."
            )

        st.info(
            f"{icon} **Management Summary**  \n"
            f"{message}  \n"
            f"Change: **{format_change(change_amount)}** "
            f"({format_percentage(growth)})."
        )

    # ========================================================
    # SALES BY BUSINESS DIMENSION
    # ========================================================

    st.divider()

    st.subheader("🏢 Sales by Business Dimension")

    dimension_row = st.columns(2)

    # --------------------------------------------------------
    # Department
    # --------------------------------------------------------

    department_amount = (
        filtered_data
        .groupby("DEPT", as_index=False)["AMT"]
        .sum()
        .sort_values("AMT")
    )

    department_chart = px.bar(
        department_amount,
        x="AMT",
        y="DEPT",
        orientation="h",
        labels={
            "AMT": "Sales",
            "DEPT": "Department",
        },
        color="AMT",
        color_continuous_scale="Blues",
    )

    department_chart.update_layout(
        coloraxis_showscale=False,
        height=400,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=20,
        ),
        xaxis_title="Sales (RM)",
        yaxis_title="",
    )

    with dimension_row[0]:

        st.markdown("**Sales by Department**")

        st.plotly_chart(
            department_chart,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Class
    # --------------------------------------------------------

    class_amount = (
        filtered_data
        .groupby("CLASS", as_index=False)["AMT"]
        .sum()
        .sort_values("AMT")
    )

    class_chart = px.bar(
        class_amount,
        x="AMT",
        y="CLASS",
        orientation="h",
        labels={
            "AMT": "Sales",
            "CLASS": "Class",
        },
        color="AMT",
        color_continuous_scale="Purples",
    )

    class_chart.update_layout(
        coloraxis_showscale=False,
        height=400,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=20,
        ),
        xaxis_title="Sales (RM)",
        yaxis_title="",
    )

    with dimension_row[1]:

        st.markdown("**Sales by Class**")

        st.plotly_chart(
            class_chart,
            use_container_width=True,
        )

    # ========================================================
    # OUTLET + SUPPLIER
    # ========================================================

    st.divider()

    st.subheader("🏪 Sales by Channel Partners")

    partner_row = st.columns(2)

    # --------------------------------------------------------
    # Outlet
    # --------------------------------------------------------

    outlet_amount = (
        filtered_data
        .groupby("OUTLET", as_index=False)["AMT"]
        .sum()
        .sort_values("AMT", ascending=True)
    )

    outlet_chart = px.bar(
        outlet_amount,
        x="AMT",
        y="OUTLET",
        orientation="h",
        labels={
            "AMT": "Sales",
            "OUTLET": "Outlet",
        },
        color="AMT",
        color_continuous_scale="Teal",
    )

    outlet_chart.update_layout(
        coloraxis_showscale=False,
        height=450,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=20,
        ),
        xaxis_title="Sales (RM)",
        yaxis_title="",
    )

    with partner_row[0]:

        st.markdown("**Sales by Outlet**")

        st.plotly_chart(
            outlet_chart,
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Supplier
    # --------------------------------------------------------

    supplier_amount = (
        filtered_data
        .groupby("SUPPLIER", as_index=False)["AMT"]
        .sum()
        .sort_values("AMT", ascending=True)
    )

    supplier_chart = px.bar(
        supplier_amount,
        x="AMT",
        y="SUPPLIER",
        orientation="h",
        labels={
            "AMT": "Sales",
            "SUPPLIER": "Supplier",
        },
        color="AMT",
        color_continuous_scale="Greens",
    )

    supplier_chart.update_layout(
        coloraxis_showscale=False,
        height=450,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=20,
        ),
        xaxis_title="Sales (RM)",
        yaxis_title="",
    )

    with partner_row[1]:

        st.markdown("**Sales by Supplier**")

        st.plotly_chart(
            supplier_chart,
            use_container_width=True,
        )

    # ========================================================
    # TOP SKUs
    # ========================================================

    st.divider()

    st.subheader("🏆 Top 10 SKUs by Sales")

    top_skus = (
        filtered_data
        .groupby("SKU", as_index=False)
        .agg(
            QTY=("QTY", "sum"),
            AMT=("AMT", "sum"),
        )
        .sort_values(
            "AMT",
            ascending=False,
        )
        .head(10)
    )

    top_skus_chart_data = (
        top_skus
        .sort_values("AMT")
    )

    sku_chart = px.bar(
        top_skus_chart_data,
        x="AMT",
        y="SKU",
        orientation="h",
        labels={
            "AMT": "Sales",
            "SKU": "SKU",
        },
        color="AMT",
        color_continuous_scale="Oranges",
    )

    sku_chart.update_layout(
        coloraxis_showscale=False,
        height=450,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=20,
        ),
        xaxis_title="Sales (RM)",
        yaxis_title="",
    )

    st.plotly_chart(
        sku_chart,
        use_container_width=True,
    )

    top_skus_display = top_skus.copy()

    top_skus_display["AMT"] = (
        top_skus_display["AMT"]
        .map(ringgit)
    )

    top_skus_display["QTY"] = (
        top_skus_display["QTY"]
        .map(lambda x: f"{x:,.0f}")
    )

    st.dataframe(
        top_skus_display,
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # MONTHLY SUMMARY TABLE
    # ========================================================

    st.divider()

    st.subheader("📅 Monthly Sales Summary")

    monthly_display = monthly_summary.copy()

    monthly_display["MONTH"] = (
        monthly_display["MONTH"]
        .map(format_month)
    )

    monthly_display["AMT"] = (
        monthly_display["AMT"]
        .map(ringgit)
    )

    monthly_display["QTY"] = (
        monthly_display["QTY"]
        .map(lambda x: f"{x:,.0f}")
    )

    monthly_display["Growth %"] = (
        monthly_summary["Growth %"]
        .map(
            lambda x:
            "—"
            if pd.isna(x)
            else f"{x:+.1f}%"
        )
    )

    st.dataframe(
        monthly_display[
            [
                "MONTH",
                "QTY",
                "AMT",
                "Growth %",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    # ========================================================
    # DOWNLOAD
    # ========================================================

    st.divider()

    st.subheader("📥 Export")

    csv_data = filtered_data.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        "Download Filtered Data (CSV)",
        data=csv_data,
        file_name="filtered_retail_sales.csv",
        mime="text/csv",
    )

    # ========================================================
    # DATASET DETAILS
    # ========================================================

    with st.expander("🔎 View filtered data"):

        st.dataframe(
            filtered_data.style.format(
                {
                    "AMT": "RM {:,.2f}",
                    "QTY": "{:,.0f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    main()
