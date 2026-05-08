# =============================================================================
# visualizer/plots.py — Visualisation tools for market data and options
# =============================================================================
#
# Four plots:
#   1. plot_price_and_vol     — closing price + realised volatility over time
#   2. plot_return_dist       — log-return histogram vs fitted Gaussian
#   3. plot_iv_smile          — implied vol smile / skew across maturities
#   4. plot_iv_vs_realized    — ATM IV vs realised vol (variance risk premium)
#
# Style: dark Bloomberg-inspired theme (black background, cyan/orange palette,
#        monospace font, subtle grey grid).
#
# All functions save a PNG to results/plots/ and return the file path.
# =============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.stats import norm

PLOT_DIR = "results/plots"

# =============================================================================
#  Bloomberg-style theme
# =============================================================================

BG        = "#111111"   # figure / axes background
FG        = "#e0e0e0"   # text, ticks, labels
GRID      = "#2a2a2a"   # grid lines
CYAN      = "#00bfff"   # primary curve colour
ORANGE    = "#ffa500"   # secondary colour
YELLOW    = "#ffd700"   # tertiary
RED       = "#ff4d4d"   # accent / warning
GREEN     = "#00e676"   # accent / positive
PALETTE   = [CYAN, ORANGE, YELLOW, RED, GREEN, "#ff69b4"]

plt.rcParams.update({
    "figure.facecolor":     BG,
    "axes.facecolor":       BG,
    "axes.edgecolor":       "#333333",
    "axes.labelcolor":      FG,
    "axes.titlecolor":      FG,
    "text.color":           FG,
    "xtick.color":          FG,
    "ytick.color":          FG,
    "grid.color":           GRID,
    "grid.linewidth":       0.6,
    "legend.facecolor":     "#1a1a1a",
    "legend.edgecolor":     "#333333",
    "legend.labelcolor":    FG,
    "font.family":          "monospace",
    "axes.prop_cycle":      plt.cycler(color=PALETTE),
})


def _style_ax(ax) -> None:
    """Apply common axis styling: grid, no top/right spines."""
    ax.grid(True, which="major", linestyle="--", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#333333")
    ax.spines["bottom"].set_color("#333333")


def _save(fig: plt.Figure, filename: str) -> str:
    """Save figure to results/plots/ and close it."""
    os.makedirs(PLOT_DIR, exist_ok=True)
    path = os.path.join(PLOT_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Saved: {path}")
    return path


# =============================================================================
#  1. Price + Realised Volatility
# =============================================================================

def plot_price_and_vol(results: dict, ticker: str) -> str:
    """
    Plot closing price and annualised realised volatility on a dual Y-axis.

    Visually shows that volatility spikes when price drops — the well-known
    leverage effect (negative correlation between returns and vol).

    Parameters
    ----------
    results : dict {ticker: DataFrame} — output of run_price_pipeline()
    ticker  : str — which ticker to plot

    Returns
    -------
    str : path to saved PNG
    """
    df = results[ticker].dropna(subset=["realised_vol"])

    fig, ax1 = plt.subplots(figsize=(13, 5))

    # --- Price (left axis) ---
    ax1.plot(df.index, df["close"], color=CYAN, linewidth=1.2, label="Close")
    ax1.set_ylabel("Price (USD)", color=CYAN, fontsize=10)
    ax1.tick_params(axis="y", labelcolor=CYAN)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax1.xaxis.set_major_locator(mdates.YearLocator())

    # --- Realised vol (right axis) ---
    ax2 = ax1.twinx()
    ax2.fill_between(df.index, df["realised_vol"] * 100,
                     alpha=0.20, color=ORANGE)
    ax2.plot(df.index, df["realised_vol"] * 100,
             color=ORANGE, linewidth=1.0, label="Realised Vol (21d)")
    ax2.set_ylabel("Realised Volatility (%)", color=ORANGE, fontsize=10)
    ax2.tick_params(axis="y", labelcolor=ORANGE)
    ax2.spines["top"].set_visible(False)

    # --- Styling ---
    _style_ax(ax1)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2,
               loc="upper left", fontsize=9)

    ax1.set_title(f"{ticker}  |  Price and Realised Volatility (21-day)",
                  fontsize=12, fontweight="bold", pad=10)
    fig.tight_layout()

    return _save(fig, f"{ticker}_price_vol.png")


# =============================================================================
#  2. Log-return distribution vs Gaussian
# =============================================================================

def plot_return_dist(results: dict, ticker: str) -> str:
    """
    Histogram of daily log-returns overlaid with a fitted Gaussian.

    The gap between histogram and Gaussian visually demonstrates the
    fat tails and negative skew that Black-Scholes ignores.

    Parameters
    ----------
    results : dict {ticker: DataFrame} — output of run_price_pipeline()
    ticker  : str — which ticker to plot

    Returns
    -------
    str : path to saved PNG
    """
    returns = results[ticker]["log_return"].dropna()
    mu, sigma = returns.mean(), returns.std()

    fig, ax = plt.subplots(figsize=(10, 5))
    _style_ax(ax)

    # --- Histogram ---
    ax.hist(returns, bins=50, density=True,
            color=CYAN, alpha=0.65, label="Log-returns")

    # --- Fitted Gaussian ---
    x = np.linspace(returns.min(), returns.max(), 400)
    ax.plot(x, norm.pdf(x, mu, sigma),
            color=RED, linewidth=2,
            label=f"Fitted Gaussian  mu={mu:.4f}  sigma={sigma:.4f}")

    ax.set_title(f"{ticker}  |  Daily Log-Return Distribution",
                 fontsize=12, fontweight="bold", pad=10)
    ax.set_xlabel("Log-return", fontsize=10)
    ax.set_ylabel("Density", fontsize=10)
    ax.legend(fontsize=9)
    fig.tight_layout()

    return _save(fig, f"{ticker}_return_dist.png")


# =============================================================================
#  3. Implied Volatility Smile
# =============================================================================

def plot_iv_smile(chain: pd.DataFrame, S: float, ticker: str) -> str:
    """
    Plot the full implied volatility smile on a single chart.

    Uses OTM options only (most liquid and informative):
      - OTM puts  for moneyness < 1  (left side)
      - OTM calls for moneyness > 1  (right side)

    One curve per expiry — shows the vol skew structure across maturities.

    Parameters
    ----------
    chain  : DataFrame — output of run_options_pipeline()["chain"]
    S      : float     — spot price
    ticker : str       — used in title and filename

    Returns
    -------
    str : path to saved PNG
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    _style_ax(ax)

    expiries = sorted(chain["expiry"].unique())

    for exp, color in zip(expiries, PALETTE):
        # OTM puts: strike < S
        puts = chain[
            (chain["option_type"] == "put") &
            (chain["expiry"] == exp) &
            (chain["strike"] < S)
        ].copy()

        # OTM calls: strike > S
        calls = chain[
            (chain["option_type"] == "call") &
            (chain["expiry"] == exp) &
            (chain["strike"] > S)
        ].copy()

        smile = pd.concat([puts, calls])
        smile["moneyness"] = smile["strike"] / S

        # Keep strikes within 70%-130% of spot and cap IV at 100%
        smile = smile[
            (smile["moneyness"] >= 0.7) &
            (smile["moneyness"] <= 1.3) &
            (smile["implied_vol"] <= 1.0)
        ].sort_values("moneyness")

        if len(smile) < 3:
            continue

        ax.plot(smile["moneyness"], smile["implied_vol"] * 100,
                color=color, marker="o", markersize=3,
                linewidth=1.5, label=exp)

    # ATM line
    ax.axvline(x=1.0, color=FG, linestyle="--",
               linewidth=0.8, alpha=0.5, label="ATM (K=S)")

    # Shade OTM regions
    ax.axvspan(0.7, 1.0, alpha=0.05, color=RED,   label="OTM puts")
    ax.axvspan(1.0, 1.3, alpha=0.05, color=GREEN, label="OTM calls")

    ax.set_xlabel("Moneyness (K / S)", fontsize=10)
    ax.set_ylabel("Implied Volatility (%)", fontsize=10)
    ax.set_title(f"{ticker}  |  Implied Volatility Smile  (S = {S:.2f})",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=9, title="Expiry",
              title_fontsize=8, framealpha=0.6)
    fig.tight_layout()

    return _save(fig, f"{ticker}_iv_smile.png")


# =============================================================================
#  4. IV vs Realised Volatility
# =============================================================================

def plot_iv_vs_realized(chain: pd.DataFrame,
                        results: dict,
                        ticker: str,
                        S: float) -> str:
    """
    Compare ATM implied volatility against historical realised volatility.

    The spread IV - sigma_realized is the variance risk premium: the extra
    compensation option sellers demand for bearing volatility risk.
    In practice IV > sigma_realized on average.

    Parameters
    ----------
    chain   : DataFrame — output of run_options_pipeline()["chain"]
    results : dict      — output of run_price_pipeline()
    ticker  : str
    S       : float     — spot price (used to select near-ATM strikes)

    Returns
    -------
    str : path to saved PNG
    """
    # ATM IV: median IV of strikes within 2% of spot, calls only
    atm = chain[
        (chain["option_type"] == "call") &
        (chain["strike"].between(S * 0.98, S * 1.02))
    ]
    if atm.empty:
        atm = chain[chain["option_type"] == "call"]

    iv_by_expiry = (atm.groupby("expiry")["implied_vol"]
                       .median()
                       .sort_index())

    # Most recent realised vol from historical data
    realized = results[ticker]["realised_vol"].dropna().iloc[-1]

    fig, ax = plt.subplots(figsize=(9, 5))
    _style_ax(ax)

    x = np.arange(len(iv_by_expiry))
    bars = ax.bar(x, iv_by_expiry.values * 100,
                  color=CYAN, alpha=0.8, label="ATM Implied Vol",
                  width=0.5)

    # Realised vol reference line
    ax.axhline(y=realized * 100, color=ORANGE, linewidth=2,
               linestyle="--",
               label=f"Realised Vol  ({realized*100:.1f}%)")

    # Value labels on bars
    for bar, val in zip(bars, iv_by_expiry.values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.3,
                f"{val*100:.1f}%",
                ha="center", va="bottom", fontsize=9, color=FG)

    ax.set_xticks(x)
    ax.set_xticklabels(iv_by_expiry.index, rotation=15, fontsize=9)
    ax.set_ylabel("Volatility (%)", fontsize=10)
    ax.set_title(f"{ticker}  |  ATM Implied Vol vs Realised Vol",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=9)
    fig.tight_layout()

    return _save(fig, f"{ticker}_iv_vs_realized.png")
