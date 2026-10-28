
import re

import numpy as np
import pandas as pd


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize whitespace in DataFrame column names."""
    df = df.copy()
    df.columns = [
        re.sub(r"\s+", " ", str(col).replace("\xa0", " ")).strip()
        for col in df.columns
    ]
    return df


def normalize_sku(series: pd.Series) -> pd.Series:
    """Normalize SKU values, including Excel-generated trailing .0."""
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
    )


def parse_number(value):
    """Parse numeric values from Excel, including Indonesian number formats."""
    if pd.isna(value):
        return np.nan

    if isinstance(value, (int, float, np.number)):
        return float(value)

    text = str(value).strip()
    text = text.replace("Rp", "").replace("rp", "")
    text = text.replace(" ", "").replace("\u00a0", "")

    if not text or text.lower() in {"nan", "none", "-", "null"}:
        return np.nan

    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]

    text = re.sub(r"[^\d,.\-]", "", text)

    if not text or text in {"-", ".", ","}:
        return np.nan

    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            # Example: 1.234,56 -> 1234.56
            text = text.replace(".", "").replace(",", ".")
        else:
            # Example: 1,234.56 -> 1234.56
            text = text.replace(",", "")

    elif "," in text:
        # Example: 1234,56 -> 1234.56
        text = text.replace(",", ".")

    elif "." in text:
        if text.count(".") > 1:
            # Example: 1.234.567 -> 1234567
            text = text.replace(".", "")
        else:
            left, right = text.split(".", 1)
            if len(right) == 3 and left.lstrip("-").isdigit():
                # Example: 1.234 -> 1234
                text = left + right

    try:
        result = float(text)
        return -result if negative else result
    except (ValueError, TypeError):
        return np.nan


def format_idr(value) -> str:
    """Format a value as Indonesian Rupiah."""
    value = 0 if pd.isna(value) else float(value)
    formatted = f"{abs(value):,.0f}".replace(",", ".")
    return f"-Rp {formatted}" if value < 0 else f"Rp {formatted}"


def format_idr_compact(value) -> str:
    """Format Rupiah values using K, M, or B suffixes."""
    if pd.isna(value):
        return "N/A"

    value = float(value)
    absolute = abs(value)

    if absolute >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:,.2f} B"
    if absolute >= 1_000_000:
        return f"Rp {value / 1_000_000:,.2f} M"
    if absolute >= 1_000:
        return f"Rp {value / 1_000:,.1f} K"

    return f"Rp {value:,.0f}"


def format_pct(value) -> str:
    """Format a percentage with its sign."""
    return "N/A" if pd.isna(value) else f"{value:+.2f}%"




def find_date_column(df: pd.DataFrame, candidates: list) -> str | None:
    """Return the first matching date column."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def clean_numeric_column(
    df: pd.DataFrame,
    column: str,
    default=None,
) -> pd.DataFrame:
    """Clean a numeric column and optionally fill missing values."""
    df = df.copy()

    if column in df.columns:
        df[column] = df[column].map(parse_number)
        if default is not None:
            df[column] = df[column].fillna(default)

    return df


def normalize_peak_season(value) -> str:
    """Normalize common Excel boolean representations."""
    if pd.isna(value):
        return "Unknown"

    if isinstance(value, (bool, np.bool_)):
        return "Peak Season" if value else "Off-Peak Season"

    text = str(value).strip().lower()

    if text in {"true", "1", "yes", "y", "peak", "peak season"}:
        return "Peak Season"

    if text in {"false", "0", "no", "n", "off-peak", "off peak"}:
        return "Off-Peak Season"

    return str(value)



def get_first_existing_column(
    df: pd.DataFrame,
    candidates: list[str],
):
    """Return the first matching column name."""
    for column in candidates:
        if column in df.columns:
            return column
    return None


def safe_ratio(numerator, denominator):
    """Return numerator / denominator * 100, or NaN when undefined."""
    if denominator == 0 or pd.isna(denominator):
        return float("nan")
    return numerator / denominator * 100


def default_outlet(options: list[str]):
    """Find an outlet label corresponding to Outlet 1."""
    for option in options:
        normalized = re.sub(r"[\s_-]+", "", str(option).lower())
        if normalized in {"outlet1", "1"}:
            return option
    for option in options:
        normalized = re.sub(r"[\s_-]+", "", str(option).lower())
        if "outlet1" in normalized:
            return option
    return options[0] if options else None

