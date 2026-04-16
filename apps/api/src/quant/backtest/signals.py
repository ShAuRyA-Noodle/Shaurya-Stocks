"""
Built-in SignalProducer implementations for the backtest CLI.

The CLI is deliberately agnostic to the signal source — it takes any
`SignalProducer` (callable returning `DataFrame[symbol, score]`). The
producers here are baselines you can point at without training anything:

- `MomentumSignal(lookback_days)` — score = trailing total return. Well-known,
  reproducible, a sensible null hypothesis the ML model must beat.

The ML-backed producer (load an MLflow-logged LightGBM ensemble, call
`predict_proba`, project to a long-score) is intentionally not wired here;
it requires a trained registry, which is a pipeline concern, not a CLI one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import polars as pl


@dataclass(frozen=True)
class MomentumSignal:
    """Trailing-return momentum. Higher score = stronger uptrend."""

    lookback_days: int = 126  # ~6 trading months

    def __call__(self, as_of: date, history: pl.DataFrame) -> pl.DataFrame:
        if history.is_empty():
            return pl.DataFrame({"symbol": [], "score": []})

        hist = history.filter(pl.col("date") <= as_of).sort(["symbol", "date"])
        # For each symbol, take last N closes and compute (last / first) - 1
        scores = (
            hist.group_by("symbol", maintain_order=True)
            .agg(pl.col("adj_close").tail(self.lookback_days).alias("_tail"))
            .with_columns(
                pl.col("_tail").list.last().alias("_p_end"),
                pl.col("_tail").list.first().alias("_p_start"),
                pl.col("_tail").list.len().alias("_n"),
            )
            .filter((pl.col("_n") >= self.lookback_days) & (pl.col("_p_start") > 0))
            .with_columns((pl.col("_p_end") / pl.col("_p_start") - 1.0).alias("score"))
            .select(["symbol", "score"])
        )
        return scores


__all__ = ["MomentumSignal"]
