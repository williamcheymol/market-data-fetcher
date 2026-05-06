# =============================================================================
# features/compute.py — Compute financial features from clean price data
# =============================================================================
# This is where raw prices become useful for quant analysis.
#
# Economic intuition:
#   Prices alone are not directly useful for modelling — they are
#   non-stationary (they trend over time). Log-returns are stationary,
#   approximately normally distributed, and additive across time:
#
#       r_t = log(S_t / S_{t-1})
#
#   This is exactly the discrete version of the GBM increments you used
#   in the delta hedging project. Bridging the two projects together!
# =============================================================================

import pandas as pd
import numpy as np
from config import ROLLING_WINDOW, TRADING_DAYS_PER_YEAR


def log_returns(df: pd.DataFrame) -> pd.Series:
    """
    Compute daily log-returns from the close price.

        r_t = log(Close_t / Close_{t-1})

    Returns
    -------
    pd.Series of log-returns (first value is NaN, dropped automatically).

    Economic note:
        Log-returns are preferred over simple returns (S_t/S_{t-1} - 1)
        because they are additive: r(0→T) = Σ r(t→t+1).
        They also connect directly to GBM: under Black-Scholes,
        log-returns are normally distributed with mean (r - σ²/2)dt
        and std σ√dt.
    """
    col = "close" if "close" in df.columns else "Close"
    returns = np.log(df[col] / df[col].shift(1)).dropna()
    returns.name = "log_return"
    return returns


def realised_volatility(returns: pd.Series,
                        window: int = ROLLING_WINDOW,
                        annualise: bool = True) -> pd.Series:
    """
    Compute rolling realised volatility from log-returns.

    Realised vol = rolling std of log-returns * sqrt(252) (if annualised)

    Parameters
    ----------
    returns   : pd.Series of log-returns (from log_returns())
    window    : rolling window in trading days (default: 21 = 1 month)
    annualise : if True, multiply by sqrt(252) to get annualised vol

    Returns
    -------
    pd.Series of rolling realised volatility.

    Economic note:
        This is the "historical volatility" or "realised volatility" —
        what the stock actually did, as opposed to implied volatility
        (what the market expects it to do). The gap between the two
        is the foundation of the volatility smile analysis.
    """
    vol = returns.rolling(window).std()
    if annualise:
        vol = vol * np.sqrt(TRADING_DAYS_PER_YEAR)
    vol.name = "realised_vol"
    return vol


def cumulative_returns(returns: pd.Series) -> pd.Series:
    """
    Compute cumulative returns from log-returns.

        Cumulative return at t = exp(Σ r_i for i=0..t) - 1

    Returns a series starting at 0 (no gain/loss at t=0).

    Economic note:
        This shows the total percentage gain/loss from the start date.
        Useful for comparing performance across multiple tickers
        on the same chart — regardless of their absolute price levels.
    """
    cum = np.exp(returns.cumsum()) - 1
    cum.name = "cumulative_return"
    return cum


def compute_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all features and return an enriched DataFrame.

    Adds columns: log_return, realised_vol, cumulative_return

    Parameters
    ----------
    df : clean DataFrame with at least a "close" column

    Returns
    -------
    pd.DataFrame with original columns + computed features.
    """
    returns = log_returns(df)
    vol     = realised_volatility(returns)
    cum     = cumulative_returns(returns)

    df = df.copy()
    df["log_return"]       = returns
    df["realised_vol"]     = vol
    df["cumulative_return"] = cum

    return df.dropna()
