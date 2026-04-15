"""Tests for PurgedKFold."""

from __future__ import annotations

import numpy as np
import pytest

from quant.cv.purged_kfold import PurgedKFold


def test_splits_are_disjoint_and_cover_validation() -> None:
    n, k = 100, 5
    X = np.arange(n).reshape(-1, 1)
    end = np.arange(n)  # zero-length label windows
    cv = PurgedKFold(k, end, embargo_frac=0.0)
    val_union: set[int] = set()
    for tr, va in cv.split(X):
        assert not (set(tr) & set(va)), "train/val overlap"
        val_union |= set(va.tolist())
    assert val_union == set(range(n))


def test_purging_removes_overlapping_train_samples() -> None:
    n = 20
    X = np.arange(n).reshape(-1, 1)
    # Each sample's window extends 3 bars forward.
    end = np.minimum(np.arange(n) + 3, n - 1)
    cv = PurgedKFold(4, end, embargo_frac=0.0)
    for _fold, (tr, va) in enumerate(cv.split(X)):
        if len(va) == 0 or len(tr) == 0:
            continue
        val_start, val_end = va.min(), va.max() + 1
        # No training sample's window may end at or past val_start while
        # starting before val_end.
        for i in tr:
            assert not (end[i] >= val_start and i < val_end), (
                f"sample {i} overlaps val [{val_start}, {val_end})"
            )


def test_embargo_excludes_adjacent_samples() -> None:
    n = 100
    X = np.arange(n).reshape(-1, 1)
    end = np.arange(n)
    cv = PurgedKFold(5, end, embargo_frac=0.05)  # 5 bars either side
    for tr, va in cv.split(X):
        val_end = va.max() + 1
        # Samples within 5 bars after val_end must not appear in train.
        embargoed = set(range(val_end, min(n, val_end + 5)))
        assert not (set(tr) & embargoed)


def test_n_splits_validated() -> None:
    with pytest.raises(ValueError):
        PurgedKFold(1, np.array([0]))
    with pytest.raises(ValueError):
        PurgedKFold(2, np.array([0]), embargo_frac=0.6)
