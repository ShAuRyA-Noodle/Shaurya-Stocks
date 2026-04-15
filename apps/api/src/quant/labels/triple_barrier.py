"""
Triple-barrier labeling (López de Prado, AFML ch. 3).

For each bar t, place three barriers in the forward window [t, t+horizon]:
    upper  = close_t * (1 + pt_sigma * σ_t)
    lower  = close_t * (1 - sl_sigma * σ_t)
    vertical = t + horizon

Label = +1 if upper hit first, -1 if lower hit first, 0 if vertical hit first
(or no barrier touched by the last bar in the window).

σ_t is the rolling std of log returns (same window as used for features),
so barriers scale with local volatility — same-sized moves are stronger
signals in quiet regimes than in loud ones.

Output also exposes `touch_date` (when a barrier fired) and `fwd_ret` (return
realized at touch) for meta-labeling and sample-weight schemes.

Input contract: a polars DataFrame with columns (date, symbol, adj_close, log_ret_1d),
sorted by (symbol, date). Output: same rows plus (label, touch_date, fwd_ret).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl


@dataclass(frozen=True)
class TripleBarrierConfig:
    horizon: int = 5  # vertical barrier in trading days
    pt_sigma: float = 2.0  # profit-take = +pt_sigma * σ
    sl_sigma: float = 2.0  # stop-loss   = -sl_sigma * σ
    vol_window: int = 21  # σ estimation window
    min_vol: float = 1e-4  # floor on σ to avoid div-by-zero / hair-trigger labels


def triple_barrier_labels(df: pl.DataFrame, cfg: TripleBarrierConfig | None = None) -> pl.DataFrame:
    cfg = cfg or TripleBarrierConfig()
    required = ("date", "symbol", "adj_close")
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")

    df = df.sort(["symbol", "date"])
    # Daily log returns → rolling σ (local volatility)
    df = df.with_columns(
        (pl.col("adj_close") / pl.col("adj_close").shift(1).over("symbol")).log().alias("_lret"),
    ).with_columns(
        pl.col("_lret")
        .rolling_std(window_size=cfg.vol_window, min_periods=cfg.vol_window)
        .over("symbol")
        .alias("_sigma"),
    )

    # For per-symbol vectorization, operate inside a per-group loop.
    # Polars doesn't have a stock "first-crossing" op, but numpy vectorizes per symbol cleanly.
    out_frames: list[pl.DataFrame] = []
    for (_sym,), sub in df.group_by(["symbol"], maintain_order=True):
        sub_sorted = sub.sort("date")
        labels, touch_dates, fwd_rets = _label_one_symbol(sub_sorted, cfg)
        out_frames.append(
            sub_sorted.with_columns(
                pl.Series("label", labels, dtype=pl.Int8),
                pl.Series("touch_date", touch_dates, dtype=pl.Date),
                pl.Series("fwd_ret", fwd_rets, dtype=pl.Float64),
            )
        )

    result = (
        pl.concat(out_frames)
        if out_frames
        else df.with_columns(
            pl.lit(None).cast(pl.Int8).alias("label"),
            pl.lit(None).cast(pl.Date).alias("touch_date"),
            pl.lit(None).cast(pl.Float64).alias("fwd_ret"),
        )
    )
    return result.drop(["_lret", "_sigma"])


def _label_one_symbol(
    sub: pl.DataFrame, cfg: TripleBarrierConfig
) -> tuple[list[int | None], list[object], list[float | None]]:
    n = sub.height
    close = sub["adj_close"].to_numpy().astype(float)
    sigma = sub["_sigma"].to_numpy().astype(float)
    dates = sub["date"].to_list()

    labels: list[int | None] = [None] * n
    touch_dates: list[object] = [None] * n
    fwd_rets: list[float | None] = [None] * n

    for i in range(n):
        s = sigma[i]
        if np.isnan(s) or s < cfg.min_vol:
            continue
        upper = close[i] * (1.0 + cfg.pt_sigma * s)
        lower = close[i] * (1.0 - cfg.sl_sigma * s)
        end = min(i + cfg.horizon, n - 1)
        if end <= i:
            continue

        label = 0  # vertical barrier default
        touch_idx = end
        for j in range(i + 1, end + 1):
            if close[j] >= upper:
                label = 1
                touch_idx = j
                break
            if close[j] <= lower:
                label = -1
                touch_idx = j
                break

        labels[i] = label
        touch_dates[i] = dates[touch_idx]
        fwd_rets[i] = float(close[touch_idx] / close[i] - 1.0)

    return labels, touch_dates, fwd_rets
