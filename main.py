# =============================================================================
# main.py — Full pipeline entry point
# =============================================================================
# Runs the complete Market Data Fetcher pipeline:
#   1. Download raw data for all configured tickers
#   2. Clean each DataFrame
#   3. Compute features (log-returns, realised vol, cumulative returns)
#   4. Export to CSV
# =============================================================================

from config import DEFAULT_TICKERS, START_DATE, END_DATE
from fetcher.download import download_multiple
from cleaner.pipeline import clean
from features.compute import compute_all
from exporter.export import export_multiple


def run_pipeline(tickers=DEFAULT_TICKERS,
                 start=START_DATE,
                 end=END_DATE) -> dict:
    """
    Run the full data pipeline for a list of tickers.

    Returns
    -------
    dict {ticker: enriched DataFrame}
    """
    print(f"Downloading data for: {tickers}")
    raw_data = download_multiple(tickers, start, end)

    results = {}
    for ticker, df in raw_data.items():
        print(f"Processing {ticker}...")
        df_clean    = clean(df)
        df_enriched = compute_all(df_clean)
        results[ticker] = df_enriched

    print("Exporting to CSV...")
    export_multiple(results)

    print("Done.")
    return results


if __name__ == "__main__":
    run_pipeline()
