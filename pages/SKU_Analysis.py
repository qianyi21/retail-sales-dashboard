from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from app_data import load_data, apply_filters
from data_utils import ringgit


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="SKU Analysis",
    page_icon="🔎",
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
        return pd.to_datetime(
            month,
            format="%Y-%m",
        ).strftime("%b %Y")

    except Exception:
        return str(month)


def format_percentage(value) -> str:
    """
    Safely format percentage values.
    """
    if pd.isna(value):
        return "N/A"

    return f"{value:+.1f}%"


def style_status(value: str) -> str:
    """
    Apply simple colour styling to SKU status.
    """

    if value == "Growing":
        return "color: #15803D; font-weight: 600"

    if value == "Declining":
        return "color: #DC2626; font-weight: 600"

    if value == "New":
        return "color: #2563EB; font-weight: 600"

    if value == "Dropped":
        return "color: #EA580C; font-weight: 600"

    return "color: #6B7280"


# ============================================================
# LOAD DATA
# ============================================================

data = load_data()

filtered_data = apply_filters(data)


if filtered_data.empty:

    st.warning(
        "No rows match the current filters. "
        "Please select more values from the sidebar."
    )

    st.stop()


# ============================================================
# HEADER
# ============================================================

st.title("🔎 SKU Analysis")

st.caption(
    "Compare SKU sales between two months and identify "
    "growing, declining, new, and dropped products."
)


# ============================================================
# FILTER CONTEXT
# ============================================================

selected_months = sorted(
    filtered_data["MONTH"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

if selected_months:

    if len(selected_months) == 1:

        period_text = format_month(
            selected_months[0]
        )

    else:

        period_text = (
            f"{format_month(selected_months[0])}"
            f" – "
            f"{format_month(selected_months[-1])}"
        )

    st.info(
        f"📅 **Available period:** {period_text}  |  "
        f"**{filtered_data['SKU'].nunique():,} SKUs** "
        f"in the current filtered dataset."
    )


# ============================================================
# SKU MONTHLY DATA
# ============================================================

sku_monthly = (
    filtered_data
    .groupby(
        ["SKU", "MONTH"],
        as_index=False,
    )
    .agg(
        AMT=("AMT", "sum"),
        QTY=("QTY", "sum"),
    )
)


available_months = sorted(
    filtered_data["MONTH"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


# ============================================================
# COMPARISON PERIOD
# ============================================================

st.divider()

st.subheader("📅 Comparison Period")

if len(available_months) < 2:

    st.info(
        "Upload or select at least two months "
        "to compare SKU movement."
    )

    st.stop()


comparison_columns = st.columns(2)


# ------------------------------------------------------------
# Previous Month
# ------------------------------------------------------------

with comparison_columns[0]:

    comparison_previous_month = st.selectbox(
        "Previous Month",
        available_months,
        index=max(
            0,
            len(available_months) - 2,
        ),
        format_func=format_month,
        key="sku_analysis_previous_month",
    )


# ------------------------------------------------------------
# Latest Month
# ------------------------------------------------------------

latest_month_options = [
    month
    for month in available_months
    if month != comparison_previous_month
]


default_latest_index = 0

if available_months[-1] in latest_month_options:

    default_latest_index = (
        latest_month_options.index(
            available_months[-1]
        )
    )


with comparison_columns[1]:

    comparison_latest_month = st.selectbox(
        "Comparison Month",
        latest_month_options,
        index=default_latest_index,
        format_func=format_month,
        key="sku_analysis_latest_month",
    )


previous_month = comparison_previous_month

latest_month = comparison_latest_month


st.caption(
    f"Comparing **{format_month(previous_month)}** "
    f"→ **{format_month(latest_month)}**"
)


# ============================================================
# SKU × MONTH MATRIX
# ============================================================

sku_pivot = (
    sku_monthly
    .pivot(
        index="SKU",
        columns="MONTH",
        values="AMT",
    )
    .reindex(
        columns=available_months
    )
    .fillna(0)
)


previous_amounts = sku_pivot[
    previous_month
]

latest_amounts = sku_pivot[
    latest_month
]


# ============================================================
# CALCULATE CHANGES
# ============================================================

change_amount = (
    latest_amounts
    - previous_amounts
)


change_percent = (
    change_amount
    .div(
        previous_amounts.replace(
            0,
            pd.NA,
        )
    )
    .mul(100)
)


# ============================================================
# SKU STATUS
# ============================================================

status = pd.Series(
    "Existing",
    index=sku_pivot.index,
    dtype="object",
)


# New
status.loc[
    (previous_amounts == 0)
    & (latest_amounts > 0)
] = "New"


# Dropped
status.loc[
    (previous_amounts > 0)
    & (latest_amounts == 0)
] = "Dropped"


# Growing
status.loc[
    (previous_amounts > 0)
    & (latest_amounts > 0)
    & (latest_amounts > previous_amounts)
] = "Growing"


# Declining
status.loc[
    (previous_amounts > 0)
    & (latest_amounts > 0)
    & (latest_amounts < previous_amounts)
] = "Declining"


# Existing
status.loc[
    (previous_amounts > 0)
    & (latest_amounts > 0)
    & (latest_amounts == previous_amounts)
] = "Existing"


# ============================================================
# MOVEMENT DATAFRAME
# ============================================================

sku_movement = pd.DataFrame(
    {
        "SKU": sku_pivot.index,
        "Previous Sales": previous_amounts.values,
        "Latest Sales": latest_amounts.values,
        "Change RM": change_amount.values,
        "Change %": change_percent.values,
        "Status": status.values,
    }
)


sku_movement = (
    sku_movement
    .sort_values(
        "Change RM",
        ascending=False,
    )
    .reset_index(drop=True)
)


# ============================================================
# MOVEMENT SUMMARY
# ============================================================

status_counts = (
    sku_movement["Status"]
    .value_counts()
    .reindex(
        [
            "Growing",
            "Declining",
            "New",
            "Dropped",
            "Existing",
        ],
        fill_value=0,
    )
)


st.subheader("📌 SKU Movement Summary")


summary_columns = st.columns(5)


summary_columns[0].metric(
    "🚀 Growing",
    f"{status_counts['Growing']:,}",
)


summary_columns[1].metric(
    "📉 Declining",
    f"{status_counts['Declining']:,}",
)


summary_columns[2].metric(
    "🆕 New",
    f"{status_counts['New']:,}",
)


summary_columns[3].metric(
    "⚠️ Dropped",
    f"{status_counts['Dropped']:,}",
)


summary_columns[4].metric(
    "➖ Existing",
    f"{status_counts['Existing']:,}",
)


# ============================================================
# TOP MOVERS CHART
# ============================================================

st.divider()

st.subheader("📊 Biggest SKU Sales Changes")


top_increases = (
    sku_movement[
        sku_movement["Status"] == "Growing"
    ]
    .sort_values(
        "Change RM",
        ascending=False,
    )
    .head(5)
)


top_declines = (
    sku_movement[
        sku_movement["Status"] == "Declining"
    ]
    .sort_values(
        "Change RM",
        ascending=True,
    )
    .head(5)
)


chart_data = pd.concat(
    [
        top_increases,
        top_declines,
    ],
    ignore_index=True,
)


if chart_data.empty:

    st.info(
        "No growing or declining SKUs were found "
        "for this comparison."
    )

else:

    chart_data = (
        chart_data
        .sort_values("Change RM")
    )

    chart = px.bar(
        chart_data,
        x="Change RM",
        y="SKU",
        orientation="h",
        color="Change RM",
        color_continuous_scale=[
            "#DC2626",
            "#F3F4F6",
            "#16A34A",
        ],
        labels={
            "Change RM": "Sales Change (RM)",
            "SKU": "SKU",
        },
    )

    chart.update_layout(
        coloraxis_showscale=False,
        height=450,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=20,
        ),
        xaxis_title="Sales Change (RM)",
        yaxis_title="",
    )

    chart.update_traces(
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Change: RM %{x:,.2f}"
            "<extra></extra>"
        )
    )

    st.plotly_chart(
        chart,
        use_container_width=True,
    )


# ============================================================
# FULL SKU MOVEMENT
# ============================================================

st.divider()

st.subheader("📋 SKU Movement Details")

st.caption(
    "Use the table below to investigate the movement "
    "of every SKU in the selected comparison."
)


movement_display = sku_movement.copy()


movement_display["Previous Sales"] = (
    movement_display["Previous Sales"]
    .map(ringgit)
)


movement_display["Latest Sales"] = (
    movement_display["Latest Sales"]
    .map(ringgit)
)


movement_display["Change RM"] = (
    movement_display["Change RM"]
    .map(
        lambda value:
        f"RM {value:+,.2f}"
    )
)


movement_display["Change %"] = (
    movement_display["Change %"]
    .map(format_percentage)
)


styled_movement = (
    movement_display
    .style
    .map(
        style_status,
        subset=["Status"],
    )
)


st.dataframe(
    styled_movement,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# TOP GROWING SKUs
# ============================================================

st.divider()

st.subheader(
    f"🚀 Top Growing SKUs"
)

growing_skus = (
    sku_movement[
        sku_movement["Status"] == "Growing"
    ]
    .sort_values(
        "Change RM",
        ascending=False,
    )
    .head(10)
)


if growing_skus.empty:

    st.info(
        "No growing SKUs found for this comparison."
    )

else:

    growing_display = growing_skus.copy()

    growing_display["Previous Sales"] = (
        growing_display["Previous Sales"]
        .map(ringgit)
    )

    growing_display["Latest Sales"] = (
        growing_display["Latest Sales"]
        .map(ringgit)
    )

    growing_display["Change RM"] = (
        growing_display["Change RM"]
        .map(
            lambda value:
            f"RM {value:+,.2f}"
        )
    )

    growing_display["Change %"] = (
        growing_display["Change %"]
        .map(format_percentage)
    )

    st.dataframe(
        growing_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TOP DECLINING SKUs
# ============================================================

st.subheader(
    f"📉 Top Declining SKUs"
)


declining_skus = (
    sku_movement[
        sku_movement["Status"] == "Declining"
    ]
    .sort_values(
        "Change RM",
        ascending=True,
    )
    .head(10)
)


if declining_skus.empty:

    st.info(
        "No declining SKUs found for this comparison."
    )

else:

    declining_display = declining_skus.copy()

    declining_display["Previous Sales"] = (
        declining_display["Previous Sales"]
        .map(ringgit)
    )

    declining_display["Latest Sales"] = (
        declining_display["Latest Sales"]
        .map(ringgit)
    )

    declining_display["Change RM"] = (
        declining_display["Change RM"]
        .map(
            lambda value:
            f"RM {value:+,.2f}"
        )
    )

    declining_display["Change %"] = (
        declining_display["Change %"]
        .map(format_percentage)
    )

    st.dataframe(
        declining_display,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# NEW + DROPPED
# ============================================================

st.divider()

movement_columns = st.columns(2)


# ------------------------------------------------------------
# New SKUs
# ------------------------------------------------------------

with movement_columns[0]:

    st.subheader(
        f"🆕 New SKUs in {format_month(latest_month)}"
    )

    new_skus = (
        sku_movement[
            sku_movement["Status"] == "New"
        ]
        .sort_values(
            "Latest Sales",
            ascending=False,
        )
        .head(10)
    )

    if new_skus.empty:

        st.info(
            "No new SKUs found."
        )

    else:

        new_display = new_skus.copy()

        new_display["Latest Sales"] = (
            new_display["Latest Sales"]
            .map(ringgit)
        )

        new_display["Change RM"] = (
            new_display["Change RM"]
            .map(
                lambda value:
                f"RM {value:+,.2f}"
            )
        )

        new_display["Change %"] = (
            new_display["Change %"]
            .map(format_percentage)
        )

        st.dataframe(
            new_display[
                [
                    "SKU",
                    "Latest Sales",
                    "Status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# ------------------------------------------------------------
# Dropped SKUs
# ------------------------------------------------------------

with movement_columns[1]:

    st.subheader(
        f"⚠️ Dropped SKUs in {format_month(latest_month)}"
    )

    dropped_skus = (
        sku_movement[
            sku_movement["Status"] == "Dropped"
        ]
        .sort_values(
            "Previous Sales",
            ascending=False,
        )
        .head(10)
    )

    if dropped_skus.empty:

        st.info(
            "No dropped SKUs found."
        )

    else:

        dropped_display = dropped_skus.copy()

        dropped_display["Previous Sales"] = (
            dropped_display["Previous Sales"]
            .map(ringgit)
        )

        dropped_display["Change RM"] = (
            dropped_display["Change RM"]
            .map(
                lambda value:
                f"RM {value:+,.2f}"
            )
        )

        dropped_display["Change %"] = (
            dropped_display["Change %"]
            .map(format_percentage)
        )

        st.dataframe(
            dropped_display[
                [
                    "SKU",
                    "Previous Sales",
                    "Status",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

# ============================================================
# MANAGEMENT INSIGHTS
# ============================================================

st.divider()

st.subheader("💡 Management Insights")


insights = []


# ------------------------------------------------------------
# Biggest increases - Top 2
# ------------------------------------------------------------

if not top_increases.empty:

    for _, row in top_increases.head().iterrows():

        insights.append(
            f"🚀 **{row['SKU']}** recorded a significant "
            f"sales increase of **{ringgit(row['Change RM'])}** "
            f"({format_percentage(row['Change %'])})."
        )


# ------------------------------------------------------------
# Biggest declines - Top 2
# ------------------------------------------------------------

if not top_declines.empty:

    for _, row in top_declines.head().iterrows():

        insights.append(
            f"📉 **{row['SKU']}** recorded a significant "
            f"sales decline of **{ringgit(abs(row['Change RM']))}** "
            f"({format_percentage(row['Change %'])})."
        )


# ------------------------------------------------------------
# New SKUs - Top 2
# ------------------------------------------------------------

if not new_skus.empty:

    for _, row in new_skus.head().iterrows():

        insights.append(
            f"🆕 **{row['SKU']}** is one of the highest-selling "
            f"new SKUs in {format_month(latest_month)}, "
            f"with sales of **{ringgit(row['Latest Sales'])}**."
        )


# ------------------------------------------------------------
# Dropped SKUs - Top 2
# ------------------------------------------------------------

if not dropped_skus.empty:

    for _, row in dropped_skus.head().iterrows():

        insights.append(
            f"⚠️ **{row['SKU']}** is one of the most significant "
            f"dropped SKUs, with previous-month sales of "
            f"**{ringgit(row['Previous Sales'])}**."
        )


# ------------------------------------------------------------
# Overall movement
# ------------------------------------------------------------

total_previous = sku_movement[
    "Previous Sales"
].sum()


total_latest = sku_movement[
    "Latest Sales"
].sum()


overall_change = (
    total_latest
    - total_previous
)


if total_previous != 0:

    overall_growth = (
        overall_change
        / total_previous
        * 100
    )

    if overall_growth > 0:

        insights.append(
            f"📈 Overall SKU sales increased by "
            f"**{format_percentage(overall_growth)}** "
            f"between the selected months."
        )

    elif overall_growth < 0:

        insights.append(
            f"📉 Overall SKU sales decreased by "
            f"**{format_percentage(overall_growth)}** "
            f"between the selected months."
        )

    else:

        insights.append(
            "➖ Overall SKU sales remained unchanged "
            "between the selected months."
        )


# ------------------------------------------------------------
# Display insights
# ------------------------------------------------------------

if insights:

    for insight in insights:

        st.markdown(
            f"- {insight}"
        )

else:

    st.info(
        "There are not enough changes in the selected "
        "period to generate management insights."
    )
