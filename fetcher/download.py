# =============================================================================
# fetcher/download.py — Download raw market data via yfinance
# =============================================================================
# This module is the entry point of the pipeline.
# It pulls raw OHLCV data (Open, High, Low, Close, Volume) from Yahoo Finance
# and returns a clean, standardised DataFrame.
#
# Economic intuition:
#   The "Close" price is the last traded price of the day. In quant finance,
#   we almost always use the "Adjusted Close" (Adj Close) which accounts for
#   dividends and stock splits — without this adjustment, a stock split would
#   appear as a 50% price drop, which would completely distort returns.
# =============================================================================

import yfinance as yf
import pandas as pd
from typing import Union
from curl_cffi import requests as cr

# Shared session — same SSL workaround as fetcher/options.py
_session = cr.Session(verify=False, impersonate="chrome")


def download_single(ticker: str,
                    start: str,
                    end: str,
                    auto_adjust: bool = True) -> pd.DataFrame:
    """
    Download OHLCV data for a single ticker.

    Parameters
    ----------
    ticker       : str   — e.g. "AAPL", "SPY", "BTC-USD"
    start        : str   — start date "YYYY-MM-DD"
    end          : str   — end date   "YYYY-MM-DD"
    auto_adjust  : bool  — if True, prices are adjusted for dividends & splits

    Returns
    -------
    pd.DataFrame with columns [Open, High, Low, Close, Volume]
    Index: DatetimeIndex (trading days only, no weekends/holidays)

    Raises
    ------
    ValueError if the ticker is invalid or no data is returned.
    """
    df = yf.download(ticker, start=start, end=end,
                     auto_adjust=auto_adjust, progress=False,
                     session=_session)

    # yfinance returns an empty DataFrame for invalid tickers
    if df.empty:
        raise ValueError(f"No data returned for ticker '{ticker}'. "
                         f"Check the ticker symbol and date range.")

    # Flatten MultiIndex columns that yfinance sometimes produces
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Drop extra columns yfinance may include
    cols_to_drop = [c for c in ["Dividends", "Stock Splits", "Capital Gains"]
                    if c in df.columns]
    df = df.drop(columns=cols_to_drop)

    return df


def download_multiple(tickers: list,
                      start: str,
                      end: str,
                      auto_adjust: bool = True) -> dict:
    """
    Download OHLCV data for multiple tickers.

    Returns a dictionary mapping each ticker to its DataFrame.
    Tickers that fail are skipped with a warning (not a crash).

    Parameters
    ----------
    tickers      : list of ticker strings
    start        : str — start date "YYYY-MM-DD"
    end          : str — end date   "YYYY-MM-DD"
    auto_adjust  : bool

    Returns
    -------
    dict[str, pd.DataFrame] — {ticker: DataFrame}
    """
    results = {}
    for ticker in tickers:
        try:
            results[ticker] = download_single(ticker, start, end, auto_adjust)
            print(f"  [OK] {ticker} — {len(results[ticker])} rows")
        except Exception as e:
            print(f"  [!!] {ticker} — skipped ({e})")
    return results
