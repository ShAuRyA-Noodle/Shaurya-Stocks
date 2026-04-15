"""
LightGBM trainer with MLflow tracking + purged K-fold validation.

Given a feature matrix X, labels y (from triple-barrier), and sample end
indices (for purging), trains one LightGBM multiclass model per fold, logs
metrics to MLflow, and returns the ensemble (list of boosters).

Usage:
    from quant.models.lightgbm_trainer import LightGBMEnsemble, TrainConfig

    ens = LightGBMEnsemble.train(
        X, y, sample_end_idx,
        feature_names=list(FEATURE_COLUMNS),
        cfg=TrainConfig(n_splits=5, params={...}),
        run_name="ts_xgb_AAPL",
    )
    probs = ens.predict_proba(X_test)  # averages across folds
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import lightgbm as lgb
import mlflow
import numpy as np
from sklearn.metrics import accuracy_score, log_loss

from quant.config import settings
from quant.cv.purged_kfold import PurgedKFold

log = logging.getLogger("quant.models.lightgbm")


# Default params tuned for triple-barrier 3-class (-1, 0, +1) on daily equity data.
DEFAULT_PARAMS: dict[str, Any] = {
    "objective": "multiclass",
    "num_class": 3,
    "metric": "multi_logloss",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "lambda_l1": 0.1,
    "lambda_l2": 0.1,
    "verbose": -1,
    "deterministic": True,
    "seed": 42,
}


@dataclass
class TrainConfig:
    n_splits: int = 5
    embargo_frac: float = 0.01
    num_boost_round: int = 1000
    early_stopping_rounds: int = 50
    params: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_PARAMS))


@dataclass
class FoldResult:
    fold: int
    train_size: int
    val_size: int
    val_logloss: float
    val_accuracy: float
    best_iteration: int
    booster: lgb.Booster


class LightGBMEnsemble:
    """Ensemble of K boosters trained via purged K-fold."""

    def __init__(
        self,
        boosters: list[lgb.Booster],
        classes: np.ndarray,
        feature_names: list[str],
        mlflow_run_id: str | None = None,
    ) -> None:
        self.boosters = boosters
        self.classes = classes
        self.feature_names = feature_names
        self.mlflow_run_id = mlflow_run_id

    # ----- training -----
    @classmethod
    def train(
        cls,
        X: np.ndarray,
        y: np.ndarray,
        sample_end_idx: np.ndarray,
        *,
        feature_names: list[str],
        cfg: TrainConfig | None = None,
        run_name: str = "lgbm",
        mlflow_experiment: str | None = None,
    ) -> LightGBMEnsemble:
        cfg = cfg or TrainConfig()
        if X.shape[0] != len(y):
            raise ValueError(f"X/y length mismatch: {X.shape[0]} vs {len(y)}")

        # Remap class labels to contiguous 0..K-1 for LightGBM.
        classes = np.array(sorted(np.unique(y)))
        class_to_idx = {c: i for i, c in enumerate(classes.tolist())}
        y_enc = np.array([class_to_idx[c] for c in y.tolist()], dtype=np.int32)

        cv = PurgedKFold(cfg.n_splits, sample_end_idx, embargo_frac=cfg.embargo_frac)

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(mlflow_experiment or settings.mlflow_experiment_name)

        params = dict(cfg.params)
        params["num_class"] = len(classes)

        fold_results: list[FoldResult] = []
        with mlflow.start_run(run_name=run_name) as run:
            mlflow.log_params(
                {
                    "n_splits": cfg.n_splits,
                    "embargo_frac": cfg.embargo_frac,
                    "num_boost_round": cfg.num_boost_round,
                    "early_stopping_rounds": cfg.early_stopping_rounds,
                    "n_features": X.shape[1],
                    "n_samples": X.shape[0],
                    "n_classes": len(classes),
                    **{f"lgb_{k}": v for k, v in params.items()},
                }
            )

            for fold, (tr_idx, va_idx) in enumerate(cv.split(X)):
                if len(tr_idx) == 0 or len(va_idx) == 0:
                    log.warning("fold %d has empty split, skipping", fold)
                    continue
                tr_set = lgb.Dataset(
                    X[tr_idx], label=y_enc[tr_idx], feature_name=feature_names, free_raw_data=False
                )
                va_set = lgb.Dataset(
                    X[va_idx],
                    label=y_enc[va_idx],
                    feature_name=feature_names,
                    free_raw_data=False,
                    reference=tr_set,
                )
                booster = lgb.train(
                    params,
                    tr_set,
                    num_boost_round=cfg.num_boost_round,
                    valid_sets=[va_set],
                    valid_names=["val"],
                    callbacks=[
                        lgb.early_stopping(cfg.early_stopping_rounds, verbose=False),
                        lgb.log_evaluation(0),
                    ],
                )

                val_pred = booster.predict(X[va_idx], num_iteration=booster.best_iteration)
                val_logloss = log_loss(y_enc[va_idx], val_pred, labels=list(range(len(classes))))
                val_acc = accuracy_score(y_enc[va_idx], np.argmax(val_pred, axis=1))

                fold_results.append(
                    FoldResult(
                        fold=fold,
                        train_size=len(tr_idx),
                        val_size=len(va_idx),
                        val_logloss=float(val_logloss),
                        val_accuracy=float(val_acc),
                        best_iteration=booster.best_iteration or 0,
                        booster=booster,
                    )
                )
                mlflow.log_metrics(
                    {
                        f"fold{fold}_val_logloss": float(val_logloss),
                        f"fold{fold}_val_accuracy": float(val_acc),
                    }
                )

            if not fold_results:
                raise RuntimeError("no valid folds trained")
            mlflow.log_metric("cv_val_logloss_mean", float(np.mean([r.val_logloss for r in fold_results])))
            mlflow.log_metric("cv_val_accuracy_mean", float(np.mean([r.val_accuracy for r in fold_results])))
            run_id = run.info.run_id

        return cls(
            boosters=[r.booster for r in fold_results],
            classes=classes,
            feature_names=feature_names,
            mlflow_run_id=run_id,
        )

    # ----- inference -----
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Averaged class probabilities across folds. Shape: (n, len(classes))."""
        preds = [b.predict(X, num_iteration=b.best_iteration) for b in self.boosters]
        return np.mean(np.stack(preds, axis=0), axis=0)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Argmax class labels (in the original class space)."""
        proba = self.predict_proba(X)
        return self.classes[np.argmax(proba, axis=1)]
