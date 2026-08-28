from __future__ import annotations

import re

import pandas as pd
import plotly.express as px
import streamlit as st

from app_data import load_data, apply_filters
from data_utils import ringgit


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="SKU Investigation",
    page_icon="🕵️",
    layout="wide",
)


# =========================================================
# PAGE TITLE
# =========================================================

st.title("🕵️ SKU Investigation")

st.caption(
    "Drill down into an individual SKU and identify "
    "where performance changes are coming from."
)


# =========================================================
# LOAD SHARED DATA
# =========================================================

data = load_data()
filtered_data = apply_filters(data)

if filtered_data.empty:
    st.warning(
        "No rows match the current filters. "
        "Please select more values on the Dashboard page."
    )
    st.stop()


# =========================================================
# AVAILABLE SKUS
# =========================================================

available_skus = sorted(
    filtered_data["SKU"]
    .dropna()
    .unique()
    .tolist()
)

if not available_skus:
    st.warning(
        "No SKUs are available in the current filters."
    )
    st.stop()


# =========================================================
# SKU SEARCH + SELECTOR
# =========================================================

st.subheader("Select SKU")

sku_search = st.text_input(
    "🔎 Search SKU / Product",
    placeholder="Type SKU, code, product name, etc.",
    key="investigation_sku_search",
)


if sku_search.strip():

    search_terms = re.split(
        r"[\s\-_\/]+",
        sku_search.lower().strip(),
    )

    search_terms = [
        term
        for term in search_terms
        if term
    ]

    filtered_sku_options = [
        sku
        for sku in available_skus
        if any(
            term in str(sku).lower()
            for term in search_terms
        )
    ]

else:

    filtered_sku_options = available_skus


if not filtered_sku_options:

    st.warning(
        f"No SKU found matching **{sku_search}**."
    )

    st.stop()


selected_sku = st.selectbox(
    "SKU to investigate",
    filtered_sku_options,
    key="investigation_sku",
)


sku_data = filtered_data[
    filtered_data["SKU"] == selected_sku
].copy()


if sku_data.empty:
    st.warning("No data found for this SKU.")
    st.stop()


# =========================================================
# SKU INFORMATION
# =========================================================

st.divider()
st.subheader("📋 SKU Information")

sku_supplier = (
    sku_data["SUPPLIER"]
    .dropna()
    .astype(str)
    .iloc[0]
    if not sku_data["SUPPLIER"].dropna().empty
    else "N/A"
)

sku_department = (
    sku_data["DEPT"]
    .dropna()
    .astype(str)
    .iloc[0]
    if not sku_data["DEPT"].dropna().empty
    else "N/A"
)

sku_class = (
    sku_data["CLASS"]
    .dropna()
    .astype(str)
    .iloc[0]
    if not sku_data["CLASS"].dropna().empty
    else "N/A"
)

sku_uom = (
    sku_data["UOM"]
    .dropna()
    .astype(str)
    .iloc[0]
    if not sku_data["UOM"].dropna().empty
    else "N/A"
)

info_columns = st.columns(4)

info_columns[0].metric(
    "SKU",
    selected_sku,
)

info_columns[1].metric(
    "Supplier",
    sku_supplier,
)

info_columns[2].metric(
    "Department",
    sku_department,
)

info_columns[3].metric(
    "Class",
    sku_class,
)

st.caption(f"Unit of Measure: **{sku_uom}**")


# =========================================================
# MONTHLY SKU PERFORMANCE
# =========================================================

monthly_sku = (
    sku_data
    .groupby("MONTH", as_index=False)
    .agg(
        QTY=("QTY", "sum"),
        AMT=("AMT", "sum"),
    )
    .sort_values("MONTH")
)

monthly_sku["MoM Growth %"] = (
    monthly_sku["AMT"]
    .pct_change()
    .mul(100)
)

available_months = sorted(
    monthly_sku["MONTH"]
    .dropna()
    .unique()
    .tolist()
)


# =========================================================
# OVERALL SKU KPIs
# =========================================================

total_amount = sku_data["AMT"].sum()
total_qty = sku_data["QTY"].sum()

average_monthly_amount = (
    monthly_sku["AMT"].mean()
)

best_month_row = monthly_sku.loc[
    monthly_sku["AMT"].idxmax()
]

worst_month_row = monthly_sku.loc[
    monthly_sku["AMT"].idxmin()
]


# =========================================================
# CURRENT STATUS
# =========================================================

if len(monthly_sku) >= 2:

    previous_amount_overall = monthly_sku["AMT"].iloc[-2]
    latest_amount_overall = monthly_sku["AMT"].iloc[-1]

    if (
        previous_amount_overall == 0
        and latest_amount_overall > 0
    ):
        sku_status = "New"

    elif (
        previous_amount_overall > 0
        and latest_amount_overall == 0
    ):
        sku_status = "Dropped"

    elif latest_amount_overall > previous_amount_overall:
        sku_status = "Growing"

    elif latest_amount_overall < previous_amount_overall:
        sku_status = "Declining"

    else:
        sku_status = "Existing"

else:

    sku_status = "Insufficient data"


# =========================================================
# SKU PERFORMANCE
# =========================================================

st.divider()
st.subheader("📊 SKU Performance")

kpi_columns = st.columns(5)

kpi_columns[0].metric(
    "Total Sales",
    ringgit(total_amount),
)

kpi_columns[1].metric(
    "Units Sold",
    f"{total_qty:,.0f}",
)

kpi_columns[2].metric(
    "Avg Monthly Sales",
    ringgit(average_monthly_amount),
)

kpi_columns[3].metric(
    "Best Month",
    str(best_month_row["MONTH"]),
)

kpi_columns[4].metric(
    "Current Status",
    sku_status,
)

st.caption(
    f"Best month: {best_month_row['MONTH']} "
    f"({ringgit(best_month_row['AMT'])}) · "
    f"Worst month: {worst_month_row['MONTH']} "
    f"({ringgit(worst_month_row['AMT'])})"
)


# =========================================================
# MONTH-TO-MONTH COMPARISON
# =========================================================

if len(available_months) >= 2:

    st.divider()
    st.subheader("📈 Month Comparison")

    comparison_columns = st.columns(2)

    with comparison_columns[0]:

        previous_month = st.selectbox(
            "Previous Month",
            available_months,
            index=len(available_months) - 2,
            key="investigation_previous_month",
        )

    latest_month_options = [
        month
        for month in available_months
        if month != previous_month
    ]

    with comparison_columns[1]:

        default_latest_index = (
            latest_month_options.index(
                available_months[-1]
            )
            if available_months[-1]
            in latest_month_options
            else 0
        )

        latest_month = st.selectbox(
            "Latest Month",
            latest_month_options,
            index=default_latest_index,
            key="investigation_latest_month",
        )


    # -----------------------------------------------------
    # SELECTED MONTH VALUES
    # -----------------------------------------------------

    previous_row = monthly_sku[
        monthly_sku["MONTH"] == previous_month
    ]

    latest_row = monthly_sku[
        monthly_sku["MONTH"] == latest_month
    ]

    previous_amount = (
        previous_row["AMT"].iloc[0]
        if not previous_row.empty
        else 0
    )

    latest_amount = (
        latest_row["AMT"].iloc[0]
        if not latest_row.empty
        else 0
    )

    change_amount = (
        latest_amount - previous_amount
    )

    if previous_amount != 0:

        change_percent = (
            change_amount
            / previous_amount
            * 100
        )

    else:

        change_percent = None


    # -----------------------------------------------------
    # SELECTED PERIOD STATUS
    # -----------------------------------------------------

    if (
        previous_amount == 0
        and latest_amount > 0
    ):

        comparison_status = "New"

    elif (
        previous_amount > 0
        and latest_amount == 0
    ):

        comparison_status = "Dropped"

    elif latest_amount > previous_amount:

        comparison_status = "Growing"

    elif latest_amount < previous_amount:

        comparison_status = "Declining"

    else:

        comparison_status = "Existing"


    # -----------------------------------------------------
    # COMPARISON KPIs
    # -----------------------------------------------------

    comparison_kpis = st.columns(5)

    comparison_kpis[0].metric(
        "Previous Month",
        ringgit(previous_amount),
    )

    comparison_kpis[1].metric(
        "Latest Month",
        ringgit(latest_amount),
    )

    comparison_kpis[2].metric(
        "Change",
        f"RM {change_amount:+,.2f}",
    )

    comparison_kpis[3].metric(
        "Change %",
        (
            f"{change_percent:+.1f}%"
            if change_percent is not None
            else "N/A"
        ),
    )

    comparison_kpis[4].metric(
        "Status",
        comparison_status,
    )

    st.caption(
        f"Investigation: **{selected_sku}** | "
        f"{previous_month} → {latest_month}"
    )


# =========================================================
# MONTHLY SALES TREND
# =========================================================

st.divider()
st.subheader("📈 Monthly Sales Trend")

monthly_chart = px.line(
    monthly_sku,
    x="MONTH",
    y="AMT",
    markers=True,
    text="AMT",
    labels={
        "MONTH": "Month",
        "AMT": "Sales Amount (RM)",
    },
)

monthly_chart.update_traces(
    texttemplate="RM %{text:,.0f}",
    textposition="top center",
)

monthly_chart.update_layout(
    yaxis_title="Sales Amount (RM)",
    xaxis_title="Month",
    hovermode="x unified",
)

st.plotly_chart(
    monthly_chart,
    use_container_width=True,
)


# =========================================================
# MONTHLY DETAIL
# =========================================================

st.subheader("📋 Monthly Detail")

monthly_display = monthly_sku.copy()

monthly_display["AMT"] = (
    monthly_display["AMT"].map(ringgit)
)

monthly_display["MoM Growth %"] = (
    monthly_display["MoM Growth %"]
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
            "MoM Growth %",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# OUTLET PERFORMANCE
# =========================================================

st.divider()
st.subheader("🏪 Outlet Performance")

outlet_summary = (
    sku_data
    .groupby("OUTLET", as_index=False)
    .agg(
        QTY=("QTY", "sum"),
        AMT=("AMT", "sum"),
    )
    .sort_values(
        "AMT",
        ascending=False,
    )
)

total_outlet_amount = outlet_summary["AMT"].sum()

if total_outlet_amount > 0:

    outlet_summary["Sales Share %"] = (
        outlet_summary["AMT"]
        .div(total_outlet_amount)
        .mul(100)
    )

else:

    outlet_summary["Sales Share %"] = 0


outlet_chart = px.bar(
    outlet_summary.sort_values(
        "AMT",
        ascending=True,
    ),
    x="AMT",
    y="OUTLET",
    orientation="h",
    labels={
        "AMT": "Sales Amount (RM)",
        "OUTLET": "Outlet",
    },
    color="AMT",
    color_continuous_scale="Teal",
)

outlet_chart.update_layout(
    coloraxis_showscale=False,
)

st.plotly_chart(
    outlet_chart,
    use_container_width=True,
)

st.dataframe(
    outlet_summary.style.format(
        {
            "QTY": "{:,.0f}",
            "AMT": "RM {:,.2f}",
            "Sales Share %": "{:.1f}%",
        }
    ),
    use_container_width=True,
    hide_index=True,
)


# =========================================================
# OUTLET MONTH-TO-MONTH INVESTIGATION
# =========================================================

if len(available_months) >= 2:

    st.subheader("🏪 Outlet Investigation")

    outlet_monthly = (
        sku_data
        .groupby(
            ["OUTLET", "MONTH"],
            as_index=False,
        )["AMT"]
        .sum()
    )

    outlet_pivot = (
        outlet_monthly
        .pivot(
            index="OUTLET",
            columns="MONTH",
            values="AMT",
        )
        .reindex(columns=available_months)
        .fillna(0)
    )

    outlet_previous = (
        outlet_pivot[previous_month]
    )

    outlet_latest = (
        outlet_pivot[latest_month]
    )

    outlet_change = (
        outlet_latest - outlet_previous
    )

    outlet_change_percent = (
        outlet_change
        .div(
            outlet_previous.replace(0, pd.NA)
        )
        .mul(100)
    )

    outlet_investigation = pd.DataFrame(
        {
            "Outlet": outlet_pivot.index,
            "Previous Amount": outlet_previous.values,
            "Latest Amount": outlet_latest.values,
            "Change RM": outlet_change.values,
            "Change %": outlet_change_percent.values,
        }
    )

    outlet_investigation = (
        outlet_investigation
        .sort_values(
            "Change RM",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    outlet_change_chart = px.bar(
        outlet_investigation,
        x="Change RM",
        y="Outlet",
        orientation="h",
        color="Change RM",
        color_continuous_scale="RdYlGn",
        labels={
            "Change RM": "Change (RM)",
            "Outlet": "Outlet",
        },
    )

    outlet_change_chart.update_layout(
        coloraxis_showscale=False,
    )

    st.plotly_chart(
        outlet_change_chart,
        use_container_width=True,
    )

    st.dataframe(
        outlet_investigation.style.format(
            {
                "Previous Amount": "RM {:,.2f}",
                "Latest Amount": "RM {:,.2f}",
                "Change RM": "RM {:+,.2f}",
                "Change %": "{:+.1f}%",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# SUPPLIER INVESTIGATION
# =========================================================

if len(available_months) >= 2:

    st.divider()
    st.subheader("📦 Supplier Investigation")

    supplier_monthly = (
        sku_data
        .groupby(
            ["SUPPLIER", "MONTH"],
            as_index=False,
        )["AMT"]
        .sum()
    )

    supplier_pivot = (
        supplier_monthly
        .pivot(
            index="SUPPLIER",
            columns="MONTH",
            values="AMT",
        )
        .reindex(columns=available_months)
        .fillna(0)
    )

    supplier_previous = (
        supplier_pivot[previous_month]
    )

    supplier_latest = (
        supplier_pivot[latest_month]
    )

    supplier_change = (
        supplier_latest - supplier_previous
    )

    supplier_change_percent = (
        supplier_change
        .div(
            supplier_previous.replace(0, pd.NA)
        )
        .mul(100)
    )

    supplier_investigation = pd.DataFrame(
        {
            "Supplier": supplier_pivot.index,
            "Previous Amount": supplier_previous.values,
            "Latest Amount": supplier_latest.values,
            "Change RM": supplier_change.values,
            "Change %": supplier_change_percent.values,
        }
    )

    supplier_investigation = (
        supplier_investigation
        .sort_values(
            "Change RM",
            ascending=True,
        )
        .reset_index(drop=True)
    )

    supplier_chart = px.bar(
        supplier_investigation,
        x="Change RM",
        y="Supplier",
        orientation="h",
        color="Change RM",
        color_continuous_scale="RdYlGn",
        labels={
            "Change RM": "Change (RM)",
            "Supplier": "Supplier",
        },
    )

    supplier_chart.update_layout(
        coloraxis_showscale=False,
    )

    st.plotly_chart(
        supplier_chart,
        use_container_width=True,
    )

    st.dataframe(
        supplier_investigation.style.format(
            {
                "Previous Amount": "RM {:,.2f}",
                "Latest Amount": "RM {:,.2f}",
                "Change RM": "RM {:+,.2f}",
                "Change %": "{:+.1f}%",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# MANAGEMENT / INVESTIGATION INSIGHT
# =========================================================

st.divider()
st.subheader("💡 Management Insight")

summary_lines = []


# =========================================================
# OVERALL SKU INSIGHT
# =========================================================

if len(monthly_sku) >= 2:

    previous_month_overall = (
        monthly_sku["MONTH"].iloc[-2]
    )

    latest_month_overall = (
        monthly_sku["MONTH"].iloc[-1]
    )

    previous_amount_overall = (
        monthly_sku["AMT"].iloc[-2]
    )

    latest_amount_overall = (
        monthly_sku["AMT"].iloc[-1]
    )

    if previous_amount_overall != 0:

        latest_growth = (
            (
                latest_amount_overall
                - previous_amount_overall
            )
            / previous_amount_overall
            * 100
        )

    else:

        latest_growth = None


    if latest_growth is not None:

        if latest_growth > 0:

            summary_lines.append(
                f"🟢 **{selected_sku} is growing.** "
                f"Sales increased from "
                f"{ringgit(previous_amount_overall)} "
                f"in {previous_month_overall} "
                f"to {ringgit(latest_amount_overall)} "
                f"in {latest_month_overall}, "
                f"a **{latest_growth:+.1f}%** change."
            )

        elif latest_growth < 0:

            summary_lines.append(
                f"🔴 **{selected_sku} is declining.** "
                f"Sales decreased from "
                f"{ringgit(previous_amount_overall)} "
                f"in {previous_month_overall} "
                f"to {ringgit(latest_amount_overall)} "
                f"in {latest_month_overall}, "
                f"a **{latest_growth:+.1f}%** change."
            )

        else:

            summary_lines.append(
                f"🟡 **{selected_sku} is stable.** "
                f"Sales remained at approximately "
                f"{ringgit(latest_amount_overall)} "
                f"from {previous_month_overall} "
                f"to {latest_month_overall}."
            )

    else:

        summary_lines.append(
            f"ℹ️ **{selected_sku} had no sales in "
            f"{previous_month_overall}.** "
            f"Latest month sales are "
            f"{ringgit(latest_amount_overall)}."
        )


# =========================================================
# BEST OUTLET
# =========================================================

if not outlet_summary.empty:

    best_outlet = outlet_summary.iloc[0]

    summary_lines.append(
        f"🏆 **Top outlet:** "
        f"{best_outlet['OUTLET']} generated "
        f"{ringgit(best_outlet['AMT'])} "
        f"({best_outlet['Sales Share %']:.1f}% "
        f"of this SKU's sales)."
    )


# =========================================================
# BIGGEST OUTLET DECLINE / GROWTH
# =========================================================

if len(available_months) >= 2:

    outlet_declines = outlet_investigation[
        outlet_investigation["Change RM"] < 0
    ]

    outlet_growth = outlet_investigation[
        outlet_investigation["Change RM"] > 0
    ]

    if not outlet_declines.empty:

        biggest_outlet_decline = (
            outlet_declines.iloc[0]
        )

        summary_lines.append(
            f"🏪 **Largest outlet decline:** "
            f"{biggest_outlet_decline['Outlet']} "
            f"changed by "
            f"RM {biggest_outlet_decline['Change RM']:+,.2f}."
        )

    if not outlet_growth.empty:

        biggest_outlet_growth = (
            outlet_growth
            .sort_values(
                "Change RM",
                ascending=False,
            )
            .iloc[0]
        )

        summary_lines.append(
            f"📈 **Strongest outlet growth:** "
            f"{biggest_outlet_growth['Outlet']} "
            f"changed by "
            f"RM {biggest_outlet_growth['Change RM']:+,.2f}."
        )


# =========================================================
# DISPLAY INSIGHTS
# =========================================================

if summary_lines:

    for line in summary_lines:
        st.markdown(line)

else:

    st.info(
        "There is not enough historical data to generate "
        "management insights for this SKU."
    )