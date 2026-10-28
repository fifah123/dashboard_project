from pathlib import Path
import re

import pandas as pd
import streamlit as st

from utils.cleaning import (
    clean_column_names,
    clean_numeric_column,
    get_first_existing_column,
    normalize_sku,
    normalize_peak_season
)

# ============================================================
# GENERAL EXCEL LOADER — SALES PERFORMANCE
# ============================================================

@st.cache_data(show_spinner="Loading dashboard data...")
def load_data(
    excel_path: str,
    file_mtime: float | None = None,
):
    """
    General-purpose loader for dashboard pages.

    Returns:
        sales_df, target_df, product_df
    """
    del file_mtime

    path = Path(excel_path)

    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")

    sheets = pd.read_excel(
        path,
        sheet_name=None,
        engine="openpyxl",
    )

    # Match sheet names without depending on capitalization or spaces.
    normalized_names = {
        re.sub(r"[^a-z0-9]", "", name.lower()): name
        for name in sheets
    }

    def get_sheet(*candidates):
        for candidate in candidates:
            key = re.sub(r"[^a-z0-9]", "", candidate.lower())
            if key in normalized_names:
                return sheets[normalized_names[key]].copy()
        return pd.DataFrame()

    sales_df = get_sheet(
        "SalesTransaction",
        "Sales Transactions",
        "Sales",
    )

    target_df = get_sheet(
        "SalesTarget",
        "Sales Target",
        "Target",
    )

    product_df = get_sheet(
        "MstProduct",
        "ProductMaster",
        "Products",
    )

    if sales_df.empty:
        raise ValueError(
            "Could not find a sales transaction sheet. "
            f"Available sheets: {list(sheets)}"
        )

    sales_df = clean_column_names(sales_df)
    target_df = clean_column_names(target_df)
    product_df = clean_column_names(product_df)

    # Resolve the transaction date column.
    date_column = get_first_existing_column(
        sales_df,
        [
            "TransactionDate",
            "TranscationDate",
            "Transaction Date",
            "Transcation Date",
            "Date",
        ],
    )

    if date_column is None:
        raise ValueError(
            "Could not identify the sales transaction date column. "
            f"Available columns: {list(sales_df.columns)}"
        )

    if "SKU" not in sales_df.columns:
        raise ValueError(
            "Sales transactions must contain an SKU column. "
            f"Available columns: {list(sales_df.columns)}"
        )

    sales_df["SKU"] = normalize_sku(sales_df["SKU"])
    sales_df["TransactionDate"] = pd.to_datetime(
        sales_df[date_column],
        errors="coerce",
    )

    sales_df = sales_df.dropna(
        subset=["SKU", "TransactionDate"]
    ).copy()

    # Convert known numeric columns when available.
    numeric_columns = [
        "Qty",
        "SellingPrice",
        "TotalSellingPrice",
        "DiscPercentage",
        "Discount",
        "TotalDiscount",
        "TotalNetSellingPrice",
        "RawMaterialCost",
        "TotalRawMaterialCost",
        "ProductionCost",
        "TotalProductionCost",
        "TotalCost",
        "Profit&Lost",
    ]

    for column in numeric_columns:
        if column in sales_df.columns:
            sales_df = clean_numeric_column(
                sales_df,
                column,
            )

    if "SKU" in product_df.columns:
        product_df["SKU"] = normalize_sku(product_df["SKU"])

    if "SKU" in target_df.columns:
        target_df["SKU"] = normalize_sku(target_df["SKU"])

    return sales_df, target_df, product_df


# ============================================================
# SPECIALIZED PROFIT & LOSS LOADER
# ============================================================

@st.cache_data(show_spinner="Loading Profit & Loss data...")
def load_profit_loss_data(
    excel_path: str,
    modified_time: float | None = None,
) -> pd.DataFrame:
    """
    Specialized loader for the Profit & Loss page.

    Keeps its own product enrichment, cost calculations,
    recorded profit, and reconciliation fields.
    """
    del modified_time

    path = Path(excel_path)

    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")

    sales = pd.read_excel(
        path,
        sheet_name="SalesTransaction",
        engine="openpyxl",
    )

    products = pd.read_excel(
        path,
        sheet_name="MstProduct",
        engine="openpyxl",
    )

    sales = clean_column_names(sales)
    products = clean_column_names(products)

    required = ["SKU", "Qty", "TotalNetSellingPrice"]
    missing = [col for col in required if col not in sales.columns]

    if missing:
        raise ValueError(
            f"Missing required sales columns: {missing}"
        )

    if "SKU" not in products.columns:
        raise ValueError("MstProduct must contain an SKU column.")

    date_column = get_first_existing_column(
        sales,
        [
            "TranscationDate",
            "TransactionDate",
            "Transaction Date",
            "Transcation Date",
        ],
    )

    if date_column is None:
        raise ValueError(
            "Could not identify the transaction date column."
        )

    sales["SKU"] = normalize_sku(sales["SKU"])
    products["SKU"] = normalize_sku(products["SKU"])

    sales["TransactionDate"] = pd.to_datetime(
        sales[date_column],
        errors="coerce",
    )

    sales = sales.dropna(
        subset=["TransactionDate", "SKU"]
    ).copy()

    numeric_columns = [
        "Qty",
        "SellingPrice",
        "TotalSellingPrice",
        "DiscPercentage",
        "Discount",
        "TotalDiscount",
        "TotalNetSellingPrice",
        "RawMaterialCost",
        "TotalRawMaterialCost",
        "ProductionCost",
        "TotalProductionCost",
        "TotalCost",
        "Profit&Lost",
    ]

    for column in numeric_columns:
        if column in sales.columns:
            sales = clean_numeric_column(sales, column)

    raw_available = "TotalRawMaterialCost" in sales.columns
    production_available = "TotalProductionCost" in sales.columns
    discount_available = "TotalDiscount" in sales.columns

    if not raw_available and "RawMaterialCost" in sales.columns:
        sales["TotalRawMaterialCost"] = (
            sales["RawMaterialCost"] * sales["Qty"]
        )
        raw_available = True

    if (
        not production_available
        and "ProductionCost" in sales.columns
    ):
        sales["TotalProductionCost"] = (
            sales["ProductionCost"] * sales["Qty"]
        )
        production_available = True

    product_columns = [
        "SKU",
        *[
            col
            for col in [
                "Description",
                "ShortDescription",
                "Category",
                "CategoryCode",
                "UOM",
            ]
            if col in products.columns
        ],
    ]

    products = products[product_columns].drop_duplicates(
        subset=["SKU"],
        keep="last",
    )

    sales = sales.drop(
        columns=[
            col
            for col in [
                "Description",
                "ShortDescription",
                "Category",
                "CategoryCode",
                "UOM",
            ]
            if col in sales.columns
        ],
        errors="ignore",
    )

    sales = sales.merge(
        products,
        on="SKU",
        how="left",
        validate="many_to_one",
    )

    short_name = sales.get(
        "ShortDescription",
        pd.Series(pd.NA, index=sales.index),
    )

    description = sales.get(
        "Description",
        pd.Series(pd.NA, index=sales.index),
    )

    sales["Product"] = (
        short_name.fillna(description)
        .fillna(sales["SKU"])
        .astype(str)
    )

    sales["Category"] = (
        sales.get(
            "Category",
            pd.Series("Uncategorized", index=sales.index),
        )
        .fillna("Uncategorized")
        .astype(str)
    )

    sales["Outlet"] = (
        sales.get(
            "Outlet",
            pd.Series("Unknown Outlet", index=sales.index),
        )
        .fillna("Unknown Outlet")
        .astype(str)
    )

    sales["NetSales"] = sales["TotalNetSellingPrice"]

    if "TotalCost" in sales.columns:
        sales["TotalCostCalc"] = sales["TotalCost"]
        sales["TotalCostSource"] = "TotalCost"
    else:
        sales["TotalCostCalc"] = (
            sales.get(
                "TotalRawMaterialCost",
                pd.Series(0.0, index=sales.index),
            ).fillna(0)
            + sales.get(
                "TotalProductionCost",
                pd.Series(0.0, index=sales.index),
            ).fillna(0)
        )
        sales["TotalCostSource"] = "Raw material + production"

    if "Profit&Lost" in sales.columns:
        sales["ProfitCalc"] = sales["Profit&Lost"]
        sales["ProfitSource"] = "Profit&Lost (source)"
    else:
        sales["ProfitCalc"] = (
            sales["NetSales"] - sales["TotalCostCalc"]
        )
        sales["ProfitSource"] = "Net sales - total cost"

    for column in [
        "TotalRawMaterialCost",
        "TotalProductionCost",
        "TotalDiscount",
    ]:
        if column not in sales.columns:
            sales[column] = 0.0
        else:
            sales[column] = sales[column].fillna(0)

    sales["GrossSales"] = (
        sales["TotalSellingPrice"]
        if "TotalSellingPrice" in sales.columns
        else sales["NetSales"] + sales["TotalDiscount"]
    )

    sales["YearMonth"] = (
        sales["TransactionDate"].dt.to_period("M").astype(str)
    )
    sales["Month"] = (
        sales["TransactionDate"].dt.to_period("M").dt.to_timestamp()
    )

    sales["HasRawMaterialComponent"] = raw_available
    sales["HasProductionComponent"] = production_available
    sales["HasDiscountAmount"] = discount_available

    return sales



# Loading Raw Material data
@st.cache_data(show_spinner="Loading raw material data...")
def load_material_data(
    file_path: str,
    modified_time: float,
) -> pd.DataFrame:
    """Load and prepare raw material price trend data."""
    del modified_time

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")

    raw = pd.read_excel(
        path,
        sheet_name="RawMatPriceTrend",
        engine="openpyxl",
    )
    raw = clean_column_names(raw)

    required_columns = ["Date", "SKU", "Close Price"]
    missing = [
        column
        for column in required_columns
        if column not in raw.columns
    ]

    if missing:
        raise ValueError(
            "Missing columns in RawMatPriceTrend: "
            + ", ".join(missing)
        )

    raw["Date"] = pd.to_datetime(
        raw["Date"],
        errors="coerce",
    )
    raw["SKU"] = normalize_sku(raw["SKU"])

    raw = raw.dropna(
        subset=["Date", "SKU"]
    ).copy()

    numeric_columns = [
        "Open Price",
        "Close Price",
        "Open-Close Change (%)",
        "Moving Avg (3)",
        "Harvest Success Rate (%)",
    ]

    for column in numeric_columns:
        if column in raw.columns:
            raw = clean_numeric_column(raw, column)

    # Fill missing month values.
    if "Month" not in raw.columns:
        raw["Month"] = raw["Date"].dt.strftime("%B")
    else:
        raw["Month"] = raw["Month"].fillna(
            raw["Date"].dt.strftime("%B")
        )

    # Normalize season labels if the helper exists in this module.
    if "Is Peak Season" in raw.columns:
        raw["Season Status"] = raw["Is Peak Season"].apply(
            normalize_peak_season
        )
    else:
        raw["Season Status"] = "Unknown"

    raw = raw.sort_values(
        ["SKU", "Date"]
    ).reset_index(drop=True)

    # Calculate a fallback moving average when necessary.
    if (
        "Moving Avg (3)" not in raw.columns
        or raw["Moving Avg (3)"].notna().sum() == 0
    ):
        raw["Moving Avg (3)"] = (
            raw.groupby("SKU")["Close Price"]
            .transform(
                lambda series: series.rolling(
                    window=3,
                    min_periods=1,
                ).mean()
            )
        )

    # Merge product metadata.
    try:
        products = pd.read_excel(
            path,
            sheet_name="MstProduct",
            engine="openpyxl",
        )
    except ValueError:
        products = pd.DataFrame()

    if not products.empty:
        products = clean_column_names(products)

        if "SKU" in products.columns:
            products["SKU"] = normalize_sku(products["SKU"])

            metadata_columns = [
                column
                for column in [
                    "SKU",
                    "Description",
                    "ShortDescription",
                    "Category",
                ]
                if column in products.columns
            ]

            products = products[metadata_columns].drop_duplicates(
                subset=["SKU"],
                keep="last",
            )

            raw = raw.merge(
                products,
                on="SKU",
                how="left",
                validate="many_to_one",
            )

    short_name = (
        raw["ShortDescription"].astype("string")
        if "ShortDescription" in raw.columns
        else pd.Series(pd.NA, index=raw.index, dtype="string")
    )

    description = (
        raw["Description"].astype("string")
        if "Description" in raw.columns
        else pd.Series(pd.NA, index=raw.index, dtype="string")
    )

    raw["Product"] = (
        short_name.fillna(description)
        .fillna(raw["SKU"])
        .astype(str)
    )

    if "Category" not in raw.columns:
        raw["Category"] = "Uncategorized"

    raw["Category"] = (
        raw["Category"]
        .fillna("Uncategorized")
        .astype(str)
    )

    raw["Month Period"] = (
        raw["Date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    return raw




def _parse_number(value):
    """Convert numeric values, including formatted strings, to floats."""
    if pd.isna(value):
        return float("nan")

    if isinstance(value, (int, float)):
        return float(value)

    value = str(value).strip()

    if not value:
        return float("nan")

    # Handle common currency symbols and thousands separators.
    value = (
        value.replace("IDR", "")
        .replace("Rp", "")
        .replace(" ", "")
    )

    # Handle decimal and thousands separators.
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")

    try:
        return float(value)
    except (ValueError, TypeError):
        return float("nan")


def _find_date_column(df, candidates):
    """Find a date column using exact or normalized column names."""
    normalized = {
        str(column).strip().lower().replace(" ", "").replace("_", ""):
            column
        for column in df.columns
    }

    for candidate in candidates:
        key = candidate.strip().lower().replace(" ", "").replace("_", "")
        if key in normalized:
            return normalized[key]

    return None

# load predictive data
@st.cache_data(show_spinner="Loading forecasting data...")
def load_predictive_data(
    file_path: str,
    modified_time: float,
):
    """Load sales, raw-material prices, and product metadata for forecasting."""
    del modified_time

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Workbook not found: {path}")

    # ========================================================
    # PRODUCT MASTER
    # ========================================================
    products = pd.read_excel(
        path,
        sheet_name="MstProduct",
        engine="openpyxl",
    )
    products = clean_column_names(products)

    if "SKU" not in products.columns:
        raise ValueError("MstProduct must contain SKU.")

    products["SKU"] = normalize_sku(products["SKU"])
    products = products.dropna(subset=["SKU"]).copy()

    for column in ["ShortDescription", "Description"]:
        if column not in products.columns:
            products[column] = pd.NA

    if "Category" not in products.columns:
        products["Category"] = "Uncategorized"

    products["Product"] = (
        products["ShortDescription"]
        .fillna(products["Description"])
        .fillna(products["SKU"])
        .astype(str)
    )

    products["Category"] = (
        products["Category"]
        .fillna("Uncategorized")
        .astype(str)
    )

    products = products[
        ["SKU", "Product", "Category"]
    ].drop_duplicates(subset=["SKU"], keep="last")

    # ========================================================
    # SALES TRANSACTIONS
    # ========================================================
    sales = pd.read_excel(
        path,
        sheet_name="SalesTransaction",
        engine="openpyxl",
    )
    sales = clean_column_names(sales)

    date_col = _find_date_column(
        sales,
        [
            "TranscationDate",
            "TransactionDate",
            "Transaction Date",
        ],
    )

    if date_col is None:
        raise ValueError(
            "SalesTransaction must contain a transaction date column."
        )

    if "SKU" not in sales.columns:
        raise ValueError("SalesTransaction must contain SKU.")

    if "TotalNetSellingPrice" not in sales.columns:
        raise ValueError(
            "SalesTransaction must contain TotalNetSellingPrice."
        )

    sales["Date"] = pd.to_datetime(
        sales[date_col],
        errors="coerce",
    )
    sales["SKU"] = normalize_sku(sales["SKU"])

    sales["TotalNetSellingPrice"] = (
        sales["TotalNetSellingPrice"].map(_parse_number)
    )

    sales = sales.dropna(
        subset=["Date", "SKU", "TotalNetSellingPrice"]
    ).copy()

    sales = sales.merge(
        products,
        on="SKU",
        how="left",
        validate="many_to_one",
    )

    sales["Product"] = sales["Product"].fillna(sales["SKU"])
    sales["Category"] = (
        sales["Category"].fillna("Uncategorized")
    )

    sales["Month"] = (
        sales["Date"].dt.to_period("M").dt.to_timestamp()
    )

    # Normalize optional cost fields.
    for column in [
        "TotalRawMaterialCost",
        "TotalProductionCost",
        "TotalDiscount",
        "Qty",
    ]:
        if column in sales.columns:
            sales[column] = sales[column].map(_parse_number)

    if "TotalRawMaterialCost" not in sales.columns:
        if {"RawMaterialCost", "Qty"}.issubset(sales.columns):
            sales["TotalRawMaterialCost"] = (
                sales["RawMaterialCost"] * sales["Qty"]
            )
        else:
            sales["TotalRawMaterialCost"] = 0.0

    sales["TotalRawMaterialCost"] = (
        sales["TotalRawMaterialCost"].fillna(0)
    )

    # ========================================================
    # MONTHLY SALES DATA
    # ========================================================
    monthly_sales = (
        sales.groupby(
            ["Month", "SKU", "Product", "Category"],
            as_index=False,
            dropna=False,
        )
        .agg(
            Sales=("TotalNetSellingPrice", "sum"),
            Transactions=("TotalNetSellingPrice", "size"),
            RawMaterialCost=("TotalRawMaterialCost", "sum"),
        )
        .sort_values(["SKU", "Month"])
        .reset_index(drop=True)
    )

    # ========================================================
    # RAW MATERIAL PRICE TRENDS
    # ========================================================
    raw = pd.read_excel(
        path,
        sheet_name="RawMatPriceTrend",
        engine="openpyxl",
    )
    raw = clean_column_names(raw)

    required_raw = ["Date", "SKU", "Close Price"]
    missing = [
        column
        for column in required_raw
        if column not in raw.columns
    ]

    if missing:
        raise ValueError(
            "RawMatPriceTrend is missing: "
            + ", ".join(missing)
        )

    raw["Date"] = pd.to_datetime(
        raw["Date"],
        errors="coerce",
    )
    raw["SKU"] = normalize_sku(raw["SKU"])
    raw["Close Price"] = raw["Close Price"].map(_parse_number)

    raw = raw.dropna(
        subset=["Date", "SKU", "Close Price"]
    ).copy()

    raw = raw.merge(
        products,
        on="SKU",
        how="left",
        validate="many_to_one",
    )

    raw["Product"] = raw["Product"].fillna(raw["SKU"])
    raw["Category"] = raw["Category"].fillna("Uncategorized")

    raw["Month"] = (
        raw["Date"].dt.to_period("M").dt.to_timestamp()
    )

    monthly_prices = (
        raw.groupby(
            ["Month", "SKU", "Product", "Category"],
            as_index=False,
            dropna=False,
        )
        .agg(
            ClosePrice=("Close Price", "mean"),
            PriceObservations=("Close Price", "count"),
        )
        .sort_values(["SKU", "Month"])
        .reset_index(drop=True)
    )

    return sales, raw, products, monthly_sales, monthly_prices