from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app_data import load_data, apply_filters
from data_utils import ringgit


APP_TITLE = "Monthly Comparison / Performance"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📈",
    layout="wide",
)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def calculate_growth(
    previous: float,
    current: float,
) -> float | None:
    """
    Calculate percentage change between two values.

    Returns:
        None when previous value is zero and current value
        is non-zero.
        0 when both values are zero.
    """

    if previous == 0:

        if current == 0:
            return 0.0

        return None

    return (
        (current - previous)
        / previous
        * 100
    )


def format_growth(
    value: float | None,
) -> str:
    """
    Format a percentage growth value.
    """

    if value is None or pd.isna(value):
        return "New"

    return f"{value:+.1f}%"


def format_quantity(
    value: float,
) -> str:
    """
    Format quantity values.
    """

    if pd.isna(value):
        return "0"

    return f"{value:,.0f}"


def format_month(
    month: str,
) -> str:
    """
    Convert YYYY-MM into a friendly month label.

    Example:
        2026-07 -> Jul 2026

    If conversion fails, return the original value.
    """

    try:

        return pd.to_datetime(
            month,
            format="%Y-%m",
        ).strftime("%b %Y")

    except Exception:

        return str(month)


def create_empty_message() -> None:
    """
    Display a friendly empty-data message.
    """

    st.warning(
        "No data matches the current global filters. "
        "Please select more values from the sidebar."
    )

    st.stop()


def add_change_columns(
    comparison: pd.DataFrame,
    previous_column: str,
    current_column: str,
) -> pd.DataFrame:
    """
    Add absolute and percentage change columns.
    """

    result = comparison.copy()

    result["CHANGE"] = (
        result[current_column]
        - result[previous_column]
    )

    result["CHANGE_%"] = result.apply(
        lambda row: calculate_growth(
            row[previous_column],
            row[current_column],
        ),
        axis=1,
    )

    return result


def apply_non_month_filters(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply the current global filters except Month.

    This is important for Page 5.

    The comparison page should allow the user to compare
    any two available months while still respecting:

        Warehouse
        Outlet
        Supplier
        Department
        Class
        SKU

    The sidebar Month filter is intentionally ignored.
    """

    comparison_data = data.copy()

    filter_mapping = {
        "selected_warehouses": "WHOUSE",
        "selected_outlets": "OUTLET",
        "selected_suppliers": "SUPPLIER",
        "selected_departments": "DEPT",
        "selected_classes": "CLASS",
        "selected_skus": "SKU",
    }

    for session_key, column_name in filter_mapping.items():

        selected_values = st.session_state.get(
            session_key
        )

        if selected_values is not None:

            comparison_data = comparison_data[
                comparison_data[column_name].isin(
                    selected_values
                )
            ]

    return comparison_data.copy()


def build_entity_comparison(
    previous_data: pd.DataFrame,
    current_data: pd.DataFrame,
    entity_column: str,
    include_quantity: bool = False,
) -> pd.DataFrame:
    """
    Build a month-to-month comparison for an entity.

    Example entities:

        SKU
        OUTLET
        SUPPLIER
    """

    previous_agg = (
        previous_data
        .groupby(
            entity_column,
            as_index=False,
        )
        .agg(
            PREVIOUS_SALES=("AMT", "sum"),
            **(
                {
                    "PREVIOUS_QTY": (
                        "QTY",
                        "sum",
                    )
                }
                if include_quantity
                else {}
            ),
        )
    )

    current_agg = (
        current_data
        .groupby(
            entity_column,
            as_index=False,
        )
        .agg(
            CURRENT_SALES=("AMT", "sum"),
            **(
                {
                    "CURRENT_QTY": (
                        "QTY",
                        "sum",
                    )
                }
                if include_quantity
                else {}
            ),
        )
    )

    comparison = previous_agg.merge(
        current_agg,
        on=entity_column,
        how="outer",
    )

    numeric_columns = [
        column
        for column in comparison.columns
        if column != entity_column
    ]

    comparison[numeric_columns] = (
        comparison[numeric_columns]
        .fillna(0)
    )

    comparison = add_change_columns(
        comparison,
        "PREVIOUS_SALES",
        "CURRENT_SALES",
    )

    if include_quantity:

        comparison["QTY_CHANGE"] = (
            comparison["CURRENT_QTY"]
            - comparison["PREVIOUS_QTY"]
        )

        comparison["QTY_CHANGE_%"] = (
            comparison.apply(
                lambda row: calculate_growth(
                    row["PREVIOUS_QTY"],
                    row["CURRENT_QTY"],
                ),
                axis=1,
            )
        )

    return comparison.sort_values(
        "CHANGE",
        ascending=False,
    ).reset_index(drop=True)


def format_sales_comparison_table(
    comparison: pd.DataFrame,
    entity_column: str,
    include_quantity: bool = False,
) -> pd.DataFrame:
    """
    Create a display-friendly comparison table.
    """

    display = comparison.copy()

    display["PREVIOUS_SALES"] = (
        display["PREVIOUS_SALES"]
        .map(ringgit)
    )

    display["CURRENT_SALES"] = (
        display["CURRENT_SALES"]
        .map(ringgit)
    )

    display["CHANGE"] = (
        display["CHANGE"]
        .map(ringgit)
    )

    display["CHANGE_%"] = (
        display["CHANGE_%"]
        .map(format_growth)
    )

    columns = [
        entity_column,
        "PREVIOUS_SALES",
        "CURRENT_SALES",
        "CHANGE",
        "CHANGE_%",
    ]

    if include_quantity:

        display["PREVIOUS_QTY"] = (
            display["PREVIOUS_QTY"]
            .map(format_quantity)
        )

        display["CURRENT_QTY"] = (
            display["CURRENT_QTY"]
            .map(format_quantity)
        )

        display["QTY_CHANGE"] = (
            display["QTY_CHANGE"]
            .map(
                lambda value:
                f"{value:+,.0f}"
            )
        )

        columns += [
            "PREVIOUS_QTY",
            "CURRENT_QTY",
            "QTY_CHANGE",
        ]

    return display[columns]


def display_change_table(
    comparison: pd.DataFrame,
    entity_column: str,
    include_quantity: bool = False,
) -> None:
    """
    Display a formatted comparison table.
    """

    display = format_sales_comparison_table(
        comparison,
        entity_column,
        include_quantity,
    )

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
    )


def display_top_changes(
    comparison: pd.DataFrame,
    entity_column: str,
    positive_title: str,
    negative_title: str,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:

    positive = (
        comparison[
            comparison["CHANGE"] > 0
        ]
        .sort_values(
            "CHANGE",
            ascending=False,
        )
        .head(10)
    )

    negative = (
        comparison[
            comparison["CHANGE"] < 0
        ]
        .sort_values(
            "CHANGE",
            ascending=True,
        )
        .head(10)
    )

    left_column, right_column = st.columns(2)

    with left_column:

        st.markdown(
            f"### {positive_title}"
        )

        if positive.empty:

            st.info(
                f"No {entity_column.lower()} "
                "sales increases found."
            )

        else:

            positive_display = (
                positive[
                    [
                        entity_column,
                        "CHANGE",
                        "CHANGE_%",
                    ]
                ]
                .copy()
            )

            positive_display["CHANGE"] = (
                positive_display["CHANGE"]
                .map(ringgit)
            )

            positive_display["CHANGE_%"] = (
                positive_display["CHANGE_%"]
                .map(format_growth)
            )

            st.dataframe(
                positive_display,
                use_container_width=True,
                hide_index=True,
            )

    with right_column:

        st.markdown(
            f"### {negative_title}"
        )

        if negative.empty:

            st.info(
                f"No {entity_column.lower()} "
                "sales declines found."
            )

        else:

            negative_display = (
                negative[
                    [
                        entity_column,
                        "CHANGE",
                        "CHANGE_%",
                    ]
                ]
                .copy()
            )

            negative_display["CHANGE"] = (
                negative_display["CHANGE"]
                .map(ringgit)
            )

            negative_display["CHANGE_%"] = (
                negative_display["CHANGE_%"]
                .map(format_growth)
            )

            st.dataframe(
                negative_display,
                use_container_width=True,
                hide_index=True,
            )

    return positive, negative


def create_sales_comparison_chart(
    month_a: str,
    month_b: str,
    sales_a: float,
    sales_b: float,
):
    """
    Create the two-month sales comparison chart.
    """

    chart_data = pd.DataFrame(
        {
            "MONTH": [
                month_a,
                month_b,
            ],
            "AMT": [
                sales_a,
                sales_b,
            ],
        }
    )

    chart = px.bar(
        chart_data,
        x="MONTH",
        y="AMT",
        text="AMT",
        color="MONTH",
        labels={
            "MONTH": "Month",
            "AMT": "Sales Amount (RM)",
        },
        color_discrete_sequence=[
            "#94A3B8",
            "#2563EB",
        ],
    )

    chart.update_traces(
        texttemplate="RM %{text:,.0f}",
        textposition="outside",
    )

    chart.update_layout(
        showlegend=False,
        height=400,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        xaxis_title="",
        yaxis_title="Sales (RM)",
        yaxis_tickformat=",.0f",
    )

    return chart


def create_monthly_trend_chart(
    trend_data: pd.DataFrame,
    month_a: str,
    month_b: str,
):
    """
    Create the overall monthly sales trend chart.
    """

    chart = px.line(
        trend_data,
        x="MONTH",
        y="AMT",
        markers=True,
        text="AMT",
        labels={
            "MONTH": "Month",
            "AMT": "Sales Amount (RM)",
        },
    )

    chart.update_traces(
        line=dict(
            color="#2563EB",
            width=3,
        ),
        marker=dict(
            size=8,
            color="#2563EB",
        ),
        texttemplate="RM %{text:,.0f}",
        textposition="top center",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Sales: RM %{y:,.2f}"
            "<extra></extra>"
        ),
    )

    chart.update_layout(
        height=420,
        hovermode="x unified",
        showlegend=False,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=20,
        ),
        xaxis_title="",
        yaxis_title="Sales (RM)",
        yaxis_tickformat=",.0f",
    )

    # Highlight comparison months.

    chart.add_vline(
        x=month_a,
        line_dash="dot",
        line_color="#94A3B8",
        opacity=0.8,
    )

    chart.add_vline(
        x=month_b,
        line_dash="dot",
        line_color="#2563EB",
        opacity=0.8,
    )

    return chart


# ============================================================
# MAIN PAGE
# ============================================================

def main() -> None:

    # ========================================================
    # LOAD DATA
    # ========================================================

    data = load_data()

    filtered_data = apply_filters(data)

    if filtered_data.empty:
        create_empty_message()

    # ========================================================
    # PAGE HEADER
    # ========================================================

    st.title(
        "📈 Monthly Comparison / Performance"
    )

    st.caption(
        "Compare business performance between two months "
        "and identify the biggest improvements and declines."
    )

    # ========================================================
    # COMPARISON BASE
    # ========================================================

    comparison_base = apply_non_month_filters(
        data
    )

    if comparison_base.empty:

        st.warning(
            "No data is available for comparison "
            "after applying the selected filters."
        )

        st.stop()

    # ========================================================
    # AVAILABLE MONTHS
    # ========================================================

    available_months = sorted(
        comparison_base["MONTH"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if len(available_months) < 2:

        st.warning(
            "At least two months are required "
            "for monthly comparison."
        )

        st.stop()

    # ========================================================
    # COMPARISON PERIOD
    # ========================================================

    st.subheader(
        "📅 Comparison Period"
    )

    st.caption(
        "Select any two available months. "
        "The sidebar Month filter does not restrict "
        "this comparison."
    )

    month_col_a, month_col_b = st.columns(2)

    default_previous = (
        available_months[-2]
    )

    default_current = (
        available_months[-1]
    )

    with month_col_a:

        month_a = st.selectbox(
            "Month A",
            options=available_months,
            index=available_months.index(
                default_previous
            ),
            format_func=format_month,
            key="comparison_month_a",
        )

    with month_col_b:

        month_b = st.selectbox(
            "Month B",
            options=available_months,
            index=available_months.index(
                default_current
            ),
            format_func=format_month,
            key="comparison_month_b",
        )

    if month_a == month_b:

        st.warning(
            "Please select two different months "
            "to perform a comparison."
        )

        st.stop()

    st.info(
        f"📊 Comparing "
        f"**{format_month(month_a)}** "
        f"against "
        f"**{format_month(month_b)}**."
    )

    # ========================================================
    # MONTH DATASETS
    # ========================================================

    month_a_data = comparison_base[
        comparison_base["MONTH"].astype(str)
        == str(month_a)
    ].copy()

    month_b_data = comparison_base[
        comparison_base["MONTH"].astype(str)
        == str(month_b)
    ].copy()

    if month_a_data.empty:

        st.warning(
            f"No data available for "
            f"{format_month(month_a)}."
        )

        st.stop()

    if month_b_data.empty:

        st.warning(
            f"No data available for "
            f"{format_month(month_b)}."
        )

        st.stop()

    # ========================================================
    # OVERALL PERFORMANCE
    # ========================================================

    st.divider()

    st.subheader(
        "📊 Overall Performance"
    )

    previous_sales = (
        month_a_data["AMT"].sum()
    )

    current_sales = (
        month_b_data["AMT"].sum()
    )

    previous_qty = (
        month_a_data["QTY"].sum()
    )

    current_qty = (
        month_b_data["QTY"].sum()
    )

    sales_change = (
        current_sales
        - previous_sales
    )

    qty_change = (
        current_qty
        - previous_qty
    )

    sales_growth = calculate_growth(
        previous_sales,
        current_sales,
    )

    qty_growth = calculate_growth(
        previous_qty,
        current_qty,
    )

    active_skus_current = (
        month_b_data["SKU"].nunique()
    )

    active_outlets_current = (
        month_b_data["OUTLET"].nunique()
    )

    active_suppliers_current = (
        month_b_data["SUPPLIER"].nunique()
    )

    # ========================================================
    # KPI ROW
    # ========================================================

    kpi_row_one = st.columns(4)

    kpi_row_one[0].metric(
        f"{format_month(month_a)} Sales",
        ringgit(previous_sales),
    )

    kpi_row_one[1].metric(
        f"{format_month(month_b)} Sales",
        ringgit(current_sales),
    )

    kpi_row_one[2].metric(
        "Sales Change",
        ringgit(sales_change),
        delta=(
            "New"
            if sales_growth is None
            else f"{sales_growth:+.1f}%"
        ),
    )

    kpi_row_one[3].metric(
        "Sales Growth",
        (
            "New"
            if sales_growth is None
            else f"{sales_growth:+.1f}%"
        ),
    )

    kpi_row_two = st.columns(5)

    kpi_row_two[0].metric(
        "Quantity Change",
        f"{qty_change:+,.0f}",
        delta=(
            "New"
            if qty_growth is None
            else f"{qty_growth:+.1f}%"
        ),
    )

    kpi_row_two[1].metric(
        "Quantity Growth",
        (
            "New"
            if qty_growth is None
            else f"{qty_growth:+.1f}%"
        ),
    )

    kpi_row_two[2].metric(
        f"Active SKUs ({format_month(month_b)})",
        f"{active_skus_current:,}",
    )

    kpi_row_two[3].metric(
        f"Active Outlets ({format_month(month_b)})",
        f"{active_outlets_current:,}",
    )

    kpi_row_two[4].metric(
        f"Active Suppliers ({format_month(month_b)})",
        f"{active_suppliers_current:,}",
    )

    # ========================================================
    # OVERALL SALES COMPARISON
    # ========================================================

    st.subheader(
        "📊 Sales Comparison"
    )

    overall_chart = (
        create_sales_comparison_chart(
            month_a,
            month_b,
            previous_sales,
            current_sales,
        )
    )

    st.plotly_chart(
        overall_chart,
        use_container_width=True,
    )

    # ========================================================
    # SKU PERFORMANCE
    # ========================================================

    st.divider()

    st.subheader(
        "🔎 SKU Performance Change"
    )

    sku_comparison = build_entity_comparison(
        month_a_data,
        month_b_data,
        "SKU",
        include_quantity=True,
    )

    display_change_table(
        sku_comparison,
        "SKU",
        include_quantity=True,
    )

    # ========================================================
    # SKU IMPROVEMENTS / DECLINES
    # ========================================================

    sku_positive, sku_negative = (
        display_top_changes(
            sku_comparison,
            "SKU",
            "🚀 Top Growing SKUs",
            "📉 Top Declining SKUs",
        )
    )

    # ========================================================
    # OUTLET PERFORMANCE
    # ========================================================

    st.divider()

    st.subheader(
        "🏪 Outlet Performance Change"
    )

    outlet_comparison = build_entity_comparison(
        month_a_data,
        month_b_data,
        "OUTLET",
    )

    display_change_table(
        outlet_comparison,
        "OUTLET",
    )

    # ========================================================
    # OUTLET IMPROVEMENTS / DECLINES
    # ========================================================

    outlet_positive, outlet_negative = (
        display_top_changes(
            outlet_comparison,
            "OUTLET",
            "🚀 Biggest Outlet Improvements",
            "📉 Biggest Outlet Declines",
        )
    )

    # ========================================================
    # SUPPLIER PERFORMANCE
    # ========================================================

    st.divider()

    st.subheader(
        "📦 Supplier Performance Change"
    )

    supplier_comparison = (
        build_entity_comparison(
            month_a_data,
            month_b_data,
            "SUPPLIER",
        )
    )

    display_change_table(
        supplier_comparison,
        "SUPPLIER",
    )

    # ========================================================
    # SUPPLIER IMPROVEMENTS / DECLINES
    # ========================================================

    supplier_positive, supplier_negative = (
        display_top_changes(
            supplier_comparison,
            "SUPPLIER",
            "🚀 Biggest Supplier Improvements",
            "📉 Biggest Supplier Declines",
        )
    )

    # ========================================================
    # OVERALL MONTHLY TREND
    # ========================================================

    st.divider()

    st.subheader(
        "📈 Overall Monthly Sales Trend"
    )

    trend_data = (
        comparison_base
        .groupby(
            "MONTH",
            as_index=False,
        )
        .agg(
            QTY=("QTY", "sum"),
            AMT=("AMT", "sum"),
        )
        .sort_values("MONTH")
    )

    trend_data["MoM Growth %"] = (
        trend_data["AMT"]
        .pct_change()
        .mul(100)
    )

    trend_chart = create_monthly_trend_chart(
        trend_data,
        month_a,
        month_b,
    )

    st.plotly_chart(
        trend_chart,
        use_container_width=True,
    )

    # ========================================================
    # MONTHLY TREND TABLE
    # ========================================================

    st.subheader(
        "📅 Monthly Sales Summary"
    )

    trend_display = trend_data.copy()

    trend_display["MONTH"] = (
        trend_display["MONTH"]
        .map(format_month)
    )

    trend_display["AMT"] = (
        trend_data["AMT"]
        .map(ringgit)
    )

    trend_display["QTY"] = (
        trend_data["QTY"]
        .map(format_quantity)
    )

    trend_display["MoM Growth %"] = (
        trend_data["MoM Growth %"]
        .map(format_growth)
    )

    st.dataframe(
        trend_display[
            [
                "MONTH",
                "AMT",
                "QTY",
                "MoM Growth %",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    # ============================================================
    # MANAGEMENT INSIGHTS
    # ============================================================

    st.divider()

    st.subheader(
        "💡 Management Insights"
    )

    # ============================================================
    # OVERALL SALES INSIGHT
    # ============================================================

    if sales_growth is None:

        st.info(
            f"🆕 **Sales increased from "
            f"{ringgit(previous_sales)}** "
            f"in {format_month(month_a)} "
            f"to **{ringgit(current_sales)}** "
            f"in {format_month(month_b)}."
        )

    elif sales_growth > 0:

        st.success(
            f"📈 **Sales increased by "
            f"{sales_growth:+.1f}%** "
            f"from {format_month(month_a)} "
            f"to {format_month(month_b)}, "
            f"rising from "
            f"**{ringgit(previous_sales)}** "
            f"to **{ringgit(current_sales)}**."
        )

    elif sales_growth < 0:

        st.error(
            f"📉 **Sales declined by "
            f"{abs(sales_growth):.1f}%** "
            f"from {format_month(month_a)} "
            f"to {format_month(month_b)}, "
            f"falling from "
            f"**{ringgit(previous_sales)}** "
            f"to **{ringgit(current_sales)}**."
        )

    else:

        st.info(
            f"🟡 **Sales remained unchanged** "
            f"between {format_month(month_a)} "
            f"and {format_month(month_b)}."
        )


    # ============================================================
    # QUANTITY INSIGHT
    # ============================================================

    if qty_growth is not None:

        if qty_growth > 0:

            st.success(
                f"📦 **Units sold increased by "
                f"{qty_growth:+.1f}%**, "
                f"from "
                f"{format_quantity(previous_qty)} "
                f"to "
                f"{format_quantity(current_qty)} units."
            )

        elif qty_growth < 0:

            st.warning(
                f"📦 **Units sold declined by "
                f"{abs(qty_growth):.1f}%**, "
                f"from "
                f"{format_quantity(previous_qty)} "
                f"to "
                f"{format_quantity(current_qty)} units."
            )

        else:

            st.info(
                f"📦 **Units sold remained unchanged** "
                f"at {format_quantity(current_qty)} units."
            )


    # ============================================================
    # SIGNIFICANT SKU CHANGES
    # ============================================================

    st.markdown("### 🔎 Significant SKU Changes")

    # Top 3 increases

    significant_sku_increases = (
        sku_comparison[
            sku_comparison["CHANGE"] > 0
        ]
        .sort_values(
            "CHANGE",
            ascending=False,
        )
        .head()
    )

    if not significant_sku_increases.empty:

        st.markdown("#### 🚀 Biggest SKU Sales Increases")

        for _, row in significant_sku_increases.iterrows():

            st.success(
                f"**{row['SKU']}** increased sales by "
                f"**{ringgit(row['CHANGE'])}** "
                f"({format_growth(row['CHANGE_%'])})."
            )

    # Top 3 decreases

    significant_sku_decreases = (
        sku_comparison[
            sku_comparison["CHANGE"] < 0
        ]
        .sort_values(
            "CHANGE",
            ascending=True,
        )
        .head()
    )

    if not significant_sku_decreases.empty:

        st.markdown("#### 📉 Biggest SKU Sales Decreases")

        for _, row in significant_sku_decreases.iterrows():

            st.error(
                f"**{row['SKU']}** decreased sales by "
                f"**{ringgit(abs(row['CHANGE']))}** "
                f"({format_growth(row['CHANGE_%'])})."
            )


    # ============================================================
    # SIGNIFICANT OUTLET CHANGES
    # ============================================================

    st.markdown("### 🏪 Significant Outlet Changes")

    # Top 3 increases

    significant_outlet_increases = (
        outlet_comparison[
            outlet_comparison["CHANGE"] > 0
        ]
        .sort_values(
            "CHANGE",
            ascending=False,
        )
        .head()
    )

    if not significant_outlet_increases.empty:

        st.markdown("#### 🚀 Biggest Outlet Sales Increases")

        for _, row in significant_outlet_increases.iterrows():

            st.success(
                f"**{row['OUTLET']}** increased sales by "
                f"**{ringgit(row['CHANGE'])}** "
                f"({format_growth(row['CHANGE_%'])})."
            )

    # Top 3 decreases

    significant_outlet_decreases = (
        outlet_comparison[
            outlet_comparison["CHANGE"] < 0
        ]
        .sort_values(
            "CHANGE",
            ascending=True,
        )
        .head()
    )

    if not significant_outlet_decreases.empty:

        st.markdown("#### 📉 Biggest Outlet Sales Decreases")

        for _, row in significant_outlet_decreases.iterrows():

            st.error(
                f"**{row['OUTLET']}** decreased sales by "
                f"**{ringgit(abs(row['CHANGE']))}** "
                f"({format_growth(row['CHANGE_%'])})."
            )


    # ============================================================
    # SIGNIFICANT SUPPLIER CHANGES
    # ============================================================

    st.markdown("### 📦 Significant Supplier Changes")

    # Top 3 increases

    significant_supplier_increases = (
        supplier_comparison[
            supplier_comparison["CHANGE"] > 0
        ]
        .sort_values(
            "CHANGE",
            ascending=False,
        )
        .head()
    )

    if not significant_supplier_increases.empty:

        st.markdown("#### 🚀 Biggest Supplier Sales Increases")

        for _, row in significant_supplier_increases.iterrows():

            st.success(
                f"**{row['SUPPLIER']}** increased sales by "
                f"**{ringgit(row['CHANGE'])}** "
                f"({format_growth(row['CHANGE_%'])})."
            )

    # Top 3 decreases

    significant_supplier_decreases = (
        supplier_comparison[
            supplier_comparison["CHANGE"] < 0
        ]
        .sort_values(
            "CHANGE",
            ascending=True,
        )
        .head()
    )

    if not significant_supplier_decreases.empty:

        st.markdown("#### 📉 Biggest Supplier Sales Decreases")

        for _, row in significant_supplier_decreases.iterrows():

            st.error(
                f"**{row['SUPPLIER']}** decreased sales by "
                f"**{ringgit(abs(row['CHANGE']))}** "
                f"({format_growth(row['CHANGE_%'])})."
            )

    # ========================================================
    # DATA COVERAGE
    # ========================================================

    st.divider()

    st.caption(
        f"Comparison based on "
        f"**{len(month_a_data):,} rows** in "
        f"**{format_month(month_a)}** and "
        f"**{len(month_b_data):,} rows** in "
        f"**{format_month(month_b)}**, "
        f"after applying the selected global filters "
        f"except the sidebar Month filter."
    )


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":
    main()