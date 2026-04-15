"""Backtest — walk-forward engine + overfitting-aware statistics."""

from quant.backtest.engine import (
    BacktestResult,
    SignalProducer,
    WalkForwardConfig,
    walk_forward,
)
from quant.backtest.reproducibility import ReproManifest, build_manifest
from quant.backtest.statistics import (
    deflated_sharpe_ratio,
    probability_of_backtest_overfitting,
    sharpe_ratio,
)

__all__ = [
    "BacktestResult",
    "ReproManifest",
    "SignalProducer",
    "WalkForwardConfig",
    "build_manifest",
    "deflated_sharpe_ratio",
    "probability_of_backtest_overfitting",
    "sharpe_ratio",
    "walk_forward",
]
