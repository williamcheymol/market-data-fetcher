# =============================================================================
# fetcher/options.py — Fetch option chains and risk-free rate via yfinance
# =============================================================================
#
# What is an option chain?
#   For a given underlying (e.g. AAPL), the option chain lists all available
#   contracts: every combination of (strike K, expiry T, type call/put) with
#   their bid, ask, volume, and open interest.
#   This is the raw market data from which implied volatility is extracted.
#
# Risk-free rate:
#   We use the 3-month US Treasury Bill yield (^IRX) as a proxy for r.
#   This is standard practice in equity options pricing.
#
# SSL note:
#   yfinance 1.3+ uses curl_cffi internally. On systems where the local CA
#   certificate store cannot verify Yahoo Finance's certificate chain (e.g.
#   corporate proxies with custom root CAs), we create the session manually
#   with verify=False. This is safe for a read-only market-data client.
# =============================================================================

import yfinance as yf
import pandas as pd
from curl_cffi import requests as cr
from config import MAX_MATURITIES

# Shared session — created once at import, reused by all fetchers.
# verify=False bypasses SSL certificate verification (needed on some networks).
_session = cr.Session(verify=False, impersonate="chrome")


def fetch_spot_price(ticker: str) -> float:
    """
    Fetch the latest closing price for a ticker.

    Parameters
    ----------
    ticker : str — e.g. "AAPL"

    Returns
    -------
    float : last closing price
    """
    t = yf.Ticker(ticker, session=_session)
    hist = t.history(period="5d")
    if hist.empty:
        raise ValueError(f"Could not fetch spot price for '{ticker}'.")
    return float(hist["Close"].iloc[-1])


def fetch_risk_free_rate() -> float:
    """
    Fetch the current 3-month US T-Bill yield from Yahoo Finance (^IRX).

    ^IRX is quoted in percent (e.g. 5.23 means 5.23%).
    We convert to decimal (0.0523).

    Returns
    -------
    float : annualised risk-free rate as a decimal
    """
    irx = yf.download("^IRX", period="5d", progress=False,
                      auto_adjust=True, session=_session)

    if isinstance(irx.columns, pd.MultiIndex):
        irx.columns = irx.columns.get_level_values(0)

    if irx.empty:
        raise ValueError("Could not fetch risk-free rate (^IRX).")

    rate_pct = float(irx["Close"].dropna().iloc[-1])
    return rate_pct / 100.0


def fetch_option_chain(ticker: str,
                       max_maturities: int = MAX_MATURITIES) -> pd.DataFrame:
    """
    Fetch the option chain for a ticker and return a clean DataFrame.

    Filters applied:
      - Only the nearest `max_maturities` expiry dates
      - Mid price > 0  (uses bid/ask when available, lastPrice after hours)

    Parameters
    ----------
    ticker         : str — underlying ticker, e.g. "AAPL"
    max_maturities : int — number of expiry dates to include

    Returns
    -------
    pd.DataFrame with columns:
        expiry, strike, option_type, bid, ask, mid,
        volume, open_interest, yf_implied_vol
    """
    t = yf.Ticker(ticker, session=_session)
    expiries = t.options  # sorted nearest → furthest

    if not expiries:
        raise ValueError(f"No option chain available for '{ticker}'.")

    expiries = expiries[:max_maturities]

    frames = []
    for exp in expiries:
        try:
            chain = t.option_chain(exp)
        except Exception as e:
            print(f"  Warning: could not fetch chain for expiry {exp} — {e}")
            continue

        for opt_type, df in [("call", chain.calls), ("put", chain.puts)]:
            keep = ["strike", "lastPrice", "bid", "ask",
                    "volume", "impliedVolatility"]
            df = df[[c for c in keep if c in df.columns]].copy()
            df.rename(columns={"impliedVolatility": "yf_implied_vol"}, inplace=True)

            df["expiry"]      = exp
            df["option_type"] = opt_type

            # Mid price: use bid/ask spread when available (market hours),
            # fall back to last traded price (after hours / weekend).
            bid  = df.get("bid",       pd.Series(dtype=float))
            ask  = df.get("ask",       pd.Series(dtype=float))
            last = df.get("lastPrice", pd.Series(dtype=float))
            mid  = (bid + ask) / 2.0
            df["mid"] = mid.where(bid > 0, last)

            frames.append(df)

    if not frames:
        raise ValueError(f"Empty option chain for '{ticker}'.")

    chain_df = pd.concat(frames, ignore_index=True)

    # Only filter: mid > 0 (covers live bid/ask and lastPrice fallback).
    chain_df = chain_df[chain_df["mid"] > 0]

    # --- Cleanup ---
    # volume: fill missing values with 0 and cast to int
    chain_df["volume"] = chain_df["volume"].fillna(0).astype(int)

    # yf_implied_vol: very small values (e.g. 1e-5) are effectively 0
    if "yf_implied_vol" in chain_df.columns:
        chain_df["yf_implied_vol"] = chain_df["yf_implied_vol"].where(
            chain_df["yf_implied_vol"] > 1e-4, 0.0
        )

    # Drop columns that are uninformative after hours
    chain_df = chain_df.drop(columns=["lastPrice", "bid", "ask"], errors="ignore")

    # Sort: puts first, then calls; within each group by expiry then strike
    chain_df = chain_df.sort_values(
        ["option_type", "strike", "expiry"],
        ascending=[False, True, True]   # "put" > "call" alphabetically
    ).reset_index(drop=True)
    print(f"  [OK] {ticker} option chain — {len(chain_df)} contracts "
          f"across {len(expiries)} expiries")
    return chain_df
