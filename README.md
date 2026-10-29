# GGF Beverage Business Dashboard

An interactive Streamlit dashboard for exploring GGF Beverage sales, profitability, raw-material price movements, and forecast scenarios using `FruitsTrxDatasets.xlsx`.

## 🚀 Live Demo

**[Open the GGF Beverage Business Dashboard](https://khofifah-ds-ggf-dashboard-project.streamlit.app/)**

Explore interactive sales analytics, profitability insights, raw-material trends, and forecasting scenarios directly in your browser.

## 📌 Purpose

Turn transaction and raw-material history into understandable business insights. The dashboard is descriptive and exploratory; it is not an audited financial statement, procurement system, or guaranteed forecasting system.


## User Guide

## 1. Overview

The GGF Beverage Business Dashboard is an interactive application built with Streamlit to help users understand beverage sales performance, profitability, raw-material price movements, and potential future sales trends.

This guide explains how to navigate the dashboard, interpret its metrics, and use the insights to support business decisions.

### Dashboard Pages

| Page | Purpose |
|---|---|
| Executive Overview | Review overall business performance |
| Sales Performance | Analyze sales, products, discounts, and targets |
| Profit & Loss | Evaluate costs and profitability |
| Raw Material Analysis | Monitor raw-material prices and seasonal patterns |
| Predictive Analytics | Explore forecasts based on historical data |

*The available pages may vary depending on the version of the application.*

---

## 2. Getting Started

### Launch the dashboard

1. Open a terminal in the project directory.
2. Activate your Python virtual environment.
3. Run the following command:

   ```bash
   streamlit run app.py
   ```

4. Open the local URL displayed in your terminal, usually `http://localhost:8501`.

### Prepare the data

The dashboard uses `FruitsTrxDatasets.xlsx`. Ensure the workbook is available at the file path configured in the application.

The workbook contains product information, sales targets, sales transactions, and raw-material price history.

---

## 3. Navigation and Filters

### Navigate between pages

Use the Streamlit navigation menu to open the page you want to explore.

Start with the Executive Overview, then navigate to individual analytical pages to investigate specific business questions.

### Apply filters

Depending on the page, available filters may include:

- **Date range:** Select the period to analyze.
- **Product or SKU:** Focus on specific products.
- **Category:** Compare product categories.
- **Outlet:** Analyze sales by location.
- **Forecast settings:** Configure the forecasting period or method, where supported.

To use a filter:

1. Select the desired value or range.
2. Review the updated KPIs, charts, and tables.
3. Adjust other filters to investigate different segments.

**Important:** Check the selected filters before comparing results. KPIs calculated over different periods or product groups may not be directly comparable.

---

## 4. Executive Overview

### Purpose

The Executive Overview provides a high-level summary of business performance.

### What to look at

- **Net Sales:** Total recorded net sales for the selected scope.
- **Reported Profit:** Profit or loss recorded in the source data.
- **Profit Margin:** Reported profit as a percentage of net sales.
- **Target Achievement:** Actual net sales compared with the sales target.
- **Sales Trends:** Changes in sales and profitability over time.
- **Product Contribution:** Products contributing the most to sales or profit.

### How to use this page

1. Select the reporting period.
2. Review the headline KPIs.
3. Examine monthly trends to identify increases or decreases.
4. Compare product contributions to identify important revenue drivers.
5. Open Sales Performance or Profit & Loss for further investigation.

### Business questions

- Is the business meeting its sales target?
- Are sales and profit moving in the same direction?
- Which products contribute most to revenue?
- Which trends require further investigation?

---

## 5. Sales Performance

### Purpose

This page helps users understand sales results, product performance, discounts, and target achievement.

### Key metrics

| Metric | Meaning |
|---|---|
| Gross Sales | Sales value before discounts |
| Discounts | Total recorded discount value |
| Net Sales | Recorded net selling value |
| Units Sold | Total quantity sold |
| Discount Rate | Discounts as a percentage of gross sales |
| Target Achievement | Actual net sales as a percentage of target |
| Product Sales Share | A product's contribution to total net sales |

### How to analyze sales

1. Select the date range.
2. Apply product, category, or outlet filters if available.
3. Review total sales and units sold.
4. Examine sales trends to identify stronger and weaker periods.
5. Compare products by revenue and sales volume.
6. Review discount patterns and target achievement.
7. Inspect the transaction table for detailed records, where available.

### Interpreting the results

- **High sales:** The product generates substantial revenue.
- **Low sales:** Investigate demand, distribution, availability, or product performance.
- **High discount rate:** Review whether discounts are aligned with sales objectives.
- **Low target achievement:** Identify underperforming products, outlets, or periods.

High revenue does not necessarily mean high profitability. Use the Profit & Loss page to investigate costs and margins.

---

## 6. Profit & Loss

### Purpose

This page examines profitability and helps identify differences between recorded financial figures and calculated metrics.

### Key metrics

| Metric | Meaning |
|---|---|
| Net Sales | Recorded net sales |
| Total Cost | Recorded total cost |
| Reported Profit | Profit/loss from the source data |
| Calculated Profit | Net sales minus total cost |
| Profit Margin | Reported profit divided by net sales |
| Cost-to-Sales Ratio | Total cost divided by net sales |
| Reconciliation Difference | Difference between reported and calculated profit |

### How to analyze profitability

1. Select the period and available product filters.
2. Review net sales, total cost, and reported profit.
3. Compare profitability across products.
4. Examine monthly revenue and profit trends.
5. Review the cost structure if component data is available.
6. Investigate any reconciliation differences.

### Understanding profit reconciliation

The dashboard may compare two profit measures:

```text
Calculated Profit = Net Sales - Total Cost

Reconciliation Difference =
    Reported Profit - Calculated Profit
```

A non-zero difference indicates that the two measures do not agree under the selected definitions.

Possible areas to investigate include cost allocation, accounting definitions, discount treatment, timing, and source-data quality. The difference does not automatically mean the reported profit is incorrect.

**Important:** Treat source-reported profit and calculated profit as separate measures until the business confirms the official accounting definition.

### Business questions

- Which products generate the highest reported profit?
- Which products have low or negative margins?
- Are costs increasing faster than sales?
- Do reported and calculated profit figures agree?

---

## 7. Raw Material Analysis

### Purpose

This page helps users monitor raw-material price movements and explore historical price patterns.

### Key metrics and indicators

| Metric | Meaning |
|---|---|
| Latest Average Close Price | Average close price on the latest date in the filtered data |
| Price Change | Percentage movement between opening and closing prices |
| Period Price Change | Change between the first and last observed prices |
| Moving Average (3) | Average of three consecutive price observations |
| Products Monitored | Number of distinct SKUs in the selected data |
| Peak-Season Share | Share of known season records classified as peak season |

### How to analyze raw-material prices

1. Select the available date range and SKU filters.
2. Review the latest price indicators.
3. Examine opening and closing prices over time.
4. Compare price movements across SKUs.
5. Use the moving-average line to assess smoothed price trends.
6. Review seasonality indicators if available.
7. Inspect the detailed table or download the data if the page supports CSV export.

### Interpreting price movements

- **Increasing prices:** May indicate rising raw-material purchase-price exposure.
- **Decreasing prices:** May indicate easing price pressure.
- **Large price changes:** Review the underlying observations and confirm whether the movement is genuine.
- **Moving-average changes:** Help reveal broader movements while smoothing short-term fluctuations.

A moving average is a smoothing measure, not a forecast.

### Important limitation

Raw-material price trends do not directly explain finished-product profitability. To quantify the impact of material prices on beverage costs, the business needs a reliable mapping between raw materials and finished products, such as a bill of materials (BOM) or recipe.

---

## 8. Predictive Analytics

### Purpose

This page explores possible future values based on historical observations.

Forecast availability and model options depend on the implementation.

### How to generate a forecast

1. Select the target variable and any supported filters.
2. Confirm that the historical data contains valid dates and numeric values.
3. Select the forecasting method if the application provides a choice.
4. Set the forecast horizon.
5. Run or review the forecast.
6. Compare the predicted values with historical observations.
7. Review evaluation metrics or backtesting results when available.

### Understanding forecast results

- **Historical values:** Observations recorded in the source data.
- **Forecast values:** Model estimates for future periods.
- **Forecast horizon:** Number of future observations being estimated.
- **MAE:** Average absolute prediction error.
- **RMSE:** Prediction error metric that penalizes large errors more heavily.
- **WAPE:** Total absolute prediction error relative to total actual values, expressed as a percentage.

Lower error values generally indicate better predictions when comparing models on the same dataset and evaluation period.

### How to use forecasts

Use forecasts to explore potential scenarios, support planning discussions, and identify expected changes that require attention.

A forecast based only on historical sales may not account for promotions, holidays, price changes, stockouts, or supply constraints unless these factors are explicitly modeled.

**Important:** Forecasts are estimates, not guarantees. Evaluate them against historical observations before using them for business planning.

---

## 9. Reviewing and Exporting Data

Some pages may provide detailed tables or CSV downloads.

### Recommended workflow

1. Apply the required filters.
2. Review the summary charts and KPIs.
3. Inspect the underlying records.
4. Download the filtered data if an export option is available.
5. Use the exported records to investigate unexpected results.

When reviewing exported data, check for missing values, duplicate records, incorrect dates, inconsistent SKU identifiers, and unusual numeric values.

---

## 10. Troubleshooting

| Issue | What to check |
|---|---|
| Dashboard fails to start | Confirm dependencies are installed and run the correct Streamlit entry point |
| Workbook not found | Verify the workbook path configured in the application |
| Missing worksheet or column | Check the worksheet names and source column headers |
| Empty charts | Review filters, date parsing, and available numeric observations |
| Unexpected sales totals | Check duplicate transactions and joins with product or target data |
| Incorrect price values | Verify decimal and thousands separators |
| Profit differences | Review source definitions and cost calculations |
| Unexpected forecast | Check historical data, date frequency, outliers, and forecast settings |

---

## 11. Recommended Analysis Workflow

For a typical business review, follow this sequence:

1. **Review overall performance** using the Executive Overview.
2. **Investigate sales drivers** using Sales Performance.
3. **Evaluate profitability** using Profit & Loss.
4. **Monitor material prices** using Raw Material Analysis.
5. **Explore future scenarios** using Predictive Analytics.
6. **Validate findings** against detailed records and the relevant business definitions.

This workflow moves from understanding overall performance to investigating its potential drivers and exploring future scenarios.

---

## 12. Disclaimer

This dashboard is designed for exploratory business analysis and decision support. Results depend on the source workbook, implemented calculations, selected filters, and data quality.

Validate financial definitions and forecast performance with the appropriate business owners before using the results for formal reporting or operational decisions.
