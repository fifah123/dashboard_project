
from pathlib import Path
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from utils.cleaning import (
    clean_column_names,
    parse_number,
    format_idr_compact,
    format_pct,
    find_date_column,
    normalize_sku,
)
from utils.loader import load_predictive_data
# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]
EXCEL_PATH = BASE_DIR / "FruitsTrxDatasets.xlsx"

# ============================================================
# FORECASTING ENGINE
# ============================================================

def make_monthly_series(df, date_col, value_col):
    """Aggregate observations into a continuous monthly series."""
    data = df[[date_col, value_col]].dropna().copy()

    if data.empty:
        return pd.Series(dtype=float)

    data[date_col] = pd.to_datetime(data[date_col])
    data["Month"] = data[date_col].dt.to_period("M").dt.to_timestamp()

    series = (
        data.groupby("Month")[value_col]
        .mean()
        .sort_index()
    )

    full_index = pd.date_range(
        start=series.index.min(),
        end=series.index.max(),
        freq="MS",
    )

    # Preserve actual observed monthly totals/means where available.
    return series.reindex(full_index).astype(float)


def fit_forecast(series, horizon=3):
    """
    Fit a lightweight additive trend and monthly seasonality model.

    If enough history is available, estimate seasonality from monthly
    deviations. Otherwise use a linear trend without seasonality.

    Returns forecast, prediction interval, and model diagnostics.
    """
    series = series.dropna().astype(float).sort_index()

    if len(series) < 3:
        raise ValueError(
            "At least 3 observed monthly data points are required."
        )

    y = series.to_numpy(dtype=float)
    n = len(y)
    x = np.arange(n, dtype=float)

    use_seasonality = n >= 18

    # Initial linear trend.
    slope, intercept = np.polyfit(x, y, 1)
    trend = intercept + slope * x
    seasonal_pattern = np.zeros(12, dtype=float)

    if use_seasonality:
        residual = y - trend
        month_numbers = series.index.month.to_numpy()

        for month in range(1, 13):
            mask = month_numbers == month
            if mask.sum() >= 2:
                seasonal_pattern[month - 1] = np.median(
                    residual[mask]
                )

        # Center seasonal effects to avoid shifting the overall trend.
        seasonal_pattern -= seasonal_pattern.mean()

        deseasonalized = y - seasonal_pattern[month_numbers - 1]
        slope, intercept = np.polyfit(x, deseasonalized, 1)
        trend = intercept + slope * x

        fitted = trend + seasonal_pattern[month_numbers - 1]
        model_name = "Linear trend + monthly seasonality"
    else:
        fitted = trend
        model_name = "Linear trend"

    residuals = y - fitted
    residual_std = (
        float(np.std(residuals, ddof=1))
        if len(residuals) > 1
        else 0.0
    )

    future_dates = pd.date_range(
        start=series.index[-1] + pd.offsets.MonthBegin(1),
        periods=horizon,
        freq="MS",
    )

    future_x = np.arange(n, n + horizon, dtype=float)
    forecast_values = intercept + slope * future_x

    if use_seasonality:
        forecast_values += seasonal_pattern[future_dates.month - 1]

    # Approximate prediction intervals. These are not formal
    # calibrated intervals for a complex time-series model.
    uncertainty = residual_std * np.sqrt(
        1 + np.arange(1, horizon + 1) / max(n, 1)
    )

    forecast = pd.DataFrame({
        "Month": future_dates,
        "Forecast": forecast_values,
        "Lower": forecast_values - 1.96 * uncertainty,
        "Upper": forecast_values + 1.96 * uncertainty,
    })

    # Avoid negative sales or prices.
    forecast["Forecast"] = forecast["Forecast"].clip(lower=0)
    forecast["Lower"] = forecast["Lower"].clip(lower=0)
    forecast["Upper"] = forecast["Upper"].clip(lower=0)

    diagnostics = {
        "model": model_name,
        "observations": n,
        "residual_std": residual_std,
        "fitted": pd.Series(fitted, index=series.index),
    }

    return forecast, diagnostics


def backtest_forecast(series):
    """
    Hold out the final portion of the series and forecast it from
    earlier observations. Returns metrics for the holdout period.
    """
    series = series.dropna().astype(float).sort_index()

    if len(series) < 8:
        return None

    test_size = min(3, max(1, len(series) // 5))
    train = series.iloc[:-test_size]
    test = series.iloc[-test_size:]

    if len(train) < 3:
        return None

    forecast, _ = fit_forecast(train, horizon=test_size)
    actual = test.to_numpy(dtype=float)
    predicted = forecast["Forecast"].to_numpy(dtype=float)

    mae = float(np.mean(np.abs(actual - predicted)))

    nonzero = actual != 0
    mape = (
        float(np.mean(np.abs(
            (actual[nonzero] - predicted[nonzero]) / actual[nonzero]
        )) * 100)
        if nonzero.any()
        else np.nan
    )

    return {
        "MAE": mae,
        "MAPE": mape,
        "Test size": test_size,
    }


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🔮 Predictive Analytics")
st.caption(
    "Forecast future sales and raw material prices, evaluate historical "
    "forecast errors, and explore potential cost scenarios."
)

try:
    sales_df, raw_df, products_df, monthly_sales_df, monthly_prices_df = (
        load_predictive_data(
            str(EXCEL_PATH),
            EXCEL_PATH.stat().st_mtime,
        )
    )
except Exception as exc:
    st.error(f"Unable to load forecasting data: {exc}")
    st.info("Check the workbook, sheet names, and required columns.")
    st.stop()

if monthly_sales_df.empty:
    st.warning("No valid sales records are available for forecasting.")
    st.stop()


# ============================================================
# SIDEBAR SETTINGS
# ============================================================

st.sidebar.header("⚙️ Forecast Settings")

horizon = st.sidebar.selectbox(
    "Forecast horizon",
    options=[1, 3, 6, 12],
    index=1,
    format_func=lambda n: f"{n} month{'s' if n != 1 else ''}",
)

product_options = sorted(
    products_df["Product"].dropna().unique().tolist()
)

selected_product = st.sidebar.selectbox(
    "Product",
    options=["All Products"] + product_options,
    index=0,
)

st.sidebar.caption(
    "Forecasts use monthly historical observations. "
    "Longer horizons generally have greater uncertainty."
)


# ============================================================
# BUILD SELECTED DATASETS
# ============================================================

if selected_product == "All Products":
    sales_selected = sales_df.copy()
    raw_selected = raw_df.copy()
else:
    sales_selected = sales_df[
        sales_df["Product"] == selected_product
    ].copy()

    raw_selected = raw_df[
        raw_df["Product"] == selected_product
    ].copy()
# ============================================================
# SALES FORECAST
# ============================================================

st.divider()
st.subheader("📈 Monthly Sales Forecast")

monthly_sales = make_monthly_series(
    sales_selected,
    "Date",
    "TotalNetSellingPrice",
)

if len(monthly_sales.dropna()) < 3:
    st.warning(
        "There are not enough monthly sales observations to create a "
        "forecast. At least 3 months of historical data are required."
    )
else:
    sales_forecast, sales_diagnostics = fit_forecast(
        monthly_sales,
        horizon=horizon,
    )

    latest_sales = float(monthly_sales.dropna().iloc[-1])
    next_month_sales = float(sales_forecast["Forecast"].iloc[0])
    final_forecast_sales = float(sales_forecast["Forecast"].iloc[-1])

    sales_change = (
        (next_month_sales / latest_sales - 1) * 100
        if latest_sales != 0
        else np.nan
    )

    sales_k1, sales_k2, sales_k3 = st.columns(3)

    sales_k1.metric(
        "Latest Actual Monthly Sales",
        format_idr_compact(latest_sales),
    )

    sales_k2.metric(
        "Next Month Forecast",
        format_idr_compact(next_month_sales),
        delta=format_pct(sales_change),
    )

    sales_k3.metric(
        f"Sales Forecast in {horizon} Month(s)",
        format_idr_compact(final_forecast_sales),
    )

    history_df = monthly_sales.dropna().rename(
        "Actual"
    ).reset_index()
    history_df.columns = ["Month", "Actual"]

    fig_sales = go.Figure()

    fig_sales.add_trace(
        go.Scatter(
            x=history_df["Month"],
            y=history_df["Actual"],
            mode="lines+markers",
            name="Historical Sales",
        )
    )

    fig_sales.add_trace(
        go.Scatter(
            x=sales_forecast["Month"],
            y=sales_forecast["Forecast"],
            mode="lines+markers",
            name="Forecast Sales",
            line=dict(dash="dash"),
        )
    )

    fig_sales.add_trace(
        go.Scatter(
            x=pd.concat([
                sales_forecast["Month"],
                sales_forecast["Month"].iloc[::-1],
            ]),
            y=pd.concat([
                sales_forecast["Upper"],
                sales_forecast["Lower"].iloc[::-1],
            ]),
            fill="toself",
            fillcolor="rgba(100, 149, 237, 0.18)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            name="Approx. 95% interval",
        )
    )

    fig_sales.update_layout(
        title="Historical Sales and Forecast",
        xaxis_title="Month",
        yaxis_title="Net Sales (IDR)",
        yaxis_tickformat="~s",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=20, r=20, t=80, b=20),
    )

    st.plotly_chart(fig_sales, use_container_width=True)

    st.caption(
        f"Model: {sales_diagnostics['model']} | "
        f"Training observations: {sales_diagnostics['observations']} months"
    )

    st.markdown("#### Sales Forecast Table")

    sales_table = sales_forecast.copy()
    sales_table["Month"] = sales_table["Month"].dt.strftime("%b %Y")

    st.dataframe(
        sales_table.rename(columns={
            "Month": "Month",
            "Forecast": "Forecast Sales (IDR)",
            "Lower": "Lower Estimate (IDR)",
            "Upper": "Upper Estimate (IDR)",
        }).style.format({
            "Forecast Sales (IDR)": lambda x: format_idr_compact(x),
            "Lower Estimate (IDR)": lambda x: format_idr_compact(x),
            "Upper Estimate (IDR)": lambda x: format_idr_compact(x),
        }),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# SALES FORECAST BACKTEST
# ============================================================

st.divider()
st.subheader("🧪 Forecast Backtesting")

sales_backtest = backtest_forecast(monthly_sales)

if sales_backtest is None:
    st.info(
        "At least 8 monthly observations are required for the sales "
        "backtest. Collect more historical data to evaluate accuracy."
    )
else:
    bt1, bt2, bt3 = st.columns(3)

    bt1.metric(
        "Mean Absolute Error (MAE)",
        format_idr_compact(sales_backtest["MAE"]),
    )

    bt2.metric(
        "Mean Absolute Percentage Error (MAPE)",
        (
            f"{sales_backtest['MAPE']:.2f}%"
            if pd.notna(sales_backtest["MAPE"])
            else "N/A"
        ),
    )

    bt3.metric(
        "Holdout Months",
        f"{sales_backtest['Test size']}",
    )

    st.caption(
        "MAE measures average absolute forecast error in IDR. MAPE "
        "measures percentage error where actual values are nonzero. "
        "These metrics describe a small historical holdout, not a "
        "guarantee of future performance."
    )


# ============================================================
# RAW MATERIAL PRICE FORECAST
# ============================================================

st.divider()
st.subheader("🌱 Raw Material Price Forecast")

monthly_price = make_monthly_series(
    raw_selected,
    "Date",
    "Close Price",
)

if len(monthly_price.dropna()) < 3:
    st.warning(
        "There are not enough monthly raw material price observations "
        "to forecast. At least 3 months are required."
    )
else:
    price_forecast, price_diagnostics = fit_forecast(
        monthly_price,
        horizon=horizon,
    )

    latest_price = float(monthly_price.dropna().iloc[-1])
    next_price = float(price_forecast["Forecast"].iloc[0])
    price_change = (
        (next_price / latest_price - 1) * 100
        if latest_price != 0
        else np.nan
    )

    price_k1, price_k2, price_k3 = st.columns(3)

    price_k1.metric(
        "Latest Average Monthly Close Price",
        format_idr_compact(latest_price),
    )

    price_k2.metric(
        "Next Month Price Forecast",
        format_idr_compact(next_price),
        delta=format_pct(price_change),
    )

    price_k3.metric(
        f"Price Forecast in {horizon} Month(s)",
        format_idr_compact(price_forecast["Forecast"].iloc[-1]),
    )

    price_history = monthly_price.dropna().rename(
        "Actual Price"
    ).reset_index()
    price_history.columns = ["Month", "Actual Price"]

    fig_price = go.Figure()

    fig_price.add_trace(
        go.Scatter(
            x=price_history["Month"],
            y=price_history["Actual Price"],
            mode="lines+markers",
            name="Historical Close Price",
        )
    )

    fig_price.add_trace(
        go.Scatter(
            x=price_forecast["Month"],
            y=price_forecast["Forecast"],
            mode="lines+markers",
            name="Forecast Close Price",
            line=dict(dash="dash"),
        )
    )

    fig_price.add_trace(
        go.Scatter(
            x=pd.concat([
                price_forecast["Month"],
                price_forecast["Month"].iloc[::-1],
            ]),
            y=pd.concat([
                price_forecast["Upper"],
                price_forecast["Lower"].iloc[::-1],
            ]),
            fill="toself",
            fillcolor="rgba(255, 165, 0, 0.18)",
            line=dict(color="rgba(255,255,255,0)"),
            hoverinfo="skip",
            name="Approx. 95% interval",
        )
    )

    fig_price.update_layout(
        title="Historical and Forecast Raw Material Prices",
        xaxis_title="Month",
        yaxis_title="Close Price (IDR)",
        yaxis_tickformat="~s",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(l=20, r=20, t=80, b=20),
    )

    st.plotly_chart(fig_price, use_container_width=True)

    st.caption(
        f"Model: {price_diagnostics['model']} | "
        f"Training observations: {price_diagnostics['observations']} months"
    )


# ============================================================
# RAW MATERIAL COST SCENARIO ANALYSIS
# ============================================================

st.divider()
st.subheader("💡 Raw Material Cost Scenario")

st.write(
    "Estimate the impact of a raw material cost increase or decrease "
    "on a future month's cost and profit. This is a scenario analysis, "
    "not a separate prediction of sales volume."
)

if (
    "TotalRawMaterialCost" in sales_selected.columns
    and not sales_selected.empty
):
    historical_monthly_cost = (
        sales_selected.groupby("Month", as_index=False)
        ["TotalRawMaterialCost"].sum()
        .sort_values("Month")
    )

    if not historical_monthly_cost.empty:
        baseline_cost = float(
            historical_monthly_cost["TotalRawMaterialCost"].tail(3).mean()
        )

        baseline_sales = float(
            monthly_sales.dropna().tail(3).mean()
        ) if not monthly_sales.dropna().empty else 0

        scenario_change = st.slider(
            "Assumed raw material cost change (%)",
            min_value=-50,
            max_value=100,
            value=10,
            step=5,
        )

        scenario_cost = baseline_cost * (
            1 + scenario_change / 100
        )

        cost_difference = scenario_cost - baseline_cost

        # Assumes sales revenue and all other costs remain unchanged.
        estimated_profit_impact = -cost_difference

        sc1, sc2, sc3 = st.columns(3)

        sc1.metric(
            "Baseline Monthly Raw Material Cost",
            format_idr_compact(baseline_cost),
        )

        sc2.metric(
            "Scenario Monthly Cost",
            format_idr_compact(scenario_cost),
            delta=format_idr_compact(cost_difference),
        )

        sc3.metric(
            "Estimated Profit Impact",
            format_idr_compact(estimated_profit_impact),
        )

        if scenario_change > 0:
            st.warning(
                "In this scenario, raw material costs increase. "
                "If selling prices, volumes, and other costs remain "
                "unchanged, estimated profit decreases."
            )
        elif scenario_change < 0:
            st.success(
                "In this scenario, raw material costs decrease. "
                "If selling prices, volumes, and other costs remain "
                "unchanged, estimated profit increases."
            )
        else:
            st.info("The scenario assumes no change in raw material cost.")

        st.caption(
            "Baseline cost is the average monthly raw material cost over "
            "the latest three observed months. Estimated profit impact "
            "assumes no changes to sales, production costs, or pricing."
        )
    else:
        st.info("Not enough cost data for scenario analysis.")
else:
    st.info(
        "TotalRawMaterialCost is unavailable in SalesTransaction, "
        "so the cost scenario cannot be calculated."
    )


# ============================================================
# DOWNLOAD FORECASTS
# ============================================================

st.divider()
st.subheader("⬇️ Export Forecasts")

download_frames = []

if "sales_forecast" in locals():
    sales_export = sales_forecast.copy()
    sales_export["Forecast Type"] = "Net Sales"
    download_frames.append(sales_export)

if "price_forecast" in locals():
    price_export = price_forecast.copy()
    price_export["Forecast Type"] = "Raw Material Close Price"
    download_frames.append(price_export)

if download_frames:
    export_df = pd.concat(download_frames, ignore_index=True)
    export_df["Month"] = pd.to_datetime(export_df["Month"]).dt.strftime(
        "%Y-%m-%d"
    )

    st.download_button(
        label="Download Forecast Report (CSV)",
        data=export_df.to_csv(index=False).encode("utf-8-sig"),
        file_name="ggf_predictive_analytics_forecast.csv",
        mime="text/csv",
    )

st.caption(
    "GGF Beverage Dashboard | Predictive Analytics"
)
