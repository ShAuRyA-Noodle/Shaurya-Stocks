"""
Purged K-Fold CV with embargo (López de Prado, AFML ch. 7).

Plain K-Fold leaks information when labels overlap in time: a training sample
whose triple-barrier window ends *after* a validation sample's start shares
price-path information with it. This splitter:

1. Purges from the train set any sample whose label window [start_i, end_i]
   overlaps a validation sample's window.
2. Embargoes the `embargo_frac` of bars immediately before and after each
   validation block to prevent near-future leakage via serial correlation.

API mirrors sklearn splitters: `.split(X) → iter[(train_idx, val_idx)]`.

Samples are assumed to be ordered by their start time. The caller provides
`sample_end_idx[i]` = the index position (in the same array) where sample
i's label window closes — typically computed by looking up the triple-barrier
`touch_date` in the sample-date array.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np


class PurgedKFold:
    def __init__(
        self,
        n_splits: int,
        sample_end_idx: np.ndarray,
        *,
        embargo_frac: float = 0.01,
    ) -> None:
        if n_splits < 2:
            raise ValueError("n_splits must be >= 2")
        if not 0.0 <= embargo_frac < 0.5:
            raise ValueError("embargo_frac must be in [0, 0.5)")
        end = np.asarray(sample_end_idx, dtype=np.int64)
        if end.ndim != 1:
            raise ValueError("sample_end_idx must be 1-D")
        self.n_splits = n_splits
        self.sample_end_idx = end
        self.embargo_frac = embargo_frac

    def get_n_splits(self) -> int:
        return self.n_splits

    def split(
        self,
        X: np.ndarray,
        y: np.ndarray | None = None,
        groups: np.ndarray | None = None,
    ) -> Iterator[tuple[np.ndarray, np.ndarray]]:
        del y, groups
        n = len(X)
        if len(self.sample_end_idx) != n:
            raise ValueError(f"sample_end_idx length {len(self.sample_end_idx)} != sample count {n}")

        indices = np.arange(n)
        starts = indices
        ends = np.clip(self.sample_end_idx, 0, n - 1)
        fold_size = n // self.n_splits
        embargo = round(n * self.embargo_frac)

        for k in range(self.n_splits):
            val_start = k * fold_size
            val_end = n if k == self.n_splits - 1 else val_start + fold_size
            val_idx = indices[val_start:val_end]

            train_mask = np.ones(n, dtype=bool)
            train_mask[val_start:val_end] = False

            # Embargo before and after validation block
            train_mask[max(0, val_start - embargo) : val_start] = False
            train_mask[val_end : min(n, val_end + embargo)] = False

            # Purge samples whose [start, end] overlaps [val_start, val_end)
            overlap = (ends >= val_start) & (starts < val_end)
            train_mask &= ~overlap

            yield indices[train_mask], val_idx
