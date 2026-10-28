
from pathlib import Path

import re

import pandas as pd

import plotly.express as px

import plotly.graph_objects as go

import streamlit as st

# ============================================================

# PAGE CONFIGURATION

# ============================================================

st.set_page_config(

    page_title="Sales Performance | GGF Beverage",

    page_icon="🥤",

    layout="wide",

)

st.title("🥤 GGF Beverage Dashboard")

st.subheader("Page 1 — Sales Performance")

st.caption(

    "Monitor revenue, sales target achievement, product performance, "

    "discount impact, and profitability."

)

# ============================================================

# CONFIGURATION

# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

EXCEL_PATH = BASE_DIR / "FruitsTrxDatasets.xlsx"

SHEET_PRODUCT = "MstProduct"

SHEET_TARGET = "SalesTarget"

SHEET_TRANSACTION = "SalesTransaction"

# ============================================================

# DATA CLEANING HELPERS

# ============================================================

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:

    df = df.copy()

    df.columns = [

        re.sub(r"\s+", " ", str(col).replace("\xa0", " ")).strip()

        for col in df.columns

    ]

    return df

def normalize_sku(series: pd.Series) -> pd.Series:

    result = series.astype("string").str.strip()

    return result.str.replace(r"\.0$", "", regex=True)

def parse_number(value):

    """Parse numeric values and Indonesian/English formatted numbers."""

    if pd.isna(value):

        return 0.0

    if isinstance(value, (int, float)):

        return float(value)

    text = str(value).strip()

    text = (

        text.replace("\xa0", "")

        .replace(" ", "")

        .replace("Rp", "")

        .replace("IDR", "")

    )

    if text in {"", "-", "nan", "None"}:

        return 0.0

    is_negative = text.startswith("(") and text.endswith(")")

    if is_negative:

        text = text[1:-1]

    text = re.sub(r"[^0-9,.\-]", "", text)

    if not text or text in {"-", ".", ","}:

        return 0.0

    if "," in text and "." in text:

        if text.rfind(",") > text.rfind("."):

            text = text.replace(".", "").replace(",", ".")

        else:

            text = text.replace(",", "")

    elif "," in text:

        parts = text.split(",")

        if len(parts) == 2 and len(parts[1]) in (1, 2):

            text = text.replace(",", ".")

        else:

            text = text.replace(",", "")

    elif "." in text:

        parts = text.split(".")

        if len(parts) > 2:

            text = text.replace(".", "")

        elif len(parts) == 2 and len(parts[1]) == 3:

            text = text.replace(".", "")

    try:

        number = float(text)

        return -abs(number) if is_negative else number

    except ValueError:

        return 0.0

def clean_numeric_column(

    df: pd.DataFrame,

    columns: list[str],

) -> pd.DataFrame:

    df = df.copy()

    for col in columns:

        if col in df.columns:

            df[col] = df[col].map(parse_number)

    return df

def format_idr(value) -> str:

    return f"Rp {value:,.0f}".replace(",", ".")

def format_idr_compact(value):

    value = float(value or 0)

    abs_value = abs(value)

    if abs_value >= 1_000_000_000:

        return f"Rp {value / 1_000_000_000:,.2f} B"

    if abs_value >= 1_000_000:

        return f"Rp {value / 1_000_000:,.2f} M"

    if abs_value >= 1_000:

        return f"Rp {value / 1_000:,.1f} K"

    return f"Rp {value:,.0f}"

def format_percent(value) -> str:

    if pd.isna(value):

        return "N/A"

    return f"{value:.1f}%"

def render_top3_sku_section(filtered_sales: pd.DataFrame) -> None:
    """Render a Top 3 SKU profitability chart and full-width summary cards."""
    st.markdown("### 3. Top 3 SKU: Profitability & Discounts")

    agg_metrics = {
        "UnitsSold": ("Qty", "sum"),
        "GrossSales": ("TotalSellingPrice", "sum"),
        "Discounts": ("TotalDiscount", "sum"),
        "NetSales": ("TotalNetSellingPrice", "sum"),
    }
    if "Profit&Lost" in filtered_sales.columns:
        agg_metrics["Profit"] = ("Profit&Lost", "sum")
    if "TotalCost" in filtered_sales.columns:
        agg_metrics["TotalCost"] = ("TotalCost", "sum")

    top3_sku = (
        filtered_sales.groupby(["SKU", "Product"], as_index=False)
        .agg(**agg_metrics)
        .sort_values("NetSales", ascending=False)
        .head(3)
        .copy()
    )
    if top3_sku.empty:
        st.info("No product data available for this selection.")
        return

    top3_sku["DiscountRatePct"] = (
        top3_sku["Discounts"]
        .div(top3_sku["GrossSales"].where(top3_sku["GrossSales"] != 0))
        .mul(100)
    )
    if "Profit" in top3_sku.columns:
        top3_sku["ProfitMarginPct"] = (
            top3_sku["Profit"]
            .div(top3_sku["NetSales"].where(top3_sku["NetSales"] != 0))
            .mul(100)
        )

    # Compare discount rate and profit margin.
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=top3_sku["Product"], y=top3_sku["DiscountRatePct"],
        name="Discount Rate",
        hovertemplate="%{x}<br>Discount Rate: %{y:.2f}%<extra></extra>",
    ))
    if "ProfitMarginPct" in top3_sku.columns:
        fig.add_trace(go.Bar(
            x=top3_sku["Product"], y=top3_sku["ProfitMarginPct"],
            name="Profit Margin",
            hovertemplate="%{x}<br>Profit Margin: %{y:.2f}%<extra></extra>",
        ))
    fig.update_layout(
        barmode="group", height=400, xaxis_title="Product",
        yaxis_title="Percentage (%)", yaxis_ticksuffix="%",
        legend_title="Metric", margin=dict(l=10, r=10, t=30, b=70),
    )
    st.plotly_chart(fig, width="stretch", key="top3_sku_profitability")

    # Full-width cards are placed below the chart, not in a half-width column.
    st.markdown("#### Top 3 Product Summary")
    card_cols = st.columns(len(top3_sku), gap="medium")
    for rank, (_, row) in enumerate(top3_sku.iterrows(), start=1):
        with card_cols[rank - 1]:
            with st.container(border=True):
                st.caption(f"TOP PRODUCT #{rank}")
                st.markdown(f"**{row['Product']}**")
                st.caption(f"SKU: {row['SKU']}")
                st.metric("Net Sales", format_idr_compact(row["NetSales"]))
                st.metric("Units Sold", f"{row['UnitsSold']:,.0f}")
                st.metric("Discount Rate", format_percent(row["DiscountRatePct"]))

                if "Profit" in top3_sku.columns:
                    st.metric("Profit / Loss", format_idr_compact(row["Profit"]))
                    margin = row["ProfitMarginPct"]
                    st.metric("Profit Margin", format_percent(margin))
                    if pd.isna(margin):
                        status = "Margin unavailable"
                    elif margin < 0:
                        status = "Loss-making"
                    elif margin < 10:
                        status = "Low margin"
                    else:
                        status = "Positive margin"
                    st.caption(f"Status: **{status}**")

                if "TotalCost" in top3_sku.columns:
                    cost = row["TotalCost"]
                    st.caption(
                        "Total Cost: " + (
                            format_idr_compact(cost) if pd.notna(cost) else "N/A"
                        )
                    )

    st.caption(
        "Ranked by net sales. Profit margin is Profit / Net Sales × 100%. "
        "The 10% low-margin threshold is illustrative."
    )

# ============================================================

# LOAD EXCEL DATA

# ============================================================

@st.cache_data(show_spinner="Loading sales data...")

def load_data(file_path: str, modified_time: float):

    product = pd.read_excel(file_path, sheet_name=SHEET_PRODUCT)

    target = pd.read_excel(file_path, sheet_name=SHEET_TARGET)

    sales = pd.read_excel(file_path, sheet_name=SHEET_TRANSACTION)

    product = clean_column_names(product)

    target = clean_column_names(target)

    sales = clean_column_names(sales)

    required_columns = {

        "MstProduct": {

            "SKU", "ShortDescription", "Category", "Price"

        },

        "SalesTarget": {"Period", "SKU", "SalesTarget"},

        "SalesTransaction": {

            "TranscationDate",

            "SKU",

            "Qty",

            "TotalNetSellingPrice",

            "TotalDiscount",

            "Outlet",

        },

    }

    for name, df, required in [

        ("MstProduct", product, required_columns["MstProduct"]),

        ("SalesTarget", target, required_columns["SalesTarget"]),

        ("SalesTransaction", sales, required_columns["SalesTransaction"]),

    ]:

        missing = required.difference(df.columns)

        if missing:

            raise ValueError(

                f"Missing columns in {name}: {sorted(missing)}"

            )

    # Normalize product identifiers.

    product["SKU"] = normalize_sku(product["SKU"])

    target["SKU"] = normalize_sku(target["SKU"])

    sales["SKU"] = normalize_sku(sales["SKU"])

    # Convert dates.

    if "CreationDate" in product.columns:

        product["CreationDate"] = pd.to_datetime(

            product["CreationDate"], errors="coerce"

        )

    target["Period"] = pd.to_datetime(

        target["Period"], errors="coerce"

    )

    sales["TranscationDate"] = pd.to_datetime(

        sales["TranscationDate"], errors="coerce"

    )

    # Convert numeric columns.

    product = clean_numeric_column(product, ["Price"])

    target = clean_numeric_column(target, ["SalesTarget"])

    sales = clean_numeric_column(

        sales,

        [

            "Qty",

            "SellingPrice",

            "TotalSellingPrice",

            "Discount",

            "TotalDiscount",

            "TotalNetSellingPrice",

            "RawMaterialCost",

            "TotalRawMaterialCost",

            "ProductionCost",

            "TotalProductionCost",

            "TotalCost",

            "Profit&Lost",

        ],

    )

    # Remove invalid records.

    sales = sales.dropna(

        subset=["TranscationDate", "SKU"]

    ).copy()

    target = target.dropna(

        subset=["Period", "SKU"]

    ).copy()

    # Aggregate target records by SKU and month.

    target["Month"] = target["Period"].dt.to_period("M")

    target = (

        target.groupby(["Month", "SKU"], as_index=False)

        .agg(SalesTarget=("SalesTarget", "sum"))

    )

    # Prevent duplicate product master rows from multiplying sales.

    product = product.drop_duplicates(

        subset=["SKU"], keep="last"

    ).copy()

    # Join product metadata to sales transactions.

    product_columns = [

        col for col in [

            "SKU",

            "Description",

            "ShortDescription",

            "Category",

            "CategoryCode",

            "UOM",

            "Price",

        ]

        if col in product.columns

    ]

    sales = sales.merge(

        product[product_columns],

        on="SKU",

        how="left",

        validate="many_to_one",

    )

    # Use a consistent product name.

    product_name = sales["ShortDescription"].fillna(

        sales["SKU"]

    )

    if "Description" in sales.columns:

        product_name = sales["ShortDescription"].fillna(

            sales["Description"]

        ).fillna(sales["SKU"])

    sales["Product"] = product_name

    sales["Outlet"] = sales["Outlet"].fillna("Unknown")

    sales["Month"] = sales["TranscationDate"].dt.to_period("M")

    return sales, target, product

# ============================================================

# LOAD AND VALIDATE

# ============================================================

if not EXCEL_PATH.exists():

    st.error(

        f"Workbook not found: {EXCEL_PATH}\n\n"

        "Place FruitsTrxDatasets.xlsx in the project root, "

        "beside app.py."

    )

    st.stop()

try:

    sales_df, target_df, product_df = load_data(

        str(EXCEL_PATH),

        EXCEL_PATH.stat().st_mtime,

    )

except Exception as exc:

    st.error(f"Unable to load sales data: {exc}")

    st.stop()

if sales_df.empty:

    st.warning("No valid sales transactions were found.")

    st.stop()

# ============================================================

# SIDEBAR FILTERS

# ============================================================

st.sidebar.header("🔎 Sales Filters")

min_date = sales_df["TranscationDate"].min().date()

max_date = sales_df["TranscationDate"].max().date()

date_range = st.sidebar.date_input(

    "Transaction date range",

    value=(min_date, max_date),

    min_value=min_date,

    max_value=max_date,

)

if isinstance(date_range, (tuple, list)) and len(date_range) == 2:

    start_date, end_date = date_range

else:

    start_date, end_date = min_date, max_date

product_options = sorted(

    sales_df["Product"].dropna().unique()

)

selected_products = st.sidebar.multiselect(

    "Product",

    options=product_options,

    default=product_options,

)

outlet_options = sorted(

    sales_df["Outlet"].dropna().unique()

)

selected_outlets = st.sidebar.multiselect(

    "Outlet",

    options=outlet_options,

    default=outlet_options,

)

category_options = (

    sorted(sales_df["Category"].dropna().unique())

    if "Category" in sales_df.columns

    else []

)

selected_categories = st.sidebar.multiselect(

    "Category",

    options=category_options,

    default=category_options,

)

st.sidebar.caption(

    "Filters apply to the KPI cards, charts, and transaction table."

)

# ============================================================

# APPLY FILTERS

# ============================================================

filtered_sales = sales_df[

    sales_df["TranscationDate"].dt.date.between(

        start_date, end_date

    )

    & sales_df["Product"].isin(selected_products)

    & sales_df["Outlet"].isin(selected_outlets)

].copy()

if selected_categories and "Category" in filtered_sales.columns:

    filtered_sales = filtered_sales[

        filtered_sales["Category"].isin(selected_categories)

    ]

if filtered_sales.empty:

    st.warning("No transactions match the selected filters.")

    st.stop()

# Keep targets within the selected dates and products.

filtered_targets = target_df[

    target_df["Month"].between(

        pd.Period(start_date, freq="M"),

        pd.Period(end_date, freq="M"),

    )

    & target_df["SKU"].isin(filtered_sales["SKU"].unique())

].copy()

net_sales = filtered_sales["TotalNetSellingPrice"].sum()

gross_sales = filtered_sales["TotalSellingPrice"].sum()

total_discount = filtered_sales["TotalDiscount"].sum()

units_sold = filtered_sales["Qty"].sum()

total_target = filtered_targets["SalesTarget"].sum()

target_achievement = (

    net_sales / total_target * 100

    if total_target > 0

    else float("nan")

)

target_gap = net_sales - total_target

# ============================================================

# KPI CARDS

# ============================================================

st.markdown("### Sales Overview")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Net Sales", format_idr_compact(net_sales))

col2.metric("Sales Target", format_idr_compact(total_target))

col3.metric(

    "Target Achievement",

    format_percent(target_achievement),

    delta=(

        f"{format_idr_compact(target_gap)} vs target"

        if total_target > 0

        else None

    ),

)

col4.metric("Units Sold", f"{units_sold:,.0f}")

col5, col6, col7, col8 = st.columns(4)

col5.metric("Gross Sales", format_idr_compact(gross_sales))

col6.metric("Total Discounts", format_idr_compact(total_discount))

discount_rate = (

    total_discount / gross_sales * 100

    if gross_sales > 0

    else 0

)

col7.metric("Discount Rate", format_percent(discount_rate))

col8.metric(

    "Products Sold",

    f"{filtered_sales['SKU'].nunique():,}",

)

st.divider()

# ============================================================

# MONTHLY SALES VS TARGET — TOGGLE PRODUCTS VIA LEGEND

# ============================================================

st.markdown("### 1. Monthly Sales vs Target")

# Aggregate actual sales by month and product.

monthly_product_sales = (

    filtered_sales.groupby(["Month", "Product"], as_index=False)

    .agg(NetSales=("TotalNetSellingPrice", "sum"))

)

# Map SKU to product names for the target data.

# Target data originally has Month, SKU, and SalesTarget,

# so Product must be added before grouping by Product.

product_name_columns = ["SKU", "ShortDescription"]

if "Description" in product_df.columns:

    product_name_columns.append("Description")

product_name_map = product_df[

    product_name_columns

].drop_duplicates(subset=["SKU"]).copy()

monthly_product_target = filtered_targets.merge(

    product_name_map,

    on="SKU",

    how="left",

)

monthly_product_target["Product"] = (

    monthly_product_target["ShortDescription"]

    .fillna(

        monthly_product_target["Description"]

        if "Description" in monthly_product_target.columns

        else monthly_product_target["SKU"]

    )

    .fillna(monthly_product_target["SKU"])

)

monthly_product_target = (

    monthly_product_target

    .groupby(["Month", "Product"], as_index=False)

    .agg(SalesTarget=("SalesTarget", "sum"))

)

fig_monthly = go.Figure()

products = sorted(

    set(monthly_product_sales["Product"].dropna().unique())

    | set(monthly_product_target["Product"].dropna().unique())

)

for product in products:

    sales_data = (

        monthly_product_sales[

            monthly_product_sales["Product"] == product

        ]

        .sort_values("Month")

        .copy()

    )

    target_data = (

        monthly_product_target[

            monthly_product_target["Product"] == product

        ]

        .sort_values("Month")

        .copy()

    )

    # Convert Period values to timestamps for Plotly compatibility.

    sales_x = sales_data["Month"].dt.to_timestamp()

    target_x = target_data["Month"].dt.to_timestamp()

    # Actual sales line.

    if not sales_data.empty:

        fig_monthly.add_trace(

            go.Scatter(

                x=sales_x,

                y=sales_data["NetSales"],

                mode="lines+markers",

                name=f"{product} — Sales",

                legendgroup=product,

                hovertemplate=(

                    "<b>%{fullData.name}</b><br>"

                    "Month: %{x|%b %Y}<br>"

                    "Sales: Rp %{y:,.0f}"

                    "<extra></extra>"

                ),

            )

        )

    # Target line, dashed to distinguish it from actual sales.

    if not target_data.empty:

        fig_monthly.add_trace(

            go.Scatter(

                x=target_x,

                y=target_data["SalesTarget"],

                mode="lines+markers",

                line=dict(dash="dash"),

                name=f"{product} — Target",

                legendgroup=product,

                hovertemplate=(

                    "<b>%{fullData.name}</b><br>"

                    "Month: %{x|%b %Y}<br>"

                    "Target: Rp %{y:,.0f}"

                    "<extra></extra>"

                ),

            )

        )

fig_monthly.update_layout(

    height=500,

    hovermode="x unified",

    showlegend=True,

    legend=dict(

        title="Products — click to show/hide",

        orientation="h",

        yanchor="bottom",

        y=1.02,

        xanchor="left",

        x=0,

        groupclick="togglegroup",

    ),

    xaxis=dict(

        title="Month",

        tickformat="%b %Y",

    ),

    yaxis=dict(

        title="Amount (IDR)",

        tickprefix="Rp ",

        tickformat="~s",

    ),

    margin=dict(l=10, r=20, t=100, b=20),

)

st.plotly_chart(

    fig_monthly,

    width="stretch",

    key="monthly_sales_target",

)

st.caption(

    "Click a product legend entry to hide or show both its Sales "

    "and Target lines. Double-click a legend entry to isolate it."

)

st.divider()

# ============================================================
# PRODUCT PERFORMANCE AND TOP 3 SKU
# ============================================================

st.markdown("### 2. Sales by Product")

product_sales = (
    filtered_sales.groupby("Product", as_index=False)
    .agg(
        NetSales=("TotalNetSellingPrice", "sum"),
        UnitsSold=("Qty", "sum"),
    )
    .sort_values("NetSales", ascending=True)
)

fig_product = px.bar(
    product_sales,
    x="NetSales",
    y="Product",
    orientation="h",
    text="NetSales",
    labels={"NetSales": "Net Sales (IDR)", "Product": "Product"},
)
fig_product.update_traces(
    texttemplate="%{x:,.0f}",
    textposition="outside",
    cliponaxis=False,
    hovertemplate="%{y}<br>Net Sales: Rp %{x:,.0f}<extra></extra>",
)
fig_product.update_layout(
    showlegend=False,
    xaxis=dict(tickformat="~s"),
    margin=dict(l=5, r=30, t=20, b=20),
)
st.plotly_chart(fig_product, width="stretch", key="product_sales")

st.divider()
render_top3_sku_section(filtered_sales)

st.divider()

# ============================================================

# PRODUCT PERFORMANCE TABLE

# ============================================================

st.markdown("### 4. Product Performance Details")

product_detail = (

    filtered_sales.groupby(

        ["SKU", "Product"], as_index=False

    )

    .agg(

        UnitsSold=("Qty", "sum"),

        GrossSales=("TotalSellingPrice", "sum"),

        Discounts=("TotalDiscount", "sum"),

        NetSales=("TotalNetSellingPrice", "sum"),

    )

)

product_targets = (

    filtered_targets.groupby("SKU", as_index=False)

    .agg(SalesTarget=("SalesTarget", "sum"))

)

product_detail = product_detail.merge(

    product_targets,

    on="SKU",

    how="left",

)

product_detail["SalesTarget"] = (

    product_detail["SalesTarget"].fillna(0)

)

product_detail["Achievement (%)"] = (

    product_detail["NetSales"]

    .div(product_detail["SalesTarget"].replace(0, float("nan")))

    .mul(100)

)

product_detail["Target Gap"] = (

    product_detail["NetSales"] - product_detail["SalesTarget"]

)

product_detail = product_detail.sort_values(

    "NetSales", ascending=False

)

display_detail = product_detail.copy()

for col in [

    "GrossSales",

    "Discounts",

    "NetSales",

    "SalesTarget",

    "Target Gap",

]:

    display_detail[col] = display_detail[col].map(format_idr)

display_detail["UnitsSold"] = (

    display_detail["UnitsSold"].map(lambda x: f"{x:,.0f}")

)

display_detail["Achievement (%)"] = (

    display_detail["Achievement (%)"].map(format_percent)

)

display_detail = display_detail.rename(

    columns={

        "SKU": "SKU",

        "Product": "Product",

        "UnitsSold": "Units Sold",

        "GrossSales": "Gross Sales",

        "Discounts": "Discounts",

        "NetSales": "Net Sales",

        "SalesTarget": "Sales Target",

        "Achievement (%)": "Target Achievement",

        "Target Gap": "Gap vs Target",

    }

)

st.dataframe(

    display_detail,

    width="stretch",

    hide_index=True,

)

csv = product_detail.to_csv(index=False).encode("utf-8")

st.download_button(

    label="Download Product Performance CSV",

    data=csv,

    file_name="ggf_product_performance.csv",

    mime="text/csv",

)

# ============================================================

# HIGH SALES, LOW PROFIT ANALYSIS

# ============================================================

st.divider()

st.markdown("### 5. High Sales, Low Profit")

st.caption(

    "Identify products with strong revenue but weak profitability, "

    "and investigate cost and discount pressure."

)

required_cols = [

    "TotalNetSellingPrice",

    "TotalSellingPrice",

    "TotalDiscount",

    "Profit&Lost",

]

missing_cols = [

    col for col in required_cols

    if col not in filtered_sales.columns

]

if missing_cols:

    st.warning(

        f"Cannot calculate profitability analysis. "

        f"Missing columns: {', '.join(missing_cols)}"

    )

else:

    # Aggregate at product level

    profit_analysis = (

        filtered_sales.groupby(

            ["SKU", "Product"], as_index=False

        )

        .agg(

            UnitsSold=("Qty", "sum"),

            GrossSales=("TotalSellingPrice", "sum"),

            Discounts=("TotalDiscount", "sum"),

            NetSales=("TotalNetSellingPrice", "sum"),

            Profit=("Profit&Lost", "sum"),

        )

    )

    # Aggregate costs only when available

    if "TotalCost" in filtered_sales.columns:

        costs = (

            filtered_sales.groupby("SKU", as_index=False)

            .agg(TotalCost=("TotalCost", "sum"))

        )

        profit_analysis = profit_analysis.merge(

            costs, on="SKU", how="left"

        )

    else:

        profit_analysis["TotalCost"] = float("nan")

    # Profitability metrics

    profit_analysis["ProfitMarginPct"] = (

        profit_analysis["Profit"]

        .div(

            profit_analysis["NetSales"].where(

                profit_analysis["NetSales"] != 0

            )

        )

        * 100

    )

    profit_analysis["DiscountRatePct"] = (

        profit_analysis["Discounts"]

        .div(

            profit_analysis["GrossSales"].where(

                profit_analysis["GrossSales"] != 0

            )

        )

        * 100

    )

    profit_analysis["CostRatioPct"] = (

        profit_analysis["TotalCost"]

        .div(

            profit_analysis["NetSales"].where(

                profit_analysis["NetSales"] != 0

            )

        )

        * 100

    )

    # Define high sales using the median among products

    # with positive net sales.

    positive_sales = profit_analysis.loc[

        profit_analysis["NetSales"] > 0, "NetSales"

    ]

    if positive_sales.empty:

        st.info("No products with positive net sales in this selection.")

    else:

        high_sales_threshold = positive_sales.median()

        # Low profit = below 10% margin, or negative profit.

        # Adjust this threshold to match your business criteria.

        low_margin_threshold = st.slider(

            "Low profit margin threshold (%)",

            min_value=0,

            max_value=30,

            value=10,

            step=1,

            key="low_profit_margin_threshold",

        )

        profit_analysis["HighSales"] = (

            profit_analysis["NetSales"] >= high_sales_threshold

        )

        profit_analysis["LowProfit"] = (

            (profit_analysis["Profit"] < 0)

            | (

                profit_analysis["ProfitMarginPct"]

                < low_margin_threshold

            )

        )

        profit_analysis["Issue"] = profit_analysis.apply(

            lambda row: (

                "High sales, negative profit"

                if row["Profit"] < 0

                else "High sales, low margin"

                if row["HighSales"] and row["LowProfit"]

                else "Low margin"

                if row["LowProfit"]

                else "Healthy margin"

            ),

            axis=1,

        )

        # Flag high-sales products with low profit

        problem_products = profit_analysis[

            profit_analysis["HighSales"]

            & profit_analysis["LowProfit"]

        ].copy()

        # KPI cards

        total_problem_sales = problem_products["NetSales"].sum()

        total_problem_profit = problem_products["Profit"].sum()

        k1, k2, k3 = st.columns(3)

        k1.metric(

            "Products to Investigate",

            f"{len(problem_products):,}",

        )

        k2.metric(

            "Net Sales at Risk",

            format_idr_compact(total_problem_sales),

        )

        k3.metric(

            "Combined Profit",

            format_idr_compact(total_problem_profit),

        )

        st.caption(

            f"High-sales threshold: "

            f"{format_idr_compact(high_sales_threshold)} net sales. "

            f"Low-margin threshold: below {low_margin_threshold}% "

            "or negative profit."

        )

        # Scatter plot: high sales vs profit margin

        fig_profit = px.scatter(

            profit_analysis,

            x="NetSales",

            y="ProfitMarginPct",

            size="UnitsSold",

            color="Issue",

            hover_name="Product",

            hover_data={

                "SKU": True,

                "NetSales": ":,.0f",

                "Profit": ":,.0f",

                "ProfitMarginPct": ":.2f",

                "DiscountRatePct": ":.2f",

                "CostRatioPct": ":.2f",

                "UnitsSold": ":,.0f",

            },

            labels={

                "NetSales": "Net Sales (IDR)",

                "ProfitMarginPct": "Profit Margin (%)",

                "Issue": "Product Status",

                "UnitsSold": "Units Sold",

            },

            title="Product Revenue vs Profit Margin",

        )

        fig_profit.add_hline(

            y=low_margin_threshold,

            line_dash="dash",

            annotation_text="Low margin threshold",

        )

        fig_profit.add_vline(

            x=high_sales_threshold,

            line_dash="dash",

            annotation_text="High sales threshold",

        )

        fig_profit.update_layout(

            height=500,

            xaxis=dict(tickprefix="Rp ", tickformat="~s"),

            yaxis=dict(ticksuffix="%"),

            legend_title_text="Product Status",

        )

        st.plotly_chart(

            fig_profit,

            width="stretch",

            key="high_sales_low_profit_scatter",

        )

        # Prioritize lowest-margin, high-sales products

        st.markdown("#### Products Requiring Investigation")

        if problem_products.empty:

            st.success(

                "No high-sales products met the current low-profit "

                "criteria for this filter selection."

            )

        else:

            problem_products = problem_products.sort_values(

                ["ProfitMarginPct", "NetSales"],

                ascending=[True, False],

            )

            display_cols = [

                "SKU",

                "Product",

                "UnitsSold",

                "GrossSales",

                "Discounts",

                "DiscountRatePct",

                "NetSales",

                "Profit",

                "ProfitMarginPct",

                "TotalCost",

                "CostRatioPct",

            ]

            display_cols = [

                col for col in display_cols

                if col in problem_products.columns

            ]

            display_problem = problem_products[

                display_cols

            ].copy()

            for col in [

                "GrossSales",

                "Discounts",

                "NetSales",

                "Profit",

                "TotalCost",

            ]:

                if col in display_problem.columns:

                    display_problem[col] = (

                        display_problem[col].map(

                            lambda x: format_idr(x)

                            if pd.notna(x) else "N/A"

                        )

                    )

            for col in [

                "DiscountRatePct",

                "ProfitMarginPct",

                "CostRatioPct",

            ]:

                if col in display_problem.columns:

                    display_problem[col] = (

                        display_problem[col].map(

                            lambda x: f"{x:.2f}%"

                            if pd.notna(x) else "N/A"

                        )

                    )

            st.dataframe(

                display_problem,

                width="stretch",

                hide_index=True,

            )

            st.download_button(

                "Download Low-Profit Products CSV",

                data=problem_products.to_csv(

                    index=False

                ).encode("utf-8"),

                file_name="high_sales_low_profit.csv",

                mime="text/csv",

                key="download_high_sales_low_profit",

            )

            st.markdown("#### Recommended Investigation")

            st.write(

                "- **High discount rate:** review discount rules "

                "and promotional effectiveness."

            )

            st.write(

                "- **High cost ratio:** investigate raw material, "

                "production, and procurement costs."

            )

            st.write(

                "- **Negative profit:** verify transaction values, "

                "cost allocation, and the predefined profit/loss calculation."

            )

# ============================================================

# FILTERED TRANSACTIONS

# ============================================================

with st.expander("View filtered transaction data"):

    st.dataframe(

        filtered_sales.sort_values(

            "TranscationDate",

            ascending=False,

        ),

        width="stretch",

        hide_index=True,

    )

st.caption("Sales Performance | GGF Beverage Dashboard")
