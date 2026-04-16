"""Backtest — walk-forward engine + overfitting-aware statistics + runner."""

from quant.backtest.engine import (
    BacktestResult,
    SignalProducer,
    WalkForwardConfig,
    walk_forward,
)
from quant.backtest.reproducibility import ReproManifest, build_manifest
from quant.backtest.runner import (
    RunConfig,
    SignalSpec,
    StatsSpec,
    load_config,
    load_prices_csv,
    run_backtest,
)
from quant.backtest.signals import MomentumSignal
from quant.backtest.statistics import (
    deflated_sharpe_ratio,
    probability_of_backtest_overfitting,
    sharpe_ratio,
)

__all__ = [
    "BacktestResult",
    "MomentumSignal",
    "ReproManifest",
    "RunConfig",
    "SignalProducer",
    "SignalSpec",
    "StatsSpec",
    "WalkForwardConfig",
    "build_manifest",
    "deflated_sharpe_ratio",
    "load_config",
    "load_prices_csv",
    "probability_of_backtest_overfitting",
    "run_backtest",
    "sharpe_ratio",
    "walk_forward",
]
