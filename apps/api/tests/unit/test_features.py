"""Unit tests for technical feature engineering."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest

from quant.features.technical import FEATURE_COLUMNS, add_technical_features


def _synthetic_ohlcv(symbol: str, n: int, seed: int = 0) -> pl.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0005, 0.015, size=n)
    close = 100.0 * np.cumprod(1.0 + rets)
    # high/low around close, open ~ prev close + small noise
    noise = rng.normal(0, 0.3, size=n)
    open_ = np.concatenate([[close[0]], close[:-1]]) + noise
    high = np.maximum.reduce([open_, close]) * (1 + rng.uniform(0.001, 0.01, n))
    low = np.minimum.reduce([open_, close]) * (1 - rng.uniform(0.001, 0.01, n))
    vol = rng.integers(1_000_000, 5_000_000, size=n)
    start = date(2023, 1, 2)
    dates = [start + timedelta(days=i) for i in range(n)]
    return pl.DataFrame(
        {
            "date": dates,
            "symbol": [symbol] * n,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "adj_close": close,
            "volume": vol,
        }
    )


def test_feature_columns_present_after_build() -> None:
    df = _synthetic_ohlcv("AAPL", 300)
    out = add_technical_features(df)
    for col in FEATURE_COLUMNS:
        assert col in out.columns, f"missing feature: {col}"


def test_features_populated_after_warmup() -> None:
    df = _synthetic_ohlcv("AAPL", 300)
    out = add_technical_features(df)
    tail = out.tail(50)  # deep past the 200-day SMA warmup
    # Every core feature column should be fully populated in the tail.
    for col in FEATURE_COLUMNS:
        nulls = tail[col].null_count()
        nans = int(tail[col].is_nan().sum()) if tail[col].dtype.is_float() else 0
        assert nulls == 0, f"{col} has {nulls} nulls in tail"
        assert nans == 0, f"{col} has {nans} NaNs in tail"


def test_no_leakage_across_symbols() -> None:
    a = _synthetic_ohlcv("AAA", 250, seed=1)
    b = _synthetic_ohlcv("BBB", 250, seed=2)
    merged = pl.concat([a, b]).sort(["symbol", "date"])
    out_merged = add_technical_features(merged)

    out_a_solo = add_technical_features(a).sort("date")
    out_a_from_merged = out_merged.filter(pl.col("symbol") == "AAA").sort("date")
    # Features on AAA should be identical whether computed in isolation or
    # alongside BBB — any difference means a rolling op crossed symbols.
    for col in FEATURE_COLUMNS:
        lhs = out_a_solo[col].to_numpy()
        rhs = out_a_from_merged[col].to_numpy()
        mask = ~(np.isnan(lhs) | np.isnan(rhs))
        np.testing.assert_allclose(
            lhs[mask], rhs[mask], rtol=1e-10, atol=1e-12, err_msg=f"cross-symbol leak in {col}"
        )


def test_rsi_bounded_0_100() -> None:
    df = _synthetic_ohlcv("AAPL", 300)
    out = add_technical_features(df)
    rsi = out["rsi_14"].to_numpy()
    rsi = rsi[~np.isnan(rsi)]
    assert rsi.min() >= 0.0
    assert rsi.max() <= 100.0


def test_missing_required_column_raises() -> None:
    df = _synthetic_ohlcv("AAPL", 10).drop("adj_close")
    with pytest.raises(ValueError, match="missing required columns"):
        add_technical_features(df)
