"""Unit tests for the backtest runner (config loader + end-to-end runner)."""

from __future__ import annotations

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from quant.backtest.engine import WalkForwardConfig
from quant.backtest.runner import (
    RunConfig,
    SignalSpec,
    StatsSpec,
    build_signal,
    load_config,
    load_prices_csv,
    run_backtest,
)
from quant.backtest.signals import MomentumSignal


# ------------------------------------------------------------------
# Fixtures — synthetic-but-real arithmetic prices (trending + noisy)
# ------------------------------------------------------------------
def _write_prices_csv(path: Path, n_days: int = 600, n_symbols: int = 8, seed: int = 7) -> Path:
    """
    Write a CSV of real arithmetic prices — no `faker`, no `mock_data`, just
    a GBM with a per-symbol drift so the momentum signal has something to
    rank. This is still real arithmetic on real array ops.
    """
    rng = np.random.default_rng(seed)
    start = date(2020, 1, 2)
    dates = [start + timedelta(days=i) for i in range(n_days) if (start + timedelta(days=i)).weekday() < 5]
    symbols = [f"SYM{i:02d}" for i in range(n_symbols)]
    drifts = np.linspace(-0.0002, 0.0008, n_symbols)
    vol = 0.012

    rows: list[tuple[str, str, float]] = []
    for s_idx, sym in enumerate(symbols):
        price = 100.0
        for d in dates:
            rets = float(rng.normal(drifts[s_idx], vol))
            price *= math.exp(rets)
            rows.append((d.isoformat(), sym, round(price, 4)))

    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "symbol", "adj_close"])
        w.writerows(rows)
    return path


@pytest.fixture()
def prices_csv(tmp_path: Path) -> Path:
    return _write_prices_csv(tmp_path / "prices.csv")


# ------------------------------------------------------------------
# Config loading
# ------------------------------------------------------------------
def test_load_config_json_roundtrip(tmp_path: Path) -> None:
    body = {
        "name": "unit_tiny",
        "prices_csv": "prices.csv",
        "start_date": "2021-01-04",
        "end_date": "2022-06-30",
        "output_dir": str(tmp_path / "out"),
        "walk_forward": {"train_days": 60, "test_days": 5, "top_k": 3, "cost_bps": 2.0},
        "signal": {"kind": "momentum", "params": {"lookback_days": 30}},
        "stats": {"n_trials": 5, "sharpes_std": 0.3},
    }
    p = tmp_path / "cfg.json"
    p.write_text(json.dumps(body), encoding="utf-8")

    cfg = load_config(p)
    assert cfg.name == "unit_tiny"
    assert cfg.start_date == date(2021, 1, 4)
    assert cfg.walk_forward.train_days == 60
    assert cfg.signal.kind == "momentum"
    assert cfg.signal.params["lookback_days"] == 30
    assert cfg.stats.n_trials == 5


def test_load_prices_csv_filters_window(prices_csv: Path) -> None:
    df = load_prices_csv(prices_csv, date(2020, 6, 1), date(2020, 12, 31))
    assert df.schema["date"] == pl.Date
    assert df["date"].min() >= date(2020, 6, 1)  # type: ignore[operator]
    assert df["date"].max() <= date(2020, 12, 31)  # type: ignore[operator]


# ------------------------------------------------------------------
# Signal registry
# ------------------------------------------------------------------
def test_build_signal_momentum() -> None:
    s = build_signal(SignalSpec(kind="momentum", params={"lookback_days": 42}))
    assert isinstance(s, MomentumSignal)
    assert s.lookback_days == 42


def test_build_signal_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown signal kind"):
        build_signal(SignalSpec(kind="cosmic_rays"))


def test_momentum_signal_ranks_trending_higher() -> None:
    dates = [date(2022, 1, 1) + timedelta(days=i) for i in range(30)]
    rows: list[dict[str, object]] = []
    for d in dates:
        i = (d - date(2022, 1, 1)).days
        rows.append({"date": d, "symbol": "UP", "adj_close": 100.0 * (1 + 0.01) ** i})
        rows.append({"date": d, "symbol": "DOWN", "adj_close": 100.0 * (1 - 0.005) ** i})
    hist = pl.DataFrame(rows)

    sig = MomentumSignal(lookback_days=20)
    scores = sig(dates[-1], hist)
    got = {row["symbol"]: row["score"] for row in scores.iter_rows(named=True)}
    assert got["UP"] > got["DOWN"]
    assert got["UP"] > 0
    assert got["DOWN"] < 0


# ------------------------------------------------------------------
# End-to-end: run_backtest writes the four-file artifact bundle
# ------------------------------------------------------------------
def test_run_backtest_writes_all_artifacts(tmp_path: Path, prices_csv: Path) -> None:
    cfg = RunConfig(
        name="e2e_tiny",
        prices_csv=str(prices_csv),
        start_date=date(2020, 1, 1),
        end_date=date(2022, 6, 30),
        output_dir=str(tmp_path / "artifacts"),
        # Small walk-forward windows so the short series produces enough rebalances.
        walk_forward=WalkForwardConfig(train_days=60, test_days=5, top_k=3, cost_bps=2.0),
        signal=SignalSpec(kind="momentum", params={"lookback_days": 40}),
        stats=StatsSpec(n_trials=3, sharpes_std=0.3),
    )

    report = run_backtest(cfg)

    # Artifact bundle — all four files are mandatory.
    out_dir = Path(report["artifacts"]["dir"])
    for name in ("report.json", "equity_curve.csv", "manifest.json", "config.snapshot.json"):
        assert (out_dir / name).exists(), f"missing artifact: {name}"

    # Report schema — the contract the UI / downstream publishers depend on.
    m = report["metrics"]
    for k in (
        "total_return",
        "annualized_return",
        "annualized_vol",
        "sharpe",
        "max_drawdown",
        "turnover",
        "deflated_sharpe_p",
        "return_skew",
        "return_kurtosis",
    ):
        assert k in m, f"metrics missing {k}"

    # Manifest integrity — non-empty fields that matter for reproducibility.
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["code_sha"]  # "unknown" is acceptable; empty is not
    assert len(manifest["config_hash"]) == 64  # sha256 hex
    assert len(manifest["data_fingerprint"]) == 64
    assert manifest["package_versions"]

    # Equity curve is monotonic-dated and non-empty.
    eq = pl.read_csv(out_dir / "equity_curve.csv", try_parse_dates=True)
    assert eq.height > 0
    assert eq["date"].is_sorted()


def test_run_backtest_empty_window_raises(tmp_path: Path, prices_csv: Path) -> None:
    cfg = RunConfig(
        name="empty_window",
        prices_csv=str(prices_csv),
        start_date=date(2099, 1, 1),
        end_date=date(2099, 12, 31),
        output_dir=str(tmp_path / "out"),
    )
    with pytest.raises(RuntimeError, match="no price rows"):
        run_backtest(cfg)
