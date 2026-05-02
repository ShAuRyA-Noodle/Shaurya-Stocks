"""
Probability calibration for the LightGBM trainer.

Gradient-boosted decision trees produce raw `predict_proba` outputs that are
typically *miscalibrated* — over-confident at the extremes, especially on
class-imbalanced multiclass problems like ours (the triple-barrier label
distribution is dominated by the vertical-barrier-timeout class). A model
saying "70% probability of +1" is only useful if 70% of those predictions
actually realize +1 in practice. Calibration is the diagnostic + the fix.

This module provides:

1. `expected_calibration_error(probs, labels, n_bins)` — Expected Calibration
   Error (ECE) per class, one-vs-rest. ECE ∈ [0, 1]; lower is better. A
   model with ECE = 0 is perfectly calibrated; ECE > 0.05 typically means
   the published probabilities should not be trusted as decision confidences.

2. `fit_isotonic_per_class(probs, labels)` — fits one isotonic regression
   per class on out-of-fold predictions. Isotonic is non-parametric and
   monotone, makes no shape assumption beyond "higher raw probability →
   higher true frequency". The standard choice for tree ensembles.

3. `apply_calibrators(probs, calibrators)` — applies the per-class
   calibrators and renormalizes each row to sum to 1 (the calibrators are
   independent per class, so the row sum drifts; renormalization keeps the
   output a valid probability vector).

Calibrators are fit on OOF predictions — never on training data — so the
calibration step does not leak through purged K-fold's protections.
"""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression


def expected_calibration_error(
    probs: np.ndarray,
    labels: np.ndarray,
    n_bins: int = 15,
) -> dict[int, float]:
    """
    Per-class ECE under the one-vs-rest framing.

    `probs` is (n_samples, n_classes); `labels` is (n_samples,) integer-encoded.
    Returns {class_idx: ece_for_that_class, ..., -1: macro_average}.
    """
    if probs.ndim != 2:
        raise ValueError("probs must be 2-D (n_samples, n_classes)")
    n_samples, n_classes = probs.shape
    if labels.shape != (n_samples,):
        raise ValueError("labels must be 1-D with len == n_samples")
    if n_bins < 2:
        raise ValueError("n_bins must be >= 2")

    edges = np.linspace(0.0, 1.0, n_bins + 1)
    out: dict[int, float] = {}
    for cls in range(n_classes):
        confidence = probs[:, cls]
        is_correct = (labels == cls).astype(np.float64)
        ece = 0.0
        for b in range(n_bins):
            lo, hi = edges[b], edges[b + 1]
            # Closed lower boundary on the first bin so confidence = 0.0
            # samples are still counted; subsequent bins are half-open.
            if b == 0:
                mask = (confidence >= lo) & (confidence <= hi)
            else:
                mask = (confidence > lo) & (confidence <= hi)
            if not mask.any():
                continue
            avg_conf = float(confidence[mask].mean())
            avg_acc = float(is_correct[mask].mean())
            weight = float(mask.sum()) / n_samples
            ece += weight * abs(avg_conf - avg_acc)
        out[cls] = ece

    out[-1] = float(np.mean([out[c] for c in range(n_classes)]))
    return out


def fit_isotonic_per_class(
    probs: np.ndarray,
    labels: np.ndarray,
) -> list[IsotonicRegression]:
    """
    Fit one IsotonicRegression per class on (raw_proba_for_class, is_class) pairs.
    Returns a list of length n_classes.
    """
    if probs.ndim != 2:
        raise ValueError("probs must be 2-D")
    n_classes = probs.shape[1]
    calibrators: list[IsotonicRegression] = []
    for cls in range(n_classes):
        raw = probs[:, cls]
        target = (labels == cls).astype(np.float64)
        ir = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        ir.fit(raw, target)
        calibrators.append(ir)
    return calibrators


def apply_calibrators(
    probs: np.ndarray,
    calibrators: list[IsotonicRegression],
) -> np.ndarray:
    """
    Apply the per-class calibrators and renormalize each row to sum to 1.

    Independent per-class calibration breaks the simplex constraint; the
    renormalization restores it. If a row sums to ~0 (every class came back
    near-zero — pathological) we fall back to uniform across classes rather
    than divide by zero.
    """
    if probs.ndim != 2:
        raise ValueError("probs must be 2-D")
    if probs.shape[1] != len(calibrators):
        raise ValueError(f"probs has {probs.shape[1]} classes, but {len(calibrators)} calibrators provided")
    out = np.zeros_like(probs, dtype=np.float64)
    for cls, ir in enumerate(calibrators):
        out[:, cls] = ir.transform(probs[:, cls])

    row_sums = out.sum(axis=1, keepdims=True)
    eps = 1e-12
    safe = np.where(row_sums < eps, 1.0, row_sums)
    out = out / safe
    fallback_mask = row_sums.flatten() < eps
    if fallback_mask.any():
        out[fallback_mask] = 1.0 / probs.shape[1]
    return out


__all__ = [
    "apply_calibrators",
    "expected_calibration_error",
    "fit_isotonic_per_class",
]
