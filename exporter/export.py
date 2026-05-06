# =============================================================================
# exporter/export.py — Export processed data to CSV or return as DataFrame
# =============================================================================
# The final step of the pipeline: persist the enriched data for downstream use.
#
# Design principle:
#   Every downstream project (delta hedging, backtesting, smile analysis)
#   should be able to load data with a single pd.read_csv() call.
#   This module ensures the output format is always consistent.
# =============================================================================

import pandas as pd
import os
from config import EXPORT_DIR


def to_csv(df: pd.DataFrame, ticker: str, output_dir: str = EXPORT_DIR) -> str:
    """
    Export a DataFrame to CSV.

    File is saved as: {output_dir}/{ticker}_data.csv

    Parameters
    ----------
    df         : enriched DataFrame (output of features/compute.py)
    ticker     : ticker string, used in the filename
    output_dir : directory where the file is saved (created if not exists)

    Returns
    -------
    str : full path to the saved file
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{ticker}_data.csv")
    df.to_csv(path)
    print(f"  Saved: {path}")
    return path


def to_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Return the processed DataFrame as-is.

    Used when the caller wants to work directly in memory
    without writing to disk (e.g. feeding directly into a pricer).
    """
    return df.reset_index()


def export_multiple(data: dict, output_dir: str = EXPORT_DIR) -> list:
    """
    Export a dict of DataFrames (one per ticker) to CSV files.

    Parameters
    ----------
    data       : dict {ticker: DataFrame} — output of fetcher/download.py
    output_dir : target directory

    Returns
    -------
    list of file paths created
    """
    paths = []
    for ticker, df in data.items():
        path = to_csv(df, ticker, output_dir)
        paths.append(path)
    return paths
