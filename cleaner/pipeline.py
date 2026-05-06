# =============================================================================
# cleaner/pipeline.py — Clean and standardise raw market data
# =============================================================================
# Raw data from yfinance is rarely perfect:
#   - Missing values (NaN) on days with no trading activity
#   - Duplicate dates (rare but happens with some tickers)
#   - Zero or negative prices (data errors)
#   - Inconsistent column names across tickers
#
# Economic intuition:
#   A single NaN in a price series corrupts ALL downstream calculations:
#   returns, rolling vol, cumulative P&L. Cleaning is not optional —
#   it is the difference between a meaningful backtest and garbage output.
# =============================================================================

import pandas as pd
import numpy as np


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove duplicate index entries, keeping the last occurrence.

    Duplicates can appear when data providers merge datasets from
    different sources (e.g. pre/post market data).
    """
    return df[~df.index.duplicated(keep="last")]


def remove_invalid_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove rows where Close price is zero, negative, or NaN.

    A zero price is always a data error — no listed stock trades at 0.
    """
    col = "Close" if "Close" in df.columns else "close"
    return df[df[col].notna() & (df[col] > 0)]


def fill_missing_values(df: pd.DataFrame,
                        method: str = "ffill") -> pd.DataFrame:
    """
    Fill missing values in the DataFrame.

    Parameters
    ----------
    method : "ffill" (forward-fill) or "drop"

    Economic note:
        Forward-fill is standard practice for price data — if a price
        is missing on a given day, the last known price is used.
        This is equivalent to assuming the market didn't move (reasonable
        for rare missing days, e.g. early close).
    """
    if method == "ffill":
        return df.ffill().bfill()
    elif method == "drop":
        return df.dropna()
    else:
        raise ValueError(f"Unknown fill method '{method}'. Use 'ffill' or 'drop'.")


def standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure consistent column names across all tickers.

    yfinance sometimes returns different column capitalisation or
    extra columns depending on the ticker type (stock vs ETF vs crypto).
    This function keeps only [Open, High, Low, Close, Volume] and
    renames them to lowercase for consistency.
    """
    ohlcv = ["Open", "High", "Low", "Close", "Volume"]
    cols_present = [c for c in ohlcv if c in df.columns]
    df = df[cols_present].copy()
    df.columns = [c.lower() for c in df.columns]
    return df


def clean(df: pd.DataFrame, fill_method: str = "ffill") -> pd.DataFrame:
    """
    Full cleaning pipeline: apply all steps in order.

    Steps: duplicates → invalid prices → missing values → column names

    Parameters
    ----------
    df          : raw DataFrame from fetcher/download.py
    fill_method : passed to fill_missing_values()

    Returns
    -------
    Clean pd.DataFrame ready for feature computation.
    """
    df = remove_duplicates(df)
    df = remove_invalid_prices(df)
    df = fill_missing_values(df, method=fill_method)
    df = standardise_columns(df)
    return df
