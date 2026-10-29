# Business Analysis and Forecasting Methodology

## 1. Overview

The GGF Beverage Business Dashboard is an interactive Streamlit application for analyzing sales performance, profitability, raw material price movements, and potential future business outcomes.

The dashboard supports:

- Sales performance and target achievement monitoring
- Product, category, and outlet analysis
- Profitability analysis
- Raw material price trend analysis
- Monthly sales and price forecasting
- Forecast evaluation through historical backtesting
- Scenario analysis for business planning

> [!NOTE]
> The dashboard is intended for descriptive and exploratory analysis. Forecasts are estimates based on historical data and should not be interpreted as guaranteed outcomes or audited financial results.

---

## 2. Data Sources

The dashboard uses data from `FruitsTrxDatasets.xlsx`.

### 2.1 MstProduct

Contains product master data.

| Column | Description |
|---|---|
| `SKU` | Product identifier |
| `Description` | Full product description |
| `ShortDescription` | Short product name |
| `CategoryCode` | Category identifier |
| `Category` | Product category |
| `UOM` | Unit of measurement |
| `Currency` | Product currency |
| `Price` | Reference product price |

Product master data enriches sales transactions with product names and categories.

### 2.2 SalesTransaction

Contains historical sales transactions.

| Column | Description |
|---|---|
| `TranscationDate` | Transaction date; verify the source column spelling |
| `SKU` | Product identifier |
| `Qty` | Quantity sold |
| `TotalSellingPrice` | Gross sales amount |
| `TotalDiscount` | Discount amount |
| `TotalNetSellingPrice` | Net sales after discounts |
| `TotalRawMaterialCost` | Raw material cost, if available |
| `TotalProductionCost` | Production cost, if available |
| `Outlet` | Sales outlet |

This dataset is the primary source for historical sales analysis and sales forecasting.

### 2.3 SalesTarget

Contains sales targets used to evaluate actual sales performance.

Actual sales and targets must be aggregated to matching reporting periods and business dimensions before comparison.

### 2.4 RawMatPriceTrend

Contains historical raw material price observations and related attributes.

| Column | Description |
|---|---|
| `Date` | Price observation date |
| `SKU` | Product or material identifier |
| `Close Price` | Closing price |
| `Open Price` | Opening price, if available |
| `Open-Close Change (%)` | Percentage change between opening and closing prices |
| `Moving Avg (3)` | Three-period moving average, if supplied |
| `Harvest Success Rate (%)` | Harvest success rate, if supplied |
| `Month` | Associated month |
| `Is Peak Season` | Peak-season indicator |

This dataset supports price trend analysis and forecasting when sufficient historical observations are available.

---

## 3. Data Processing Workflow

The general workflow consists of the following steps:

1. Load the required Excel worksheets.
2. Standardize column names and data types.
3. Parse dates and convert numeric fields.
4. Normalize SKU values.
5. Merge sales transactions with product master data.
6. Handle missing values and duplicate product records.
7. Apply date, product, category, and outlet filters.
8. Aggregate data to the required reporting frequency.
9. Calculate business KPIs and prepare visualizations.
10. Prepare time series for forecasting when requested.

### 3.1 Product Mapping

Sales transactions can be enriched with product information using `SKU`.

```python
sales_df = sales_df.merge(
    products_df.drop_duplicates(
        subset=["SKU"],
        keep="last",
    ),
    on="SKU",
    how="left",
    suffixes=("", "_product"),
)
```

Duplicate handling should be validated to ensure the retained product record is appropriate.

### 3.2 Monthly Aggregation

Monthly analysis groups observations by calendar month.

For sales revenue, the typical aggregation is a sum. For raw material prices, a monthly average may be more appropriate.

The aggregation method must reflect the business question being answered.

---

## 4. Descriptive Business Analysis

### 4.1 Sales Performance

The dashboard can calculate the following KPIs.

**Gross Sales**

$$
\text{Gross Sales} = \sum_{i=1}^{n} \text{TotalSellingPrice}_i
$$

**Total Discount**

$$
\text{Total Discount} = \sum_{i=1}^{n} \text{TotalDiscount}_i
$$

**Net Sales**

$$
\text{Net Sales} = \sum_{i=1}^{n} \text{TotalNetSellingPrice}_i
$$

**Units Sold**

$$
\text{Units Sold} = \sum_{i=1}^{n} \text{Qty}_i
$$

Here, $n$ is the number of transactions included in the selected filters.

### 4.2 Discount Rate

The discount rate measures total discounts relative to gross sales.

$$
\text{Discount Rate} (\%) = \frac{\text{Total Discount}}{\text{Gross Sales}} \times 100
$$

If gross sales are zero or unavailable, the rate should be treated as undefined.

### 4.3 Sales Target Achievement

Target achievement compares actual net sales with the corresponding target.

$$
\text{Target Achievement} (\%) = \frac{\text{Net Sales}}{\text{Sales Target}} \times 100
$$

- Above 100%: actual sales exceed the target.
- Equal to 100%: actual sales meet the target.
- Below 100%: actual sales are below the target.

The target must be aligned with the same period and business dimensions as actual sales.

### 4.4 Target Gap

$$
\text{Target Gap} = \text{Net Sales} - \text{Sales Target}
$$

A positive gap indicates sales above target, while a negative gap indicates a shortfall.

### 4.5 Product, Category, and Outlet Analysis

Grouping sales by product, category, or outlet helps identify:

- Products contributing the most revenue
- Categories with strong or weak sales
- Outlets with high or low sales performance
- Changes in product mix
- Differences between sales volume and revenue contribution

High sales volume does not necessarily imply high revenue or high profitability.

### 4.6 Profitability Analysis

When cost data is complete and consistently defined, estimated profit can be calculated as:

$$
\text{Profit} = \text{Net Sales} - \text{Total Cost}
$$

$$
\text{Profit Margin} (\%) = \frac{\text{Profit}}{\text{Net Sales}} \times 100
$$

If total cost consists of raw material and production costs:

$$
\text{Total Cost} = \text{Raw Material Cost} + \text{Production Cost}
$$

The source definitions must be checked to prevent overlapping cost components. Missing cost information should not automatically be interpreted as zero.

### 4.7 Raw Material Price Analysis

Price changes can be calculated as:

$$
\text{Price Change} (\%) = \frac{\text{Current Price} - \text{Previous Price}}{\text{Previous Price}} \times 100
$$

A three-period moving average smooths short-term fluctuations:

$$
MA_t = \frac{P_t + P_{t-1} + P_{t-2}}{3}
$$

Where $P_t$ represents the price at period $t$. The periods may be daily or monthly, depending on how the data is aggregated.

If `Moving Avg (3)` already exists in the source data, its calculation should be verified before use.

---

## 5. Forecasting Methodology

### 5.1 Overview

The dashboard uses a lightweight forecasting method based on an **additive linear trend with optional monthly seasonality**.

The model is implemented in `fit_forecast(series, horizon=3)`.

Unlike more complex forecasting approaches, this implementation does not train a neural network or use an external forecasting library. It estimates a linear trend using NumPy's polynomial fitting function and optionally adjusts the trend using monthly seasonal effects.

The method has two configurations:

| Historical observations | Model configuration |
|---|---|
| 3–17 monthly observations | Linear trend |
| 18 or more monthly observations | Linear trend + monthly seasonality |

At least three valid monthly observations are required. If fewer than three observations remain after cleaning, the function raises a `ValueError`.

The default forecast horizon is three months, although a different horizon can be passed to the function.

### 5.2 Preparing the Time Series

The function first removes missing observations, converts the remaining values to floating-point numbers, and sorts them by index.

Conceptually, the input is a sequence of monthly observations:

$$
y_1, y_2, \ldots, y_n
$$

Where:

- $y_t$ is the observed value at month $t$.
- $n$ is the number of valid observations.

For sales forecasting, $y_t$ should represent the intended sales metric, such as total monthly net sales.

For raw material price forecasting, $y_t$ may represent the monthly average price.

> [!IMPORTANT]
> `fit_forecast()` expects the series index to contain valid datetime values with meaningful monthly positions. It does not aggregate transaction-level data into monthly values itself. That aggregation must happen before the function is called.

### 5.3 Step 1 — Estimate the Linear Trend

The model initially fits a straight line to the historical observations.

$$
\hat{y}_t = a + bt
$$

Where:

- $\hat{y}_t$ is the fitted value at time $t$.
- $a$ is the intercept, representing the estimated baseline at index zero.
- $b$ is the slope, representing the estimated change per monthly step.
- $t$ is the sequential time index.

The parameters are estimated by linear least squares using:

```python
slope, intercept = np.polyfit(x, y, 1)
```

The time index is constructed as:

```python
x = np.arange(n, dtype=float)
```

The slope indicates the overall direction of the historical trend:

- $b > 0$: increasing trend.
- $b < 0$: decreasing trend.
- $b \approx 0$: relatively flat linear trend.

A positive slope does not guarantee that future sales will increase. It only describes the fitted historical relationship.

The initial trend is:

$$
\text{Trend}_t = a + bt
$$

This trend is used directly when there is insufficient history for the seasonal model.

### 5.4 Step 2 — Determine Whether to Use Seasonality

The code enables monthly seasonality when:

```python
use_seasonality = n >= 18
```

This threshold requires at least 18 observations, equivalent to one and a half years of monthly data.

The reason for this threshold is to provide more than one annual cycle of data before estimating recurring calendar-month effects.

However, 18 observations are only the implementation's minimum threshold. They do not guarantee that the estimated seasonal pattern is stable or reliable. More years of data generally provide a better opportunity to distinguish recurring seasonality from unusual events.

When fewer than 18 observations are available, the model uses a linear trend without seasonal adjustments.

### 5.5 Step 3 — Estimate Monthly Seasonal Effects

When seasonality is enabled, the model first calculates the residuals from the initial linear trend:

$$
e_t = y_t - \text{Trend}_t
$$

A residual is the difference between the observed value and the initial trend estimate.

For example, if observed sales are higher than the trend in December, the December residual may be positive. If they are lower than the trend in February, the February residual may be negative.

The code groups residuals by calendar month and estimates a seasonal effect for each month using the median residual:

$$
s_m = \text{median}\left(e_t \mid \text{month}(t) = m\right)
$$

Where:

- $s_m$ is the estimated seasonal effect for calendar month $m$.
- $e_t$ is a residual from the initial trend.
- $\text{month}(t)$ identifies the calendar month of observation $t$.

The median is less sensitive to unusually large positive or negative residuals than the mean.

The implementation estimates an effect only when a calendar month has at least two observations. Otherwise, that month's initial seasonal effect remains zero.

The seasonal effects are then centered by subtracting their average:

$$
s_m^{\ast} = s_m - \frac{1}{12} \sum_{j=1}^{12} s_j
$$

This adjustment makes the average of the 12 seasonal effects equal to zero. It helps prevent the seasonal component from systematically shifting the overall level of the trend.

The seasonal component is additive, meaning it is expressed in the same units as the forecast target.

For example, if the model forecasts monthly sales in IDR, the seasonal effects are also expressed in IDR. They are not percentage multipliers.

### 5.6 Step 4 — Re-estimate the Trend After Removing Seasonality

Once seasonal effects have been estimated, the model removes the relevant effect from each historical observation:

$$
y_t^{\ast} = y_t - s_{\text{month}(t)}^{\ast}
$$

The deseasonalized series is then fitted with another linear trend:

$$
\hat{y}_t^{\ast} = a + bt
$$

The final fitted value for a historical observation adds the seasonal effect back:

$$
\hat{y}_t = a + bt + s_{\text{month}(t)}^{\ast}
$$

The implementation performs this adjustment with:

```python
deseasonalized = y - seasonal_pattern[month_numbers - 1]

slope, intercept = np.polyfit(x, deseasonalized, 1)

trend = intercept + slope * x

fitted = trend + seasonal_pattern[month_numbers - 1]
```

This process separates the estimated long-term trend from recurring calendar-month deviations.

The final fitted historical values are used to calculate residuals and estimate forecast uncertainty.

### 5.7 Step 5 — Generate Future Forecasts

The function creates future month-start dates after the final observed month.

The forecast horizon determines how many future monthly values are generated.

For a model without seasonality:

$$
\hat{y}_{n+h} = a + b(n + h - 1)
$$

For a model with monthly seasonality:

$$
\hat{y}_{n+h} = a + b(n + h - 1) + s_{\text{month}(n+h)}^{\ast}
$$

Here, $h$ is the forecast step, starting at 1 for the first future month.

The trend continues from the fitted historical line. When seasonality is enabled, the corresponding calendar-month effect is added to each forecast.

The code constructs the future trend positions using:

```python
future_x = np.arange(n, n + horizon, dtype=float)

forecast_values = intercept + slope * future_x
```

If seasonality is enabled, the seasonal effect for each future calendar month is added to the trend.

The function returns a DataFrame with these columns:

| Column | Meaning |
|---|---|
| `Month` | Future monthly date |
| `Forecast` | Estimated future value |
| `Lower` | Approximate lower prediction bound |
| `Upper` | Approximate upper prediction bound |

The output is intended to support a visual comparison between historical observations and predicted future values.

### 5.8 Step 6 — Estimate Prediction Intervals

The function calculates the standard deviation of the historical residuals:

$$
s_e = \sqrt{\frac{1}{n-1} \sum_{t=1}^{n} (y_t - \hat{y}_t)^2}
$$

This is the sample standard deviation of the residuals from the fitted model.

The code uses:

```python
residuals = y - fitted

residual_std = float(np.std(residuals, ddof=1))
```

It then increases the uncertainty estimate with the forecast horizon:

$$
u_h = s_e \sqrt{1 + \frac{h}{n}}
$$

Where:

- $u_h$ is the approximate uncertainty for forecast step $h$.
- $s_e$ is the historical residual standard deviation.
- $n$ is the number of observations.

The lower and upper bounds are calculated using a multiplier of 1.96:

$$
L_h = \hat{y}_{n+h} - 1.96\,u_h
$$

$$
U_h = \hat{y}_{n+h} + 1.96\,u_h
$$

The value 1.96 is commonly associated with an approximate 95% interval under normality assumptions.

> [!WARNING]
> These bounds are heuristic, approximate prediction intervals. They are not formal, statistically calibrated 95% prediction intervals. The implementation does not explicitly account for all sources of uncertainty, such as uncertainty in the estimated trend and seasonal effects, changing residual variance, or autocorrelation.
>
> The actual coverage of these intervals has not been established by the code.

### 5.9 Step 7 — Prevent Negative Forecasts

The model clips the forecast and interval bounds to zero:

```python
forecast["Forecast"] = forecast["Forecast"].clip(lower=0)
forecast["Lower"] = forecast["Lower"].clip(lower=0)
forecast["Upper"] = forecast["Upper"].clip(lower=0)
```

This prevents negative predicted sales or prices when the business metric cannot reasonably be negative.

However, clipping is a business constraint rather than a statistical correction. It does not make the underlying model more accurate, and it can affect the interpretation of the interval when a bound reaches zero.

### 5.10 Model Diagnostics

The function returns a diagnostics dictionary containing:

| Diagnostic | Description |
|---|---|
| `model` | Selected model name |
| `observations` | Number of valid historical observations |
| `residual_std` | Standard deviation of historical fitted residuals |
| `fitted` | Historical fitted values indexed by the original dates |

The model name is either:

- `Linear trend`
- `Linear trend + monthly seasonality`

The fitted values represent the model's estimates for the historical observations. They are useful for checking how closely the fitted trend and seasonal adjustments follow the historical series.

The residual standard deviation summarizes the typical scale of the model's historical residuals. It is not, by itself, a measure of future forecast accuracy.

---

## 6. Forecast Backtesting

### 6.1 Purpose of Backtesting

Backtesting evaluates how a forecasting method performs on historical observations that were withheld from model fitting.

The dashboard's `backtest_forecast(series)` function uses a chronological holdout approach.

It does not randomly split the data, because a random split could allow later observations to influence a model evaluated on earlier dates.

### 6.2 Minimum Data Requirement

The function requires at least eight valid observations:

```python
if len(series) < 8:
    return None
```

When fewer than eight observations are available, backtesting is skipped.

This requirement is separate from the forecasting model's minimum requirement of three observations. A series may be long enough to generate a forecast but too short for the implemented backtest.

### 6.3 Training and Test Periods

The function determines the test-set size using:

```python
test_size = min(3, max(1, len(series) // 5))
```

This holds out approximately the final 20% of the series, subject to a minimum of one and a maximum of three observations.

For example:

| Total observations | Test observations | Training observations |
|---:|---:|---:|
| 8 | 1 | 7 |
| 10 | 2 | 8 |
| 15 | 3 | 12 |
| 24 | 3 | 21 |
| 36 | 3 | 33 |

The training period contains the earlier observations. The test period contains the final observations.

The model is fitted using only the training series:

```python
forecast, _ = fit_forecast(train, horizon=test_size)
```

The generated forecast is then compared with the actual observations in the held-out test period.

This estimates how the model performs when forecasting beyond the end of its training data.

### 6.4 Mean Absolute Error (MAE)

MAE measures the average absolute difference between actual and predicted values.

$$
MAE = \frac{1}{n} \sum_{t=1}^{n} \left| y_t - \hat{y}_t \right|
$$

Where:

- $y_t$ is the actual value.
- $\hat{y}_t$ is the predicted value.
- $n$ is the number of test observations.

The implementation is:

```python
mae = float(np.mean(np.abs(actual - predicted)))
```

MAE is expressed in the same units as the forecast target.

For example, if the target is monthly sales in IDR, the MAE is expressed in IDR. If the target is raw material price, the MAE is expressed in the corresponding price unit.

A lower MAE indicates smaller average absolute errors on the test observations.

### 6.5 Mean Absolute Percentage Error (MAPE)

MAPE measures the average absolute prediction error relative to actual values.

$$
MAPE = \frac{100}{n} \sum_{t=1}^{n} \left| \frac{y_t - \hat{y}_t}{y_t} \right|
$$

MAPE is commonly interpreted as a percentage error.

The implementation excludes test observations whose actual values equal zero:

```python
nonzero = actual != 0

mape = (
    float(
        np.mean(
            np.abs(
                (actual[nonzero] - predicted[nonzero])
                / actual[nonzero]
            )
        ) * 100
    )
    if nonzero.any()
    else np.nan
)
```

If all actual test values are zero, MAPE is returned as `NaN` because it cannot be calculated from those observations.

MAPE can also be unstable when actual values are close to zero. It should be interpreted alongside MAE rather than used as the only evaluation metric.

### 6.6 Backtesting Output

The function returns a dictionary containing:

| Field | Description |
|---|---|
| `MAE` | Mean absolute error on the held-out test period |
| `MAPE` | Mean absolute percentage error, excluding zero actuals |
| `Test size` | Number of held-out observations |

The current function does not return RMSE or compare multiple forecasting algorithms.

### 6.7 How to Interpret the Results

| Result | Interpretation |
|---|---|
| Lower MAE | Smaller average absolute prediction error in the target's units |
| Lower MAPE | Smaller average percentage error for nonzero actual values |
| High MAE and high MAPE | Predictions may be far from actual values in both absolute and relative terms |
| Low MAE but high MAPE | Absolute errors may be small while actual values are also small |
| MAPE is `NaN` | All actual test observations are zero, so MAPE cannot be calculated |

There is no universal MAE or MAPE threshold that guarantees a good forecast. Acceptable error depends on the scale, volatility, and business use of the metric.

The forecast should also be compared with a simple baseline when possible. For example, a naive baseline predicts the last observed value for the next period:

$$
\hat{y}_{t+1} = y_t
$$

A model that does not outperform a reasonable baseline may offer limited forecasting value.

### 6.8 Backtesting Limitations

The implemented backtest has several limitations:

1. **Small test set:** It evaluates at most three observations, so the metrics may be sensitive to individual months.
2. **Single holdout:** It does not repeat the evaluation across multiple historical forecast origins.
3. **No model comparison:** It evaluates the selected model without comparing alternative forecasting methods.
4. **No interval coverage evaluation:** It does not check how often actual values fall inside the prediction bounds.
5. **Potentially unstable MAPE:** Percentage errors are undefined for zero actuals and can be large for small actual values.
6. **Historical dependence:** Performance on the holdout period may not represent future conditions.

For more robust evaluation, consider rolling-origin backtesting, a longer test period, baseline comparison, and additional metrics when appropriate.

---

## 7. Scenario Analysis

Scenario analysis estimates how outcomes change when selected assumptions are adjusted.

A simple sales scenario can apply a percentage adjustment to a baseline forecast:

$$
\text{Scenario Sales}_t = \text{Baseline Forecast}_t \left(1 + \frac{r}{100}\right)
$$

Where $r$ is the assumed percentage adjustment.

For example, an adjustment of 10% produces a scenario value equal to 110% of the baseline forecast.

This is a sensitivity calculation, not a new statistical forecast. It does not independently model demand, price elasticity, capacity constraints, or other business effects.

Scenario assumptions should be clearly identified as user-defined inputs.

---

## 8. How to Interpret the Dashboard

| Analysis | Business question | Interpretation |
|---|---|---|
| Net Sales | How much revenue was generated after discounts? | Review the amount and trend over time. |
| Units Sold | How many units were sold? | Compare volume across products and outlets. |
| Discount Rate | How much discount was given relative to gross sales? | Investigate unusually high discount rates. |
| Target Achievement | Did sales meet the target? | Above 100% means the target was exceeded. |
| Target Gap | How far above or below target were sales? | Positive means above target; negative means below target. |
| Profit Margin | How much profit was generated relative to net sales? | Interpret only when profit and cost definitions are valid. |
| Raw Material Price | How did input prices change over time? | Identify trends and potential volatility. |
| Forecast | What values does the model estimate for future periods? | Use as a planning input, not a guarantee. |
| Backtesting | How accurately did the model forecast withheld observations? | Interpret MAE and MAPE in the context of the target and test period. |
| Scenario Analysis | How would results change under an assumption? | Compare the scenario against the baseline forecast. |

---

## 9. Assumptions and Limitations

1. **Data quality:** Missing values, duplicate records, inconsistent SKUs, and incorrect dates can affect results.
2. **Target alignment:** Actual sales and targets must use compatible periods and dimensions.
3. **Cost completeness:** Profitability calculations may be unreliable if cost components are incomplete or overlapping.
4. **Linear trend:** The model assumes the overall trend can be approximated by a straight line. It does not explicitly model trend breaks or nonlinear growth.
5. **Seasonality threshold:** Seasonal adjustments are enabled at 18 observations, but this threshold alone does not establish reliable annual seasonality.
6. **Additive seasonality:** Seasonal effects are expressed in the same units as the target. Their absolute magnitude does not automatically grow with the sales level.
7. **Residual-based intervals:** Prediction bounds are approximate and have not been statistically calibrated.
8. **Nonnegative clipping:** Forecasts and bounds are clipped at zero, which may affect interval interpretation.
9. **Backtesting:** The single holdout of at most three observations provides limited evidence about future accuracy.
10. **External factors:** The model does not explicitly account for promotions, supply disruptions, competitor activity, inflation, or changes in customer demand.
11. **Scenario assumptions:** Scenario outputs depend on the assumptions selected by the user.

---

## 10. Recommended Validation Checklist

- [ ] Gross sales and net sales reconcile with the source transactions.
- [ ] Discount calculations use consistent definitions and signs.
- [ ] Product mapping and category labels are correct.
- [ ] Monthly aggregation uses the intended date field and metric.
- [ ] Sales targets are aligned with actual sales periods.
- [ ] Cost fields are complete and consistently defined.
- [ ] Raw material prices use the intended observation frequency.
- [ ] Forecasts begin after the last observed month.
- [ ] Seasonal effects are based on valid monthly observations.
- [ ] Backtesting respects chronological order.
- [ ] MAE and MAPE are interpreted in the context of the target.
- [ ] Zero and missing values are handled appropriately.
- [ ] Prediction intervals are labeled as approximate.
- [ ] Scenario assumptions are clearly displayed.

---

## 11. Code Areas to Maintain

When updating the dashboard, review the relevant code for:

- **Data loading:** Excel sheet selection, column names, and file paths.
- **Data cleaning:** Date parsing, numeric conversion, SKU normalization, and missing-value handling.
- **Business analysis:** KPI definitions, aggregation logic, filters, and visualizations.
- **Forecasting:** Time-series preparation, trend fitting, seasonal adjustments, forecast horizon, and prediction bounds.
- **Backtesting:** Minimum data requirements, chronological split, test size, and evaluation metrics.
- **Scenario analysis:** Assumptions, adjustment formulas, and result labeling.

The documented forecasting behavior should match the implementation. Update this document whenever the model logic changes.

---

## 12. Conclusion

The GGF Beverage Business Dashboard combines descriptive analytics, a lightweight trend-and-seasonality forecasting method, historical backtesting, and scenario analysis.

The forecasting model is designed to be transparent and easy to interpret. Its results depend on the quality and length of the historical series, the stability of its trend and seasonal patterns, and the limitations of its approximate uncertainty estimates.

Forecasts should support business judgment rather than replace data validation, baseline comparison, or operational expertise.
