# =============================================================================
# tests/test_fetcher.py — Unit tests for fetcher/download.py
# =============================================================================
# Run with: pytest tests/test_fetcher.py -v
# =============================================================================

import pytest
import pandas as pd
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fetcher.download import download_single, download_multiple


class TestDownloadSingle:

    def test_returns_dataframe(self):
        """download_single returns a non-empty DataFrame."""
        df = download_single("AAPL", "2023-01-01", "2023-06-01")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_columns_present(self):
        """DataFrame contains expected OHLCV columns."""
        df = download_single("AAPL", "2023-01-01", "2023-06-01")
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            assert col in df.columns

    def test_index_is_datetime(self):
        """Index is a DatetimeIndex."""
        df = download_single("AAPL", "2023-01-01", "2023-06-01")
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_no_weekends(self):
        """No Saturday or Sunday in the index (markets are closed)."""
        df = download_single("AAPL", "2023-01-01", "2023-06-01")
        assert not any(df.index.dayofweek >= 5)

    def test_invalid_ticker_raises(self):
        """Invalid ticker raises ValueError."""
        with pytest.raises(ValueError):
            download_single("INVALID_TICKER_XYZ", "2023-01-01", "2023-06-01")


class TestDownloadMultiple:

    def test_returns_dict(self):
        """download_multiple returns a dict."""
        result = download_multiple(["AAPL", "MSFT"], "2023-01-01", "2023-03-01")
        assert isinstance(result, dict)

    def test_all_tickers_present(self):
        """All valid tickers are in the result."""
        result = download_multiple(["AAPL", "MSFT"], "2023-01-01", "2023-03-01")
        assert "AAPL" in result
        assert "MSFT" in result

    def test_invalid_ticker_skipped(self):
        """Invalid tickers are skipped, valid ones still returned."""
        result = download_multiple(["AAPL", "INVALID_XYZ"], "2023-01-01", "2023-03-01")
        assert "AAPL" in result
        assert "INVALID_XYZ" not in result
