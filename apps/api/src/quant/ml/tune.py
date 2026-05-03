"""
Hyperparameter tuning for the LightGBM trainer via Optuna TPE.

Searches over the LightGBM params + early-stopping rounds that the
existing `quant.ml.trainer` consumes, scoring each trial by 5-fold OOF
log-loss (lower is better). Uses purged K-fold + embargo same as the
production trainer — no leakage.

Memory profile (8GB Mac M2 Air):
- Default 200-symbol panel: ~1.5GB peak per trial.
- 30 trials × ~30s each = ~15 minutes wall time.
- Optuna's storage stays in-process; no SQLite by default.

Output: a JSON report with the best params + per-trial history. The
caller (CLI) can take the winning params and pass them straight into
TrainConfig for a final full run.
"""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import optuna

from quant.ml.config import TrainConfig
from quant.ml.trainer import train

log = logging.getLogger("quant.ml.tune")
optuna.logging.set_verbosity(optuna.logging.WARNING)


@dataclass(frozen=True)
class TuneReport:
    n_trials: int
    best_value: float  # OOF logloss
    best_params: dict[str, Any]
    history: list[dict[str, Any]]


def _objective(trial: optuna.Trial, base_cfg: TrainConfig) -> float:
    """Sample a config, run the trainer, return OOF logloss."""
    params = dict(base_cfg.model.params)
    params.update(
        {
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 127),
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 20, 200),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "lambda_l1": trial.suggest_float("lambda_l1", 0.0, 1.0),
            "lambda_l2": trial.suggest_float("lambda_l2", 0.0, 1.0),
        }
    )
    num_boost_round = trial.suggest_int("num_boost_round", 100, 400)

    # Build a fresh TrainConfig with mutated params. Frozen dataclasses
    # can't be mutated in-place; we deep-copy via dict round-trip.
    cfg_dict = json.loads(json.dumps({"name": base_cfg.name, "_": "_"}, default=lambda o: None))
    del cfg_dict
    new_cfg = TrainConfig(
        name=f"{base_cfg.name}_trial_{trial.number}",
        output_dir=str(Path(base_cfg.output_dir) / "tune_trials"),
        data=base_cfg.data,
        label=base_cfg.label,
        cv=base_cfg.cv,
        model=type(base_cfg.model)(
            num_boost_round=num_boost_round,
            early_stopping_rounds=base_cfg.model.early_stopping_rounds,
            params={**deepcopy(params)},
        ),
        mlflow_experiment=base_cfg.mlflow_experiment,
    )

    report = train(new_cfg)
    logloss = float(report["oof_metrics"]["oof_logloss"])
    log.info("trial %d: logloss=%.4f", trial.number, logloss)
    return logloss


def tune(
    base_cfg: TrainConfig,
    *,
    n_trials: int = 30,
    seed: int = 42,
) -> TuneReport:
    """Run an Optuna TPE study; return the best trial + history."""
    sampler = optuna.samplers.TPESampler(seed=seed)
    study = optuna.create_study(direction="minimize", sampler=sampler)
    study.optimize(lambda t: _objective(t, base_cfg), n_trials=n_trials)

    history = [
        {
            "trial": t.number,
            "value": t.value if t.value is not None else float("nan"),
            "params": dict(t.params),
        }
        for t in study.trials
    ]
    best = study.best_trial
    return TuneReport(
        n_trials=n_trials,
        best_value=float(best.value if best.value is not None else float("nan")),
        best_params=dict(best.params),
        history=history,
    )


__all__ = ["TuneReport", "tune"]
