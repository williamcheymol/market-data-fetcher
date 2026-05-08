# =============================================================================
# tests/test_implied_vol.py — Unit tests for implied volatility extraction
# =============================================================================

import pytest
import numpy as np
import pandas as pd
from features.implied_vol import _bs_price, implied_vol, compute_implied_vols


# =============================================================================
#  _bs_price — analytical BS formula
# =============================================================================

class TestBSPrice:

    def test_call_atm(self):
        """ATM call with known parameters — compare against standard formula."""
        price = _bs_price(S=100, K=100, r=0.05, T=1.0, sigma=0.2, option_type="call")
        assert abs(price - 10.4506) < 0.01

    def test_put_atm(self):
        """ATM put via put-call parity: P = C - S + K*e^{-rT}."""
        call = _bs_price(S=100, K=100, r=0.05, T=1.0, sigma=0.2, option_type="call")
        put  = _bs_price(S=100, K=100, r=0.05, T=1.0, sigma=0.2, option_type="put")
        parity = call - 100 + 100 * np.exp(-0.05 * 1.0)
        assert abs(put - parity) < 1e-8

    def test_call_zero_time(self):
        """At expiry, call = max(S - K, 0)."""
        assert _bs_price(100, 90, 0.05, 0.0, 0.2, "call") == pytest.approx(10.0)
        assert _bs_price(100, 110, 0.05, 0.0, 0.2, "call") == pytest.approx(0.0)

    def test_put_zero_time(self):
        """At expiry, put = max(K - S, 0)."""
        assert _bs_price(100, 110, 0.05, 0.0, 0.2, "put") == pytest.approx(10.0)
        assert _bs_price(100, 90, 0.05, 0.0, 0.2, "put") == pytest.approx(0.0)

    def test_zero_vol(self):
        """Zero volatility → zero option price."""
        assert _bs_price(100, 100, 0.05, 1.0, 0.0, "call") == 0.0

    def test_call_positive(self):
        """Option price is always non-negative."""
        assert _bs_price(80, 100, 0.05, 1.0, 0.3, "call") >= 0.0


# =============================================================================
#  implied_vol — round-trip test: price → IV → price
# =============================================================================

class TestImpliedVol:

    @pytest.mark.parametrize("sigma", [0.10, 0.20, 0.35, 0.50])
    def test_round_trip_call(self, sigma):
        """BS price a call, then invert — should recover the original sigma."""
        price = _bs_price(S=100, K=100, r=0.05, T=1.0, sigma=sigma, option_type="call")
        recovered = implied_vol(price, S=100, K=100, r=0.05, T=1.0, option_type="call")
        assert abs(recovered - sigma) < 1e-5

    @pytest.mark.parametrize("sigma", [0.10, 0.20, 0.35, 0.50])
    def test_round_trip_put(self, sigma):
        """BS price a put, then invert — should recover the original sigma."""
        price = _bs_price(S=100, K=110, r=0.05, T=1.0, sigma=sigma, option_type="put")
        recovered = implied_vol(price, S=100, K=110, r=0.05, T=1.0, option_type="put")
        assert abs(recovered - sigma) < 1e-5

    def test_nan_on_zero_price(self):
        """Zero market price → NaN (no solution)."""
        result = implied_vol(0.0, S=100, K=100, r=0.05, T=1.0, option_type="call")
        assert np.isnan(result)

    def test_nan_on_expired(self):
        """T=0 → NaN."""
        result = implied_vol(5.0, S=100, K=100, r=0.05, T=0.0, option_type="call")
        assert np.isnan(result)

    def test_nan_below_intrinsic(self):
        """Price below intrinsic → NaN (arbitrage region, no valid IV)."""
        # Deep ITM call, intrinsic = 20, market_price = 15 < 20
        result = implied_vol(15.0, S=120, K=100, r=0.05, T=1.0, option_type="call")
        assert np.isnan(result)

    def test_otm_call(self):
        """OTM call with reasonable price → valid IV."""
        price = _bs_price(S=100, K=120, r=0.05, T=0.5, sigma=0.25, option_type="call")
        iv = implied_vol(price, S=100, K=120, r=0.05, T=0.5, option_type="call")
        assert abs(iv - 0.25) < 1e-4


# =============================================================================
#  compute_implied_vols — DataFrame-level tests
# =============================================================================

class TestComputeImpliedVols:

    def _make_chain(self, sigmas: list) -> pd.DataFrame:
        """Build a synthetic option chain from known sigmas."""
        rows = []
        S, r, T = 100.0, 0.05, 0.5
        for i, sigma in enumerate(sigmas):
            K = 90 + i * 10
            price = _bs_price(S, K, r, T, sigma, "call")
            rows.append({
                "expiry":      (pd.Timestamp.today() + pd.Timedelta(days=int(T * 365))).strftime("%Y-%m-%d"),
                "strike":      K,
                "option_type": "call",
                "mid":         price,
            })
        return pd.DataFrame(rows)

    def test_iv_column_added(self):
        """compute_implied_vols adds an implied_vol column."""
        chain = self._make_chain([0.2, 0.25, 0.3])
        result = compute_implied_vols(chain, S=100.0, r=0.05)
        assert "implied_vol" in result.columns

    def test_round_trip_dataframe(self):
        """IV values should match the input sigmas used to generate prices."""
        sigmas = [0.20, 0.25, 0.30]
        chain = self._make_chain(sigmas)
        result = compute_implied_vols(chain, S=100.0, r=0.05)
        for i, row in result.iterrows():
            expected = sigmas[i]
            # Tolerance of 1e-3: T is computed from today's date, introducing
            # a rounding of up to ±1 day which propagates to ~0.5e-3 in IV.
            assert abs(row["implied_vol"] - expected) < 1e-3

    def test_t_column_added(self):
        """compute_implied_vols adds a T (time to maturity) column."""
        chain = self._make_chain([0.2])
        result = compute_implied_vols(chain, S=100.0, r=0.05)
        assert "T" in result.columns
        assert result["T"].iloc[0] > 0
