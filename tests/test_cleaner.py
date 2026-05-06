# =============================================================================
# tests/test_cleaner.py — Unit tests for cleaner/pipeline.py
# =============================================================================
# Run with: pytest tests/test_cleaner.py -v
#
# These tests are algebraic (exact) — we build controlled DataFrames
# and verify the cleaning functions produce exactly the right output.
# =============================================================================

import pytest
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cleaner.pipeline import (
    remove_duplicates, remove_invalid_prices,
    fill_missing_values, standardise_columns, clean
)


def make_df(close_values, dates=None):
    """Helper: build a minimal DataFrame with a Close column."""
    if dates is None:
        dates = pd.date_range("2023-01-01", periods=len(close_values), freq="B")
    return pd.DataFrame({
        "Open": close_values, "High": close_values,
        "Low": close_values,  "Close": close_values,
        "Volume": [1000] * len(close_values)
    }, index=dates)


class TestRemoveDuplicates:

    def test_removes_duplicate_dates(self):
        """Duplicate index entries are removed, keeping the last."""
        dates = pd.to_datetime(["2023-01-02", "2023-01-02", "2023-01-03"])
        df = make_df([100, 101, 102], dates)
        result = remove_duplicates(df)
        assert len(result) == 2
        assert result.loc["2023-01-02", "Close"] == 101

    def test_no_duplicates_unchanged(self):
        """DataFrame without duplicates is returned unchanged."""
        df = make_df([100, 101, 102])
        result = remove_duplicates(df)
        assert len(result) == 3


class TestRemoveInvalidPrices:

    def test_removes_zero_price(self):
        """Rows with Close == 0 are removed."""
        df = make_df([100, 0, 102])
        result = remove_invalid_prices(df)
        assert len(result) == 2
        assert 0 not in result["Close"].values

    def test_removes_negative_price(self):
        """Rows with Close < 0 are removed."""
        df = make_df([100, -5, 102])
        result = remove_invalid_prices(df)
        assert len(result) == 2

    def test_removes_nan_price(self):
        """Rows with Close == NaN are removed."""
        df = make_df([100, np.nan, 102])
        result = remove_invalid_prices(df)
        assert len(result) == 2


class TestFillMissingValues:

    def test_ffill_fills_nan(self):
        """Forward-fill replaces NaN with the previous value."""
        df = make_df([100, np.nan, 102])
        result = fill_missing_values(df, method="ffill")
        assert result["Close"].iloc[1] == 100

    def test_drop_removes_nan_rows(self):
        """Drop method removes rows with any NaN."""
        df = make_df([100, np.nan, 102])
        result = fill_missing_values(df, method="drop")
        assert len(result) == 2

    def test_invalid_method_raises(self):
        """Unknown fill method raises ValueError."""
        df = make_df([100, 101])
        with pytest.raises(ValueError):
            fill_missing_values(df, method="interpolate")


class TestStandardiseColumns:

    def test_renames_to_lowercase(self):
        """All columns are renamed to lowercase."""
        df = make_df([100, 101])
        result = standardise_columns(df)
        assert list(result.columns) == ["open", "high", "low", "close", "volume"]

    def test_drops_extra_columns(self):
        """Extra columns not in OHLCV are dropped."""
        df = make_df([100, 101])
        df["Dividends"] = 0
        result = standardise_columns(df)
        assert "dividends" not in result.columns
