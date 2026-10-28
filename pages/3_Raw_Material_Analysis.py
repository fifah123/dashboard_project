
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.cleaning import (
    clean_column_names,
    clean_numeric_column,
    format_idr,
    format_idr_compact,
    normalize_sku
)
from utils.loader import load_material_data
# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "FruitsTrxDatasets.xlsx"

# ============================================================
# LOAD DATA
# ============================================================


try:
    modified_time = EXCEL_PATH.stat().st_mtime
    df = load_material_data(str(EXCEL_PATH), modified_time)

except Exception as exc:
    st.error(f"Unable to load raw material data: {exc}")
    st.info(
        "Check the workbook location, sheet names, and required columns."
    )
    st.stop()

if df.empty:
    st.warning("No valid raw material records were found.")
    st.stop()


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🌱 Raw Material Analysis")
st.caption(
    "Monitor raw material prices, price movements, harvest conditions, "
    "and their relationship with production costs."
)


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("🔎 Raw Material Filters")

min_date = df["Date"].min().date()
max_date = df["Date"].max().date()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

if start_date > end_date:
    st.sidebar.error("Start date must not be later than end date.")
    st.stop()

product_options = sorted(df["Product"].dropna().unique().tolist())
selected_products = st.sidebar.multiselect(
    "Product",
    options=product_options,
    default=product_options,
)

category_options = sorted(df["Category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Category",
    options=category_options,
    default=category_options,
)

season_options = sorted(df["Season Status"].dropna().unique().tolist())
selected_seasons = st.sidebar.multiselect(
    "Season status",
    options=season_options,
    default=season_options,
)


# ============================================================
# APPLY FILTERS
# ============================================================

filtered = df[
    (df["Date"].dt.date >= start_date)
    & (df["Date"].dt.date <= end_date)
    & (df["Product"].isin(selected_products))
    & (df["Category"].isin(selected_categories))
    & (df["Season Status"].isin(selected_seasons))
].copy()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

filtered = filtered.sort_values(["SKU", "Date"])

# ============================================================
# KPI CALCULATIONS — IMPROVED ACCURACY
# ============================================================

# Use valid close-price observations for the latest-price KPI.
valid_prices = filtered.dropna(
    subset=["Date", "SKU", "Close Price"]
).copy()

if valid_prices.empty:
    st.warning("No valid close-price data is available.")
    st.stop()

valid_prices = valid_prices.sort_values(["SKU", "Date"])

# 1. Latest average close price:
# Average prices recorded on the latest date in the filtered data.
latest_date = valid_prices["Date"].max()

latest_prices = valid_prices.loc[
    valid_prices["Date"].eq(latest_date),
    ["SKU", "Close Price"],
]

latest_avg_price = (
    latest_prices["Close Price"].mean()
    if not latest_prices.empty
    else 0.0
)

# 2. Price change per SKU:
# Compare each SKU's first and last valid close price.
first_prices = (
    valid_prices.groupby("SKU", as_index=False)
    .first()[["SKU", "Date", "Close Price"]]
    .rename(
        columns={
            "Date": "First Date",
            "Close Price": "First Close Price",
        }
    )
)

last_prices = (
    valid_prices.groupby("SKU", as_index=False)
    .last()[["SKU", "Date", "Close Price"]]
    .rename(
        columns={
            "Date": "Last Date",
            "Close Price": "Last Close Price",
        }
    )
)

price_comparison = first_prices.merge(
    last_prices,
    on="SKU",
    how="inner",
    validate="one_to_one",
)

# Exclude zero starting prices because percentage change
# cannot be calculated meaningfully from a zero baseline.
price_comparison = price_comparison.loc[
    price_comparison["First Close Price"].ne(0)
].copy()

price_comparison["Change (%)"] = (
    (
        price_comparison["Last Close Price"]
        - price_comparison["First Close Price"]
    )
    / price_comparison["First Close Price"]
    * 100
)

valid_changes = price_comparison["Change (%)"].dropna()

avg_price_change = (
    valid_changes.mean()
    if not valid_changes.empty
    else None
)

# 3. Product count:
# Count distinct SKUs represented in the filtered records.
unique_products = filtered["SKU"].nunique()

# 4. Peak-season share:
# Exclude unknown/missing season labels from the denominator.
known_seasons = filtered[
    filtered["Season Status"].isin(
        ["Peak Season", "Off-Peak Season"]
    )
]

peak_season_share = (
    known_seasons["Season Status"].eq("Peak Season").mean() * 100
    if not known_seasons.empty
    else None
)


# ============================================================
# KPI CARDS — IMPROVED ACCURACY
# ============================================================

st.subheader("Raw Material Overview")

k1, k2, k3, k4 = st.columns(4)

k1.metric(
    "Latest Avg. Close Price",
    format_idr_compact(latest_avg_price),
    help=(
        f"Average close price on {latest_date:%d %b %Y}, "
        "using available SKU observations on that date."
    ),
)

k2.metric(
    "Average Price Change",
    (
        f"{avg_price_change:+.2f}%"
        if avg_price_change is not None
        else "N/A"
    ),
    help=(
        "Arithmetic mean of each SKU's percentage change between "
        "its first and last valid close prices in the selected period. "
        "SKUs with a zero starting price are excluded."
    ),
)

k3.metric(
    "Products Monitored",
    f"{unique_products:,}",
    help="Number of distinct SKUs in the filtered records.",
)

k4.metric(
    "Peak Season Records",
    (
        f"{peak_season_share:.1f}%"
        if peak_season_share is not None
        else "N/A"
    ),
    help=(
        "Percentage of records labeled Peak Season among records "
        "classified as Peak Season or Off-Peak Season. "
        "Unknown labels are excluded."
    ),
)

# ============================================================
# PRICE TREND
# ============================================================

st.divider()
st.subheader("📈 Raw Material Price Trend")

available_prices = [
    column
    for column in ["Open Price", "Close Price", "Moving Avg (3)"]
    if column in filtered.columns
    and filtered[column].notna().any()
]

if available_prices:
    price_trend = (
        filtered.groupby(
            ["Date", "SKU", "Product"],
            as_index=False,
        )[available_prices]
        .mean()
        .sort_values("Date")
    )

    selected_price_metric = st.selectbox(
        "Price metric",
        options=available_prices,
        index=available_prices.index("Close Price")
        if "Close Price" in available_prices
        else 0,
    )

    fig_price = px.line(
        price_trend,
        x="Date",
        y=selected_price_metric,
        color="Product",
        markers=True,
        title=f"{selected_price_metric} Over Time",
        labels={
            "Date": "Date",
            selected_price_metric: "Price (IDR)",
            "Product": "Product",
        },
    )

    fig_price.update_layout(
        yaxis=dict(
            title="Price (IDR)",
            tickformat="~s",
        ),
        xaxis_title="Date",
        legend_title="Product",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(fig_price, use_container_width=True)
else:
    st.info("No usable price series is available.")


# ============================================================
# PRICE CHANGE ANALYSIS
# ============================================================

st.divider()
st.subheader("📊 Price Change Analysis")

change_col = "Open-Close Change (%)"

if change_col in filtered.columns and filtered[change_col].notna().any():
    change_data = (
        filtered.groupby("Product", as_index=False)[change_col]
        .mean()
        .sort_values(change_col, ascending=True)
    )

    fig_change = px.bar(
        change_data,
        x=change_col,
        y="Product",
        orientation="h",
        color=change_col,
        color_continuous_scale="RdYlGn",
        title="Average Open-to-Close Price Change by Product",
        labels={
            change_col: "Price Change (%)",
            "Product": "Product",
        },
    )

    fig_change.add_vline(
        x=0,
        line_dash="dash",
        line_color="gray",
    )

    fig_change.update_layout(
        coloraxis_showscale=False,
        xaxis_ticksuffix="%",
        margin=dict(l=20, r=20, t=60, b=20),
    )

    st.plotly_chart(fig_change, use_container_width=True)
else:
    st.info("The Open-Close Change (%) field has no usable data.")


# ============================================================
# HARVEST SUCCESS AND SEASONALITY
# ============================================================

st.divider()
st.subheader("🌾 Harvest Conditions & Seasonality")

harvest_col, season_col = st.columns(2)

harvest_column = "Harvest Success Rate (%)"

with harvest_col:
    if (
        harvest_column in filtered.columns
        and filtered[harvest_column].notna().any()
    ):
        harvest_data = (
            filtered.groupby("Date", as_index=False)[harvest_column]
            .mean()
            .sort_values("Date")
        )

        fig_harvest = px.line(
            harvest_data,
            x="Date",
            y=harvest_column,
            markers=True,
            title="Harvest Success Rate Over Time",
            labels={
                "Date": "Date",
                harvest_column: "Harvest Success Rate (%)",
            },
        )

        fig_harvest.update_layout(
            yaxis_ticksuffix="%",
            margin=dict(l=20, r=20, t=60, b=20),
        )

        st.plotly_chart(fig_harvest, use_container_width=True)
    else:
        st.info("Harvest success rate data is unavailable.")

with season_col:
    season_data = (
        filtered.groupby("Season Status", as_index=False)
        .size()
        .rename(columns={"size": "Records"})
    )

    fig_season = px.pie(
        season_data,
        names="Season Status",
        values="Records",
        hole=0.45,
        title="Records by Season Status",
    )

    fig_season.update_traces(
        texttemplate="%{label}<br>%{percent}",
        hovertemplate=(
            "%{label}<br>"
            "Records: %{value}<br>"
            "Share: %{percent}<extra></extra>"
        ),
    )

    st.plotly_chart(fig_season, use_container_width=True)


# ============================================================
# RAW MATERIAL COST ANALYSIS
# ============================================================

st.divider()
st.subheader("💸 Raw Material Cost Analysis")

try:
    transactions = pd.read_excel(
        EXCEL_PATH,
        sheet_name="SalesTransaction",
        engine="openpyxl",
    )
    transactions = clean_column_names(transactions)

    date_col = next(
        (
            column for column in [
                "TranscationDate",
                "TransactionDate",
                "Transaction Date",
            ]
            if column in transactions.columns
        ),
        None,
    )

    if date_col is None:
        st.info(
            "Could not find the transaction date column in "
            "SalesTransaction. Cost analysis is unavailable."
        )
    elif "SKU" not in transactions.columns:
        st.info(
            "Could not find SKU in SalesTransaction. "
            "Cost analysis is unavailable."
        )
    else:
        transactions["SKU"] = normalize_sku(transactions["SKU"])
        transactions["TransactionDate"] = pd.to_datetime(
            transactions[date_col],
            errors="coerce",
        )

        cost_col = "TotalRawMaterialCost"

        if cost_col not in transactions.columns:
            st.info(
                "TotalRawMaterialCost is not available in "
                "SalesTransaction."
            )
        else:
            transactions = clean_numeric_column(
                transactions,
                cost_col,
                default=0,
            )

            transactions = transactions.dropna(
                subset=["TransactionDate", "SKU"]
            )

            transactions = transactions[
                (transactions["TransactionDate"].dt.date >= start_date)
                & (transactions["TransactionDate"].dt.date <= end_date)
                & (transactions["SKU"].isin(filtered["SKU"].unique()))
            ].copy()

            transactions["Month"] = (
                transactions["TransactionDate"]
                .dt.to_period("M")
                .dt.to_timestamp()
            )

            cost_by_month = (
                transactions.groupby("Month", as_index=False)[cost_col]
                .sum()
                .sort_values("Month")
            )

            cost_by_product = (
                transactions.groupby("SKU", as_index=False)[cost_col]
                .sum()
                .merge(
                    filtered[["SKU", "Product"]].drop_duplicates("SKU"),
                    on="SKU",
                    how="left",
                )
                .sort_values(cost_col, ascending=False)
            )

            cost_kpi1, cost_kpi2 = st.columns(2)

            cost_kpi1.metric(
                "Total Raw Material Cost",
                format_idr_compact(transactions[cost_col].sum()),
            )

            cost_kpi2.metric(
                "Average Monthly Cost",
                format_idr_compact(
                    cost_by_month[cost_col].mean()
                    if not cost_by_month.empty
                    else 0
                ),
            )

            cost_chart1, cost_chart2 = st.columns(2)

            with cost_chart1:
                fig_cost_month = px.bar(
                    cost_by_month,
                    x="Month",
                    y=cost_col,
                    title="Monthly Raw Material Cost",
                    labels={
                        "Month": "Month",
                        cost_col: "Cost (IDR)",
                    },
                )

                fig_cost_month.update_layout(
                    yaxis_tickformat="~s",
                    margin=dict(l=20, r=20, t=60, b=20),
                )

                st.plotly_chart(
                    fig_cost_month,
                    use_container_width=True,
                )

            with cost_chart2:
                fig_cost_product = px.bar(
                    cost_by_product.sort_values(cost_col),
                    x=cost_col,
                    y="Product",
                    orientation="h",
                    title="Raw Material Cost by Product",
                    labels={
                        cost_col: "Cost (IDR)",
                        "Product": "Product",
                    },
                )

                fig_cost_product.update_layout(
                    xaxis_tickformat="~s",
                    margin=dict(l=20, r=20, t=60, b=20),
                )

                st.plotly_chart(
                    fig_cost_product,
                    use_container_width=True,
                )

except Exception as exc:
    st.warning(f"Unable to calculate raw material costs: {exc}")


# ============================================================
# DETAILED RAW MATERIAL TABLE
# ============================================================

st.divider()
st.subheader("📋 Raw Material Data")

display_columns = [
    "Date",
    "SKU",
    "Product",
    "Category",
    "Open Price",
    "Close Price",
    "Open-Close Change (%)",
    "Moving Avg (3)",
    "Harvest Success Rate (%)",
    "Season Status",
]

display_columns = [
    column for column in display_columns
    if column in filtered.columns
]

detail = filtered[display_columns].copy()

for column in ["Open Price", "Close Price", "Moving Avg (3)"]:
    if column in detail.columns:
        detail[column] = detail[column].map(
            lambda value: format_idr(value)
            if pd.notna(value)
            else ""
        )

st.dataframe(
    detail.sort_values("Date", ascending=False),
    use_container_width=True,
    hide_index=True,
)

csv_data = filtered.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="⬇️ Download Raw Material Report (CSV)",
    data=csv_data,
    file_name="ggf_raw_material_analysis.csv",
    mime="text/csv",
)

st.caption(
    "GGF Beverage Dashboard | Raw Material Analysis"
)
