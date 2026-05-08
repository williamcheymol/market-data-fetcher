# =============================================================================
# features/implied_vol.py — Implied volatility extraction via BS inversion
# =============================================================================
#
# What is implied volatility?
#   The Black-Scholes formula gives a price V = BS(S, K, r, T, σ).
#   In practice, we observe V (the market price) and want to find σ such that
#   BS(S, K, r, T, σ) = V_market.
#   This σ is the "implied volatility" — the market's consensus expectation of
#   future volatility embedded in the option price.
#
# Method: Brent's method (scipy.optimize.brentq)
#   BS(σ) is monotonically increasing in σ, so there is at most one solution.
#   Brent's method is a robust root-finding algorithm that combines bisection,
#   secant, and inverse quadratic interpolation — it always converges.
#
# Limitations:
#   - Deep OTM options have very low vega → BS is nearly flat in σ → IV is
#     numerically unstable or undefined.
#   - Options with bid = 0 or mid ≤ intrinsic are excluded upstream.
#   - We return NaN when no solution exists in [IV_LOW, IV_HIGH].
# =============================================================================

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm
from config import IV_LOW, IV_HIGH


# =============================================================================
#  Black-Scholes analytical formulas (replicated here to keep the module
#  self-contained — avoids importing from the C++ BSFormula project)
# =============================================================================

def _bs_price(S: float, K: float, r: float, T: float,
              sigma: float, option_type: str) -> float:
    """
    Closed-form Black-Scholes price for a European option.

    Parameters
    ----------
    S, K      : spot and strike
    r         : risk-free rate (annualised, decimal)
    T         : time to maturity in years
    sigma     : volatility (annualised, decimal)
    option_type: "call" or "put"
    """
    if T <= 0.0:
        return max(S - K, 0.0) if option_type == "call" else max(K - S, 0.0)
    if sigma <= 0.0:
        return 0.0

    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def implied_vol(market_price: float, S: float, K: float,
                r: float, T: float, option_type: str,
                vol_lo: float = IV_LOW,
                vol_hi: float = IV_HIGH) -> float:
    """
    Extract implied volatility from a market option price via Brent's method.

    Solves:  BS(S, K, r, T, σ) = market_price  for σ ∈ [vol_lo, vol_hi].

    Parameters
    ----------
    market_price : observed mid price of the option
    S            : current spot price
    K            : strike
    r            : risk-free rate (decimal)
    T            : time to maturity in years
    option_type  : "call" or "put"
    vol_lo, vol_hi : search bounds for σ

    Returns
    -------
    float : implied volatility in decimal (e.g. 0.25 = 25%), or NaN if
            no solution is found (deep OTM / illiquid contract).
    """
    if T <= 0.0 or market_price <= 0.0 or S <= 0.0 or K <= 0.0:
        return np.nan

    # Price must exceed the European lower bound to have a valid IV.
    # Note: for European puts, the lower bound is K*e^{-rT} - S, which can be
    # LESS than the American intrinsic (K - S) when r > 0.
    # Using the American intrinsic here would incorrectly reject valid prices.
    disc = np.exp(-r * T)
    if option_type == "call":
        lower_bound = max(S - K * disc, 0.0)
    else:
        lower_bound = max(K * disc - S, 0.0)
    if market_price <= lower_bound:
        return np.nan

    objective = lambda sigma: _bs_price(S, K, r, T, sigma, option_type) - market_price

    # Brent requires the function to change sign over the interval
    try:
        f_lo = objective(vol_lo)
        f_hi = objective(vol_hi)
    except Exception:
        return np.nan

    if f_lo * f_hi > 0:
        # No sign change — no solution in [vol_lo, vol_hi]
        return np.nan

    try:
        return brentq(objective, vol_lo, vol_hi, xtol=1e-6, maxiter=200)
    except (ValueError, RuntimeError):
        return np.nan


def compute_implied_vols(chain: pd.DataFrame,
                         S: float,
                         r: float) -> pd.DataFrame:
    """
    Compute implied volatility for every contract in an option chain.

    Adds columns:
      - T            : time to maturity in years (from today)
      - implied_vol  : extracted IV (NaN for illiquid / unsolvable contracts)

    Rows where IV extraction fails are dropped.

    Parameters
    ----------
    chain : DataFrame from fetcher/options.py
            Required columns: expiry, strike, option_type, mid
    S     : current spot price of the underlying
    r     : risk-free rate (decimal)

    Returns
    -------
    pd.DataFrame — chain with T and implied_vol columns added,
                   NaN rows removed.
    """
    chain = chain.copy()
    today = pd.Timestamp.today().normalize()

    # Time to maturity in years for each expiry
    chain["T"] = chain["expiry"].apply(
        lambda e: max((pd.Timestamp(e) - today).days / 365.0, 1e-6)
    )

    # Vectorised IV extraction — one call per row
    chain["implied_vol"] = chain.apply(
        lambda row: implied_vol(
            market_price=row["mid"],
            S=S,
            K=row["strike"],
            r=r,
            T=row["T"],
            option_type=row["option_type"],
        ),
        axis=1,
    )

    n_total  = len(chain)
    chain    = chain.dropna(subset=["implied_vol"]).reset_index(drop=True)
    n_solved = len(chain)
    pct      = (100 * n_solved / n_total) if n_total > 0 else 0
    print(f"  IV solved: {n_solved}/{n_total} contracts ({pct:.0f}%)")

    # Final column order
    cols = ["option_type", "strike", "expiry", "mid",
            "T", "implied_vol", "yf_implied_vol", "volume"]
    chain = chain[[c for c in cols if c in chain.columns]]

    return chain
