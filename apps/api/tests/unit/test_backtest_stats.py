"""Unit tests for deflated Sharpe + PBO."""

from __future__ import annotations

import numpy as np

from quant.backtest.statistics import (
    _expected_max_sharpe,
    deflated_sharpe_ratio,
    probability_of_backtest_overfitting,
    sharpe_ratio,
)


def test_sharpe_ratio_simple() -> None:
    rng = np.random.default_rng(0)
    rets = rng.normal(0.001, 0.01, size=500)
    sr = sharpe_ratio(rets)
    # Expected ≈ 0.001/0.01 * sqrt(252) ≈ 1.58; random sample around it
    assert 0.5 < sr < 3.0


def test_expected_max_sharpe_grows_with_n() -> None:
    assert _expected_max_sharpe(1) == 0.0
    e10 = _expected_max_sharpe(10)
    e100 = _expected_max_sharpe(100)
    assert e10 > 0
    assert e100 > e10


def test_deflated_sharpe_high_trials_hurts() -> None:
    # Same observed sharpe, more trials tried => lower DSR.
    # Use a smaller observed SR so we don't saturate norm.cdf at 1.0.
    low = deflated_sharpe_ratio(0.3, n_trials=5, sharpes_std=0.2, n_obs=60)
    high = deflated_sharpe_ratio(0.3, n_trials=500, sharpes_std=0.2, n_obs=60)
    assert low > high, f"expected low > high, got low={low}, high={high}"
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0


def test_pbo_random_strategies_near_half() -> None:
    """Random iid strategies have no real edge; PBO should be around 0.5."""
    rng = np.random.default_rng(42)
    # 256 periods, 32 strategies, all pure noise
    mat = rng.normal(0, 1, size=(256, 32))
    res = probability_of_backtest_overfitting(mat, n_slices=8)
    # Pure iid noise — PBO should be in the wide middle range (not 0 or 1).
    assert 0.15 < res["pbo"] < 0.85
    assert res["n_trials"] == 70  # C(8, 4)


def test_pbo_one_dominant_strategy_low_pbo() -> None:
    """If one strategy dominates everywhere, PBO should be low."""
    rng = np.random.default_rng(7)
    mat = rng.normal(0, 1, size=(256, 16))
    mat[:, 0] += 0.5  # strategy 0 has a real edge
    res = probability_of_backtest_overfitting(mat, n_slices=8)
    assert res["pbo"] < 0.3
