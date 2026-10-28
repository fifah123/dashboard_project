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
    format_pct,
    get_first_existing_column,
    normalize_sku,
    safe_ratio,
    default_outlet
)
from utils.loader import load_profit_loss_data
# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "FruitsTrxDatasets.xlsx"

# This page assumes st.set_page_config() is called in app.py.

st.set_page_config(
    page_title="Profit & Loss | GGF Beverage",
    page_icon="🥤",
    layout="wide",
)

# ============================================================
# CUSTOM CSS — SMALLER KPI FONTS
# ============================================================

st.markdown(
    """
    <style>
    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.15rem !important;
        line-height: 1.25 !important;
    }

    [data-testid="stMetricDelta"] {
        font-size: 0.75rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# PAGE HEADER AND DATA LOADING
# ============================================================

st.title("💰 Profit & Loss Analysis")
st.caption(
    "Outlet-focused profitability analysis: sales performance, product "
    "margins, and reconciliation of recorded profit against recorded costs."
)

try:
    modified_time = EXCEL_PATH.stat().st_mtime
    df = load_profit_loss_data(str(EXCEL_PATH), modified_time)
except Exception as exc:
    st.error(f"Unable to load the workbook: {exc}")
    st.info(
        "Check that FruitsTrxDatasets.xlsx is in the project root and that "
        "the expected sheet names and columns are correct."
    )
    st.stop()

if df.empty:
    st.warning("No valid transaction data was found.")
    st.stop()


# ============================================================
# SIDEBAR FILTERS
# ============================================================

st.sidebar.header("🔎 P&L Filters")

min_date = df["TransactionDate"].min().date()
max_date = df["TransactionDate"].max().date()

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

if start_date > end_date:
    st.sidebar.error("Start date must be before end date.")
    st.stop()

product_options = sorted(df["Product"].dropna().unique().tolist())
selected_products = st.sidebar.multiselect(
    "Product", options=product_options, default=product_options
)

category_options = sorted(df["Category"].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Category", options=category_options, default=category_options
)

outlet_options = sorted(df["Outlet"].dropna().unique().tolist())
outlet_1_default = default_outlet(outlet_options)
default_outlets = [outlet_1_default] if outlet_1_default else outlet_options

selected_outlets = st.sidebar.multiselect(
    "Outlet",
    options=outlet_options,
    default=default_outlets,
    help="Defaults to Outlet 1 when that label exists in the workbook. "
         "You can select other outlets if needed.",
)

if outlet_1_default and outlet_1_default not in selected_outlets:
    st.sidebar.caption(
        f"Outlet 1 default is {outlet_1_default!r}; the current selection "
        "has been changed manually."
    )
elif outlet_1_default is None:
    st.sidebar.warning("No outlet values were found in the workbook.")

st.sidebar.divider()
st.sidebar.caption(
    "Financial figures use the selected transactions. Confirm the source "
    "definitions for cost and Profit&Lost before official financial reporting."
)


# ============================================================
# APPLY FILTERS
# ============================================================

filtered_df = df[
    (df["TransactionDate"].dt.date >= start_date)
    & (df["TransactionDate"].dt.date <= end_date)
    & (df["Product"].isin(selected_products))
    & (df["Category"].isin(selected_categories))
    & (df["Outlet"].isin(selected_outlets))
].copy()

if filtered_df.empty:
    st.warning(
        "No transactions match the selected filters. Try another date range, "
        "product, category, or outlet."
    )
    st.stop()

selected_outlet_label = (
    ", ".join(map(str, selected_outlets)) if selected_outlets else "No outlet"
)
st.markdown(
    f"**Analysis scope:** {selected_outlet_label}")
st.caption(
    f"{start_date:%d %b %Y} – {end_date:%d %b %Y} · "
    f"{len(filtered_df):,} transaction rows"
)


# ============================================================
# KPI CALCULATIONS
# ============================================================

net_sales = filtered_df["NetSales"].sum()
total_cost = filtered_df["TotalCostCalc"].sum()
total_profit = filtered_df["ProfitCalc"].sum()
total_qty = filtered_df["Qty"].sum()
total_discounts = filtered_df["TotalDiscount"].sum()

profit_margin = safe_ratio(total_profit, net_sales)
cost_to_sales = safe_ratio(total_cost, net_sales)
profitable_transactions = int((filtered_df["ProfitCalc"] > 0).sum())
loss_transactions = int((filtered_df["ProfitCalc"] < 0).sum())

# This is a reconciliation measure, not a replacement for recorded profit.
calculated_profit = net_sales - total_cost
profit_reconciliation_difference = total_profit - calculated_profit


# ============================================================
# KPI CARDS
# ============================================================

st.subheader("Financial Overview")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Net Sales", format_idr_compact(net_sales))
kpi2.metric("Total Cost", format_idr_compact(total_cost))
kpi3.metric("Recorded Profit / Loss", format_idr_compact(total_profit))
kpi4.metric("Recorded Profit Margin", format_pct(profit_margin))

kpi5, kpi6, kpi7, kpi8 = st.columns(4)
kpi5.metric("Units Sold", f"{total_qty:,.0f}")
kpi6.metric("Total Discounts", format_idr_compact(total_discounts))
kpi7.metric("Cost-to-Sales Ratio", format_pct(cost_to_sales))
kpi8.metric("Loss-Making Transactions", f"{loss_transactions:,}")


# ============================================================
# WATERFALL: GROSS SALES TO CALCULATED PROFIT
# ============================================================

st.divider()
st.subheader("🌊 From Gross Sales to Calculated Profit")
st.markdown(
    "This waterfall bridges gross sales to **calculated profit (Net Sales − Total Cost)**. "
    "It includes only fields available in the workbook: sales, discounts, and product costs. "
    "Returns, freight/logistics, and sales commissions are not shown because separate fields "
    "are not available. The recorded `Profit&Lost` value is compared below in the reconciliation section."
)

gross_sales = filtered_df["GrossSales"].sum()
# Keep the bridge mathematically consistent with the filtered Net Sales total.
net_sales_after_discount = gross_sales - total_discounts
sales_adjustment = net_sales - net_sales_after_discount
cost_for_waterfall = total_cost
calculated_profit_for_waterfall = net_sales - cost_for_waterfall

waterfall_labels = [
    "Gross Sales",
    "Discounts",
    "Net Sales Adjustment",
    "Product Costs",
    "Calculated Profit",
]
waterfall_values = [
    gross_sales,
    -total_discounts,
    sales_adjustment,
    -cost_for_waterfall,
    0,
]
waterfall_measures = ["absolute", "relative", "relative", "relative", "total"]

fig_waterfall = go.Figure(
    go.Waterfall(
        name="Sales-to-profit bridge",
        orientation="v",
        measure=waterfall_measures,
        x=waterfall_labels,
        y=waterfall_values,
        text=[format_idr_compact(v) for v in [
            gross_sales,
            -total_discounts,
            sales_adjustment,
            -cost_for_waterfall,
            calculated_profit_for_waterfall,
        ]],
        textposition="outside",
        connector={"line": {"width": 1}},
        hovertemplate="%{x}<br>Amount: %{y:,.0f}<extra></extra>",
    )
)
fig_waterfall.update_layout(
    height=470,
    showlegend=False,
    yaxis_title="Amount (IDR)",
    xaxis_title="",
    margin=dict(l=20, r=20, t=35, b=20),
)
st.plotly_chart(fig_waterfall, use_container_width=True)

if abs(sales_adjustment) > 1:
    st.caption(
        "Net Sales Adjustment bridges Gross Sales − Discounts to the actual Net Sales total. "
        "Review the source definitions if this adjustment is material; it is not labeled as a specific fee or return."
    )
else:
    st.caption(
        "The bridge reconciles Gross Sales − Discounts to Net Sales within the current tolerance. "
        "Calculated Profit is Net Sales − Total Cost; recorded `Profit&Lost` is shown separately below."
    )


# ============================================================
# MONTHLY PROFIT & LOSS TREND
# (Retained from original page; no monthly margin/contribution analysis.)
# ============================================================

st.divider()
st.subheader("📈 Monthly Profit & Loss Trend")

monthly = (
    filtered_df.groupby("Month", as_index=False)
    .agg(
        NetSales=("NetSales", "sum"),
        TotalCost=("TotalCostCalc", "sum"),
        Profit=("ProfitCalc", "sum"),
    )
    .sort_values("Month")
)

if not monthly.empty:
    fig_monthly = go.Figure()
    fig_monthly.add_trace(
        go.Bar(x=monthly["Month"], y=monthly["NetSales"], name="Net Sales")
    )
    fig_monthly.add_trace(
        go.Bar(x=monthly["Month"], y=monthly["TotalCost"], name="Total Cost")
    )
    fig_monthly.add_trace(
        go.Scatter(
            x=monthly["Month"],
            y=monthly["Profit"],
            name="Recorded Profit / Loss",
            mode="lines+markers",
            yaxis="y2",
        )
    )
    fig_monthly.update_layout(
        barmode="group",
        xaxis_title="Month",
        yaxis=dict(title="Sales and Cost (IDR)", tickformat=",.0f"),
        yaxis2=dict(
            title="Recorded Profit / Loss (IDR)",
            overlaying="y",
            side="right",
            tickformat=",.0f",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="left", x=0),
        margin=dict(l=20, r=20, t=60, b=20),
    )
    st.plotly_chart(fig_monthly, use_container_width=True)


# ============================================================
# MARGIN-FIRST PRODUCT DIAGNOSTICS
# ============================================================

st.divider()
st.subheader("🥤 Product Margin Diagnostics")
st.caption(
    "Prioritize products with substantial sales but weak margins, while also "
    "highlighting losses and unusual cost/discount patterns for investigation."
)

product_pl = (
    filtered_df.groupby(["SKU", "Product", "Category"], as_index=False)
    .agg(
        UnitsSold=("Qty", "sum"),
        GrossSales=("GrossSales", "sum"),
        NetSales=("NetSales", "sum"),
        TotalCost=("TotalCostCalc", "sum"),
        RecordedProfit=("ProfitCalc", "sum"),
        Discounts=("TotalDiscount", "sum"),
        TransactionRows=("SKU", "size"),
    )
)

product_pl["CalculatedProfit"] = product_pl["NetSales"] - product_pl["TotalCost"]
product_pl["ReconciliationDifference"] = (
    product_pl["RecordedProfit"] - product_pl["CalculatedProfit"]
)
product_pl["ProfitMarginPct"] = (
    product_pl["RecordedProfit"]
    .div(product_pl["NetSales"].where(product_pl["NetSales"] != 0))
    .mul(100)
)
product_pl["CostToSalesPct"] = (
    product_pl["TotalCost"]
    .div(product_pl["NetSales"].where(product_pl["NetSales"] != 0))
    .mul(100)
)
product_pl["DiscountRatePct"] = (
    product_pl["Discounts"]
    .div(product_pl["GrossSales"].where(product_pl["GrossSales"] != 0))
    .mul(100)
)
product_pl["ProfitPerUnit"] = (
    product_pl["RecordedProfit"]
    .div(product_pl["UnitsSold"].where(product_pl["UnitsSold"] != 0))
)
product_pl["NetSalesPerUnit"] = (
    product_pl["NetSales"]
    .div(product_pl["UnitsSold"].where(product_pl["UnitsSold"] != 0))
)

# Threshold controls: high sales is relative to products in the selected scope.
threshold_col1, threshold_col2 = st.columns(2)
positive_sales = product_pl.loc[product_pl["NetSales"] > 0, "NetSales"]
default_sales_threshold = (
    float(positive_sales.median()) if not positive_sales.empty else 0.0
)

with threshold_col1:
    high_sales_threshold = st.number_input(
        "High-sales threshold (IDR)",
        min_value=0.0,
        value=float(default_sales_threshold),
        step=1_000_000.0,
        help="Defaults to the median positive product net sales in the selected scope.",
    )
with threshold_col2:
    low_margin_threshold = st.number_input(
        "Low-margin threshold (%)",
        min_value=-100.0,
        max_value=100.0,
        value=10.0,
        step=1.0,
        help="Products below this recorded profit margin are flagged for review.",
    )

product_pl["HighSales"] = product_pl["NetSales"] >= high_sales_threshold
product_pl["LowMargin"] = product_pl["ProfitMarginPct"] < low_margin_threshold
product_pl["NegativeProfit"] = product_pl["RecordedProfit"] < 0
product_pl["CostAtOrAboveSales"] = (
    product_pl["TotalCost"] >= product_pl["NetSales"]
)
product_pl["HighDiscount"] = product_pl["DiscountRatePct"] >= 15.0
product_pl["ProfitReconciliationFlag"] = (
    product_pl["ReconciliationDifference"].abs() > 1_000
)

def build_findings(row):
    findings = []
    if row["HighSales"] and row["LowMargin"]:
        findings.append("High sales / low margin")
    if row["NegativeProfit"]:
        findings.append("Negative recorded profit")
    if row["CostAtOrAboveSales"]:
        findings.append("Cost >= net sales")
    if pd.notna(row["DiscountRatePct"]) and row["HighDiscount"]:
        findings.append("Discount rate >= 15%")
    if row["ProfitReconciliationFlag"]:
        findings.append("Profit reconciliation difference")
    return "; ".join(findings) if findings else "No configured flags"


product_pl["InvestigationFindings"] = product_pl.apply(build_findings, axis=1)

high_revenue_low_margin = product_pl[
    product_pl["HighSales"] & product_pl["LowMargin"]
].copy()
loss_products = product_pl[product_pl["NegativeProfit"]].copy()

metric1, metric2, metric3, metric4 = st.columns(4)
metric1.metric("Products Analyzed", f"{len(product_pl):,}")
metric2.metric("High-Sales / Low-Margin", f"{len(high_revenue_low_margin):,}")
metric3.metric("Loss-Making Products", f"{len(loss_products):,}")
metric4.metric(
    "Sales in High-Sales / Low-Margin Group",
    format_idr_compact(high_revenue_low_margin["NetSales"].sum()),
)

# Scatter plot: sales scale versus recorded margin.
fig_margin_scatter = px.scatter(
    product_pl,
    x="NetSales",
    y="ProfitMarginPct",
    size="UnitsSold",
    color="InvestigationFindings",
    hover_name="Product",
    hover_data={
        "SKU": True,
        "Category": True,
        "NetSales": ":,.0f",
        "TotalCost": ":,.0f",
        "RecordedProfit": ":,.0f",
        "ProfitMarginPct": ":.2f",
        "DiscountRatePct": ":.2f",
        "UnitsSold": ":,.0f",
    },
    title="Product Sales vs Recorded Profit Margin",
    labels={
        "NetSales": "Net Sales (IDR)",
        "ProfitMarginPct": "Recorded Profit Margin (%)",
        "InvestigationFindings": "Investigation flags",
        "UnitsSold": "Units sold",
    },
)
fig_margin_scatter.add_hline(
    y=0, line_dash="dash", line_color="red",
    annotation_text="Break-even margin",
)
fig_margin_scatter.add_hline(
    y=low_margin_threshold, line_dash="dot", line_color="orange",
    annotation_text=f"Low-margin threshold ({low_margin_threshold:.0f}%)",
)
fig_margin_scatter.add_vline(
    x=high_sales_threshold, line_dash="dot", line_color="gray",
    annotation_text="High-sales threshold",
)
fig_margin_scatter.update_layout(
    xaxis_tickformat=",.0f",
    margin=dict(l=20, r=20, t=70, b=20),
)
st.plotly_chart(fig_margin_scatter, use_container_width=True)

if high_revenue_low_margin.empty:
    st.success(
        "No products meet both the selected high-sales and low-margin "
        "thresholds. Review the thresholds if you want a broader shortlist."
    )
else:
    st.markdown("#### Priority products: high sales, low margin")
    priority_columns = [
        "SKU", "Product", "Category", "UnitsSold", "NetSales", "Discounts",
        "DiscountRatePct", "TotalCost", "RecordedProfit", "ProfitMarginPct",
        "CostToSalesPct", "ProfitPerUnit", "ReconciliationDifference",
        "InvestigationFindings",
    ]
    priority_display = high_revenue_low_margin[priority_columns].sort_values(
        ["NetSales", "ProfitMarginPct"], ascending=[False, True]
    ).copy()
    st.dataframe(
        priority_display.style.format({
            "UnitsSold": "{:,.0f}",
            "NetSales": lambda x: format_idr(x),
            "Discounts": lambda x: format_idr(x),
            "DiscountRatePct": "{:.2f}%",
            "TotalCost": lambda x: format_idr(x),
            "RecordedProfit": lambda x: format_idr(x),
            "ProfitMarginPct": "{:.2f}%",
            "CostToSalesPct": "{:.2f}%",
            "ProfitPerUnit": lambda x: format_idr(x),
            "ReconciliationDifference": lambda x: format_idr(x),
        }),
        use_container_width=True,
        hide_index=True,
    )

with st.expander("View all products ranked by recorded profit margin"):
    ranked_products = product_pl.sort_values(
        ["ProfitMarginPct", "NetSales"], ascending=[True, False]
    ).copy()
    rank_columns = [
        "SKU", "Product", "Category", "UnitsSold", "NetSales", "TotalCost",
        "RecordedProfit", "ProfitMarginPct", "CostToSalesPct",
        "DiscountRatePct", "ProfitPerUnit", "InvestigationFindings",
    ]
    st.dataframe(
        ranked_products[rank_columns].style.format({
            "UnitsSold": "{:,.0f}",
            "NetSales": lambda x: format_idr(x),
            "TotalCost": lambda x: format_idr(x),
            "RecordedProfit": lambda x: format_idr(x),
            "ProfitMarginPct": "{:.2f}%",
            "CostToSalesPct": "{:.2f}%",
            "DiscountRatePct": "{:.2f}%",
            "ProfitPerUnit": lambda x: format_idr(x),
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# PROFIT RECONCILIATION
# ============================================================

st.divider()
st.subheader("🧮 Profit Reconciliation")
st.markdown(
    "Compare the recorded `Profit&Lost` amount with **Net Sales − Total Cost**. "
    "A difference is a reconciliation flag for investigation, not proof that "
    "either figure is wrong."
)

recon_total = pd.DataFrame([{
    "Net Sales": net_sales,
    "Recorded Total Cost": total_cost,
    "Calculated Profit (Net Sales - Cost)": calculated_profit,
    "Recorded Profit": total_profit,
    "Difference (Recorded - Calculated)": profit_reconciliation_difference,
}])

recon_col1, recon_col2 = st.columns(2)
with recon_col1:
    st.metric(
        "Calculated Profit (Net Sales − Cost)",
        format_idr_compact(calculated_profit),
    )
with recon_col2:
    st.metric(
        "Recorded vs Calculated Difference",
        format_idr_compact(profit_reconciliation_difference),
        help="Recorded profit minus (net sales minus recorded total cost).",
    )

st.dataframe(
    recon_total.style.format({
        "Net Sales": lambda x: format_idr(x),
        "Recorded Total Cost": lambda x: format_idr(x),
        "Calculated Profit (Net Sales - Cost)": lambda x: format_idr(x),
        "Recorded Profit": lambda x: format_idr(x),
        "Difference (Recorded - Calculated)": lambda x: format_idr(x),
    }),
    use_container_width=True,
    hide_index=True,
)

recon_by_product = product_pl[[
    "SKU", "Product", "Category", "NetSales", "TotalCost",
    "CalculatedProfit", "RecordedProfit", "ReconciliationDifference",
]].copy()
recon_by_product["AbsoluteDifference"] = (
    recon_by_product["ReconciliationDifference"].abs()
)
recon_by_product = recon_by_product.sort_values(
    "AbsoluteDifference", ascending=False
)

st.markdown("#### Product-level reconciliation")
st.caption(
    "Products with the largest absolute differences appear first. "
    "Differences within Rp 1,000 are not flagged in the diagnostic table."
)
st.dataframe(
    recon_by_product.drop(columns="AbsoluteDifference").style.format({
        "NetSales": lambda x: format_idr(x),
        "TotalCost": lambda x: format_idr(x),
        "CalculatedProfit": lambda x: format_idr(x),
        "RecordedProfit": lambda x: format_idr(x),
        "ReconciliationDifference": lambda x: format_idr(x),
    }),
    use_container_width=True,
    hide_index=True,
)

# Reconciliation export includes both product analysis and differences.
csv_data = product_pl.sort_values(
    "NetSales", ascending=False
).to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="⬇️ Download Product Profitability & Reconciliation (CSV)",
    data=csv_data,
    file_name="ggf_outlet_profitability_reconciliation.csv",
    mime="text/csv",
)


# ============================================================
# COST STRUCTURE
# ============================================================

st.divider()
st.subheader("🧾 Cost Structure")
cost_col1, cost_col2 = st.columns(2)

raw_available = bool(filtered_df["HasRawMaterialComponent"].any())
production_available = bool(filtered_df["HasProductionComponent"].any())

with cost_col1:
    if raw_available and production_available:
        cost_components = pd.DataFrame({
            "Cost Component": ["Raw Material Cost", "Production Cost"],
            "Amount": [
                filtered_df["TotalRawMaterialCost"].sum(),
                filtered_df["TotalProductionCost"].sum(),
            ],
        })
        if cost_components["Amount"].sum() > 0:
            fig_cost = px.pie(
                cost_components,
                names="Cost Component",
                values="Amount",
                hole=0.45,
                title="Raw Material vs Production Cost",
            )
            fig_cost.update_traces(
                texttemplate="%{label}<br>%{percent}",
                hovertemplate=(
                    "%{label}<br>Amount: Rp %{value:,.0f}<br>"
                    "Share: %{percent}<extra></extra>"
                ),
            )
            st.plotly_chart(fig_cost, use_container_width=True)
        else:
            st.info("Cost component values are zero for the selected transactions.")
    else:
        missing_components = []
        if not raw_available:
            missing_components.append("raw material")
        if not production_available:
            missing_components.append("production")
        st.info(
            "Cost component chart unavailable because the workbook does not "
            "provide: " + " and ".join(missing_components) + " cost data."
        )

with cost_col2:
    st.markdown("#### Cost Summary")
    cost_rows = []
    if raw_available:
        cost_rows.append({
            "Cost Component": "Raw Material Cost",
            "Amount (IDR)": filtered_df["TotalRawMaterialCost"].sum(),
        })
    else:
        cost_rows.append({
            "Cost Component": "Raw Material Cost",
            "Amount (IDR)": None,
        })
    if production_available:
        cost_rows.append({
            "Cost Component": "Production Cost",
            "Amount (IDR)": filtered_df["TotalProductionCost"].sum(),
        })
    else:
        cost_rows.append({
            "Cost Component": "Production Cost",
            "Amount (IDR)": None,
        })
    cost_rows.append({
        "Cost Component": "Total Recorded Cost",
        "Amount (IDR)": total_cost,
    })
    cost_summary = pd.DataFrame(cost_rows)
    st.dataframe(
        cost_summary.style.format({
            "Amount (IDR)": lambda x: "Unavailable" if pd.isna(x)
            else format_idr_compact(x)
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# DETAILED PROFIT & LOSS TABLE
# ============================================================

st.divider()
st.subheader("📋 Detailed Profit & Loss")

display_pl = product_pl.copy()
display_pl["Profit Status"] = display_pl["RecordedProfit"].apply(
    lambda value: "Profit" if value > 0 else (
        "Loss" if value < 0 else "Break-even"
    )
)
display_pl = display_pl[[
    "SKU", "Product", "Category", "UnitsSold", "NetSales", "Discounts",
    "TotalCost", "RecordedProfit", "ProfitMarginPct", "Profit Status",
    "CalculatedProfit", "ReconciliationDifference", "InvestigationFindings",
]].rename(columns={
    "UnitsSold": "Units Sold",
    "NetSales": "Net Sales (IDR)",
    "Discounts": "Discounts (IDR)",
    "TotalCost": "Total Cost (IDR)",
    "RecordedProfit": "Recorded Profit / Loss (IDR)",
    "ProfitMarginPct": "Recorded Profit Margin (%)",
    "CalculatedProfit": "Calculated Profit (IDR)",
    "ReconciliationDifference": "Reconciliation Difference (IDR)",
    "InvestigationFindings": "Investigation Findings",
})
st.dataframe(
    display_pl.style.format({
        "Units Sold": "{:,.0f}",
        "Net Sales (IDR)": lambda x: format_idr(x),
        "Discounts (IDR)": lambda x: format_idr(x),
        "Total Cost (IDR)": lambda x: format_idr(x),
        "Recorded Profit / Loss (IDR)": lambda x: format_idr(x),
        "Recorded Profit Margin (%)": "{:.2f}%",
        "Calculated Profit (IDR)": lambda x: format_idr(x),
        "Reconciliation Difference (IDR)": lambda x: format_idr(x),
    }),
    use_container_width=True,
    hide_index=True,
)

with st.expander("View filtered transaction details"):
    transaction_columns = [
        "TransactionDate", "SKU", "Product", "Category", "Outlet", "Qty",
        "GrossSales", "TotalDiscount", "NetSales", "TotalRawMaterialCost",
        "TotalProductionCost", "TotalCostCalc", "ProfitCalc",
    ]
    transaction_details = filtered_df[
        [col for col in transaction_columns if col in filtered_df.columns]
    ].rename(columns={
        "TransactionDate": "Transaction Date",
        "GrossSales": "Gross Sales (IDR)",
        "TotalDiscount": "Discounts (IDR)",
        "NetSales": "Net Sales (IDR)",
        "TotalRawMaterialCost": "Raw Material Cost (IDR)",
        "TotalProductionCost": "Production Cost (IDR)",
        "TotalCostCalc": "Total Cost (IDR)",
        "ProfitCalc": "Recorded Profit / Loss (IDR)",
    })
    
    st.dataframe(
        transaction_details.style.format({
            "Gross Sales (IDR)": lambda x: format_idr(x),
            "Discounts (IDR)": lambda x: format_idr(x),
            "Net Sales (IDR)": lambda x: format_idr(x),
            "Raw Material Cost (IDR)": lambda x: format_idr(x),
            "Production Cost (IDR)": lambda x: format_idr(x),
            "Total Cost (IDR)": lambda x: format_idr(x),
            "Recorded Profit / Loss (IDR)": lambda x: format_idr(x),
        }, na_rep="-"),
        use_container_width=True,
        hide_index=True,
    )


st.caption("GGF Beverage Dashboard | Outlet Profitability & Margin Analysis")
