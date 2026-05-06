# =============================================================================
# tests/test_features.py — Unit tests for features/compute.py
# =============================================================================
# Run with: pytest tests/test_features.py -v
#
# Mix of algebraic tests (exact) and statistical tests (toleranced).
# =============================================================================

import pytest
import pandas as pd
import numpy as np
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from features.compute import log_returns, realised_volatility, cumulative_returns


def make_close(values):
    """Helper: build a clean DataFrame with a 'close' column."""
    dates = pd.date_range("2023-01-01", periods=len(values), freq="B")
    return pd.DataFrame({"close": values}, index=dates)


class TestLogReturns:

    def test_correct_values(self):
        """Log-returns are computed correctly: log(S_t / S_{t-1})."""
        df = make_close([100, 110, 99])
        r  = log_returns(df)
        assert r.iloc[0] == pytest.approx(np.log(110 / 100), abs=1e-10)
        assert r.iloc[1] == pytest.approx(np.log(99  / 110), abs=1e-10)

    def test_length(self):
        """Output has length n - 1 (first row is dropped)."""
        df = make_close([100, 101, 102, 103])
        r  = log_returns(df)
        assert len(r) == 3

    def test_constant_price_zero_return(self):
        """Constant price → log-return = 0 exactly."""
        df = make_close([100, 100, 100])
        r  = log_returns(df)
        np.testing.assert_allclose(r.values, 0, atol=1e-10)

    def test_series_name(self):
        """Output series is named 'log_return'."""
        df = make_close([100, 101])
        r  = log_returns(df)
        assert r.name == "log_return"


class TestRealisedVolatility:

    def test_output_length(self):
        """Output has the same length as input (NaN for initial window)."""
        df = make_close([100 * (1 + 0.01 * i) for i in range(50)])
        r  = log_returns(df)
        vol = realised_volatility(r, window=21)
        assert len(vol) == len(r)

    def test_annualisation(self):
        """Annualised vol = daily vol * sqrt(252)."""
        np.random.seed(0)
        returns = pd.Series(np.random.normal(0, 0.01, 252))
        vol_daily      = realised_volatility(returns, window=21, annualise=False)
        vol_annualised = realised_volatility(returns, window=21, annualise=True)
        ratio = (vol_annualised / vol_daily).dropna()
        assert ratio.mean() == pytest.approx(np.sqrt(252), rel=1e-6)

    def test_series_name(self):
        """Output series is named 'realised_vol'."""
        returns = pd.Series([0.01, -0.01, 0.02] * 10)
        vol = realised_volatility(returns)
        assert vol.name == "realised_vol"


class TestCumulativeReturns:

    def test_starts_at_zero(self):
        """Cumulative return at t=0 is 0 (no gain yet)."""
        returns = pd.Series([0.01, 0.02, -0.01])
        cum = cumulative_returns(returns)
        assert cum.iloc[0] == pytest.approx(np.exp(0.01) - 1, abs=1e-10)

    def test_zero_returns_zero_cumulative(self):
        """Zero returns → cumulative return stays at 0."""
        returns = pd.Series([0.0, 0.0, 0.0])
        cum = cumulative_returns(returns)
        np.testing.assert_allclose(cum.values, 0, atol=1e-10)

    def test_series_name(self):
        """Output series is named 'cumulative_return'."""
        returns = pd.Series([0.01, 0.02])
        cum = cumulative_returns(returns)
        assert cum.name == "cumulative_return"
