# =============================================================================
# main.py — Full pipeline entry point
# =============================================================================
# Two independent pipelines:
#
#   run_price_pipeline()   — historical OHLCV + realised vol (existing)
#   run_options_pipeline() — option chain + implied vol (new)
#   run_all()              — both
# =============================================================================

from config import DEFAULT_TICKERS, START_DATE, END_DATE, OPTION_TICKER, EXPORT_DIR
from fetcher.download import download_multiple
from fetcher.options import fetch_option_chain, fetch_spot_price, fetch_risk_free_rate
from cleaner.pipeline import clean
from features.compute import compute_all
from features.implied_vol import compute_implied_vols
from exporter.export import export_multiple, to_csv
from visualizer.plots import (plot_price_and_vol, plot_return_dist,
                               plot_iv_smile, plot_iv_vs_realized)

import os


def run_price_pipeline(tickers=DEFAULT_TICKERS,
                       start=START_DATE,
                       end=END_DATE) -> dict:
    """
    Download and process historical OHLCV data for a list of tickers.
    Computes log-returns, realised volatility, cumulative returns.

    Returns
    -------
    dict {ticker: enriched DataFrame}
    """
    print(f"\n=== Price pipeline — {tickers} ===")
    raw_data = download_multiple(tickers, start, end)

    results = {}
    for ticker, df in raw_data.items():
        print(f"Processing {ticker}...")
        df_clean    = clean(df)
        df_enriched = compute_all(df_clean)
        results[ticker] = df_enriched

    print("Exporting to CSV...")
    export_multiple(results)

    print("Generating plots...")
    for ticker in results:
        plot_price_and_vol(results, ticker)
        plot_return_dist(results, ticker)

    return results


def run_options_pipeline(ticker: str = OPTION_TICKER) -> dict:
    """
    Fetch option chain and compute implied volatilities for a single ticker.

    Steps:
      1. Fetch spot price S and risk-free rate r
      2. Fetch option chain (calls + puts, nearest maturities)
      3. Extract implied vol for each contract via BS inversion
      4. Export to CSV

    Returns
    -------
    dict with keys:
        "chain"  — full DataFrame with IV column
        "S"      — spot price
        "r"      — risk-free rate
    """
    print(f"\n=== Options pipeline — {ticker} ===")

    print("Fetching spot price...")
    S = fetch_spot_price(ticker)
    print(f"  S = {S:.2f}")

    print("Fetching risk-free rate (^IRX)...")
    r = fetch_risk_free_rate()
    print(f"  r = {r:.4f}  ({r*100:.2f}%)")

    print("Fetching option chain...")
    chain = fetch_option_chain(ticker)

    print("Computing implied volatilities...")
    chain_iv = compute_implied_vols(chain, S=S, r=r)

    # Export
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, f"{ticker}_options.csv")
    chain_iv.to_csv(path, index=False)
    print(f"  Saved: {path}")

    print("Generating plots...")
    plot_iv_smile(chain_iv, S=S, ticker=ticker)

    return {"chain": chain_iv, "S": S, "r": r}


def run_all(ticker: str = OPTION_TICKER):
    """
    Run both pipelines and generate all plots, including the cross-pipeline
    IV vs realised vol comparison.
    """
    price_results = run_price_pipeline(tickers=[ticker])
    options_results = run_options_pipeline(ticker=ticker)

    if ticker in price_results:
        print("Generating IV vs Realised Vol plot...")
        plot_iv_vs_realized(
            chain=options_results["chain"],
            results=price_results,
            ticker=ticker,
            S=options_results["S"],
        )


if __name__ == "__main__":
    run_all()
