"""Tests for triple-barrier labeling."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl

from quant.labels.triple_barrier import TripleBarrierConfig, triple_barrier_labels


def _drifting_path(symbol: str, n: int, drift: float, seed: int) -> pl.DataFrame:
    """Random walk with a given drift per step. Non-zero vol so σ > min_vol."""
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, 0.002, size=n)
    prices = 100.0 * np.cumprod(1.0 + rets)
    return pl.DataFrame(
        {
            "date": [date(2024, 1, 2) + timedelta(days=i) for i in range(n)],
            "symbol": [symbol] * n,
            "adj_close": prices.tolist(),
        }
    )


def _monotonic_up(n: int = 50) -> pl.DataFrame:
    return _drifting_path("UP", n, drift=0.02, seed=1)


def _monotonic_down(n: int = 50) -> pl.DataFrame:
    return _drifting_path("DOWN", n, drift=-0.02, seed=2)


def test_monotonic_up_labels_all_positive_or_zero() -> None:
    df = _monotonic_up(60)
    out = triple_barrier_labels(df, TripleBarrierConfig(horizon=5, pt_sigma=1.0, sl_sigma=1.0))
    labeled = out.filter(pl.col("label").is_not_null())
    assert labeled.height > 0
    # A strictly rising path should never hit the lower barrier.
    assert (labeled["label"] >= 0).all()


def test_monotonic_down_labels_never_positive() -> None:
    df = _monotonic_down(60)
    out = triple_barrier_labels(df, TripleBarrierConfig(horizon=5, pt_sigma=1.0, sl_sigma=1.0))
    labeled = out.filter(pl.col("label").is_not_null())
    assert labeled.height > 0
    assert (labeled["label"] <= 0).all()


def test_label_columns_present() -> None:
    df = _monotonic_up(40)
    out = triple_barrier_labels(df)
    for col in ("label", "touch_date", "fwd_ret"):
        assert col in out.columns
