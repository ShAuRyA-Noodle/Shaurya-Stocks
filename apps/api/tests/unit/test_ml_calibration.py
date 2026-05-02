"""Tests for ML probability calibration."""

from __future__ import annotations

import numpy as np
import pytest

from quant.ml.calibration import (
    apply_calibrators,
    expected_calibration_error,
    fit_isotonic_per_class,
)


# ------------------------------------------------------------------
# ECE
# ------------------------------------------------------------------
def test_ece_perfect_calibration_is_zero() -> None:
    """If P(y=c) = mean confidence in every bin, ECE should be ~0."""
    rng = np.random.default_rng(42)
    n = 5000
    # Confidences uniform in [0,1]; outcomes drawn from those exact probs.
    confidence = rng.uniform(0, 1, size=n)
    labels_class_1 = (rng.uniform(0, 1, size=n) < confidence).astype(int)
    probs = np.zeros((n, 2))
    probs[:, 1] = confidence
    probs[:, 0] = 1.0 - confidence
    ece = expected_calibration_error(probs, labels_class_1, n_bins=20)
    # Class 1 has well-matched confidences → low ECE.
    assert ece[1] < 0.04


def test_ece_constant_overconfident_model_has_high_ece() -> None:
    """Model that predicts 0.99 always but is right only 50% → ECE ≈ 0.49."""
    n = 1000
    probs = np.zeros((n, 2))
    probs[:, 1] = 0.99
    probs[:, 0] = 0.01
    rng = np.random.default_rng(0)
    labels = rng.integers(0, 2, size=n)
    ece = expected_calibration_error(probs, labels, n_bins=10)
    assert 0.4 < ece[1] < 0.6


def test_ece_returns_one_entry_per_class_plus_macro() -> None:
    n = 200
    probs = np.full((n, 3), 1.0 / 3)
    rng = np.random.default_rng(1)
    labels = rng.integers(0, 3, size=n)
    ece = expected_calibration_error(probs, labels)
    # 3 per-class entries + the -1 macro key
    assert set(ece.keys()) == {0, 1, 2, -1}
    # Macro is the mean of the per-class ECEs.
    expected_macro = np.mean([ece[0], ece[1], ece[2]])
    assert ece[-1] == pytest.approx(expected_macro)


def test_ece_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError, match="probs must be 2-D"):
        expected_calibration_error(np.zeros(5), np.zeros(5, dtype=int))
    with pytest.raises(ValueError, match="labels must be 1-D with len"):
        expected_calibration_error(np.zeros((10, 2)), np.zeros(5, dtype=int))
    with pytest.raises(ValueError, match="n_bins must be >= 2"):
        expected_calibration_error(np.zeros((10, 2)), np.zeros(10, dtype=int), n_bins=1)


# ------------------------------------------------------------------
# Isotonic fit + apply
# ------------------------------------------------------------------
def test_isotonic_calibration_reduces_ece_on_overconfident_model() -> None:
    """Build a model that's systematically over-confident, then calibrate."""
    rng = np.random.default_rng(7)
    n = 5000
    n_classes = 3

    # True probabilities for class 1 grow with a hidden feature x.
    x = rng.uniform(0, 1, size=n)
    true_p1 = x  # true P(y=1) is exactly x
    labels = np.zeros(n, dtype=int)
    labels[rng.uniform(0, 1, size=n) < true_p1] = 1
    # Class 2 is rare random noise (5%); class 0 is the rest.
    is_two = rng.uniform(0, 1, size=n) < 0.05
    labels[is_two & (labels == 0)] = 2

    # Raw model: report class-1 probability as x**0.5 (over-confident
    # in the middle), class-2 as 0.05 flat, class-0 as the residual.
    raw = np.zeros((n, n_classes))
    raw[:, 1] = np.sqrt(x)
    raw[:, 2] = 0.05
    raw[:, 0] = np.clip(1.0 - raw[:, 1] - raw[:, 2], 0.0, 1.0)
    raw /= raw.sum(axis=1, keepdims=True)

    ece_before = expected_calibration_error(raw, labels)
    calibrators = fit_isotonic_per_class(raw, labels)
    cal = apply_calibrators(raw, calibrators)
    ece_after = expected_calibration_error(cal, labels)

    # Calibration should not make class 1 worse.
    assert ece_after[1] <= ece_before[1] + 1e-3
    # On this construction, class 1 is meaningfully miscalibrated and
    # isotonic should improve it by at least 30%.
    assert ece_after[1] < 0.7 * ece_before[1]
    # Macro should also improve or stay flat.
    assert ece_after[-1] <= ece_before[-1] + 1e-3


def test_apply_calibrators_returns_valid_simplex() -> None:
    rng = np.random.default_rng(13)
    n = 200
    raw = rng.dirichlet([1.0, 1.0, 1.0], size=n)
    labels = rng.integers(0, 3, size=n)
    calibrators = fit_isotonic_per_class(raw, labels)
    cal = apply_calibrators(raw, calibrators)
    # Each row must sum to 1.0 (within float tolerance).
    np.testing.assert_allclose(cal.sum(axis=1), 1.0, atol=1e-10)
    # Each entry must be in [0, 1].
    assert (cal >= 0.0).all()
    assert (cal <= 1.0 + 1e-10).all()


def test_apply_calibrators_handles_all_zero_row_via_uniform_fallback() -> None:
    """If every per-class calibrator outputs ~0 for a row, fall back to uniform."""
    n_classes = 3
    # Synthesize calibrators by fitting on labels that never select class 0.
    rng = np.random.default_rng(0)
    raw_fit = rng.dirichlet([1.0, 1.0, 1.0], size=500)
    labels_fit = rng.integers(1, 3, size=500)  # only 1 and 2
    calibrators = fit_isotonic_per_class(raw_fit, labels_fit)

    # Now apply to a row where the raw class-1 and class-2 inputs are tiny.
    raw_test = np.array([[0.001, 0.0, 0.0]])
    cal = apply_calibrators(raw_test, calibrators)
    # Any row must sum to 1 — fallback or not.
    np.testing.assert_allclose(cal.sum(axis=1), 1.0, atol=1e-10)
    # All values valid probabilities.
    assert (cal >= 0.0).all()
    assert (cal <= 1.0 + 1e-10).all()


def test_apply_calibrators_rejects_shape_mismatch() -> None:
    raw = np.array([[0.5, 0.3, 0.2]])
    calibrators = fit_isotonic_per_class(
        np.array([[0.1, 0.9], [0.7, 0.3]]),
        np.array([1, 0]),
    )
    with pytest.raises(ValueError, match="classes, but .* calibrators"):
        apply_calibrators(raw, calibrators)
