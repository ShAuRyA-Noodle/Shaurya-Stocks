"""
Technical feature engineering — pure polars, point-in-time safe.

Contract:
- Input: polars DataFrame with columns
    date (Date), symbol (str), open, high, low, close, volume, adj_close
  sorted ascending by (symbol, date).
- Output: same rows, enriched with feature columns. No NaN-leak across symbols
  (every rolling op is grouped by symbol).
- No look-ahead: every feature at row t uses only data with date ≤ t.

Features produced (all computed on adj_close unless noted):
  ret_1d, ret_5d, ret_21d, ret_63d       — simple returns
  log_ret_1d                              — log returns
  vol_5d, vol_21d, vol_63d                — rolling std of log_ret_1d (annualized × √252)
  sma_5, sma_20, sma_50, sma_200          — simple moving averages (ratio to price)
  ema_12, ema_26                          — exponential moving averages (ratio to price)
  rsi_14                                  — Wilder RSI
  macd, macd_signal, macd_hist            — MACD(12,26,9)
  bb_upper, bb_lower, bb_pctb             — Bollinger(20, 2σ); pctb ∈ [0,1] is position in band
  atr_14                                  — Wilder ATR / close (normalized)
  obv                                     — on-balance volume (z-scored over 63d)
  volume_z_21                             — volume z-score over trailing 21d
  high_low_range_21                       — (rolling_max_21 - rolling_min_21) / close
  gap_overnight                           — (open_t - close_{t-1}) / close_{t-1}

Every feature is deterministic. Tests pin numeric output on a fixture.
"""

from __future__ import annotations

import polars as pl

ANNUALIZATION = 252**0.5


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def _rolling_by_symbol(expr: pl.Expr, *, window: int, min_periods: int | None = None) -> pl.Expr:
    """Rolling window within each symbol group, using the `over` partition."""
    return expr.rolling_mean(window_size=window, min_samples=min_periods or window).over("symbol")


def _wilder_rma(col: str, window: int) -> pl.Expr:
    """Wilder's smoothing: exponential mean with alpha = 1/window."""
    return pl.col(col).ewm_mean(alpha=1.0 / window, adjust=False).over("symbol")


# ----------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------
def add_technical_features(df: pl.DataFrame) -> pl.DataFrame:
    """Enrich a (symbol, date, OHLCV) frame with the full technical feature set.

    Input must be sorted by (symbol, date) ascending. `adj_close` is required and
    drives every price-based feature so corporate actions are handled correctly.
    """
    _require_columns(df, ("date", "symbol", "open", "high", "low", "close", "volume", "adj_close"))
    df = df.sort(["symbol", "date"])

    # --- returns ---
    df = df.with_columns(
        pl.col("adj_close").pct_change(1).over("symbol").alias("ret_1d"),
        pl.col("adj_close").pct_change(5).over("symbol").alias("ret_5d"),
        pl.col("adj_close").pct_change(21).over("symbol").alias("ret_21d"),
        pl.col("adj_close").pct_change(63).over("symbol").alias("ret_63d"),
    )
    df = df.with_columns(
        (pl.col("adj_close") / pl.col("adj_close").shift(1).over("symbol")).log().alias("log_ret_1d"),
    )

    # --- realized vol (annualized) ---
    df = df.with_columns(
        (pl.col("log_ret_1d").rolling_std(window_size=5, min_samples=5).over("symbol") * ANNUALIZATION).alias(
            "vol_5d"
        ),
        (
            pl.col("log_ret_1d").rolling_std(window_size=21, min_samples=21).over("symbol") * ANNUALIZATION
        ).alias("vol_21d"),
        (
            pl.col("log_ret_1d").rolling_std(window_size=63, min_samples=63).over("symbol") * ANNUALIZATION
        ).alias("vol_63d"),
    )

    # --- moving averages (as ratio to current price, more stationary than raw) ---
    df = df.with_columns(
        (_rolling_by_symbol(pl.col("adj_close"), window=5) / pl.col("adj_close")).alias("sma_5"),
        (_rolling_by_symbol(pl.col("adj_close"), window=20) / pl.col("adj_close")).alias("sma_20"),
        (_rolling_by_symbol(pl.col("adj_close"), window=50) / pl.col("adj_close")).alias("sma_50"),
        (_rolling_by_symbol(pl.col("adj_close"), window=200) / pl.col("adj_close")).alias("sma_200"),
    )

    # --- EMAs (for MACD and as features) ---
    df = df.with_columns(
        pl.col("adj_close").ewm_mean(span=12, adjust=False).over("symbol").alias("_ema12"),
        pl.col("adj_close").ewm_mean(span=26, adjust=False).over("symbol").alias("_ema26"),
    ).with_columns(
        (pl.col("_ema12") / pl.col("adj_close")).alias("ema_12"),
        (pl.col("_ema26") / pl.col("adj_close")).alias("ema_26"),
        (pl.col("_ema12") - pl.col("_ema26")).alias("macd"),
    )
    df = df.with_columns(
        pl.col("macd").ewm_mean(span=9, adjust=False).over("symbol").alias("macd_signal"),
    ).with_columns(
        (pl.col("macd") - pl.col("macd_signal")).alias("macd_hist"),
    )

    # --- RSI(14) via Wilder smoothing ---
    df = (
        df.with_columns(
            (pl.col("adj_close") - pl.col("adj_close").shift(1).over("symbol")).alias("_delta"),
        )
        .with_columns(
            pl.when(pl.col("_delta") > 0).then(pl.col("_delta")).otherwise(0.0).alias("_gain"),
            pl.when(pl.col("_delta") < 0).then(-pl.col("_delta")).otherwise(0.0).alias("_loss"),
        )
        .with_columns(
            _wilder_rma("_gain", 14).alias("_avg_gain"),
            _wilder_rma("_loss", 14).alias("_avg_loss"),
        )
        .with_columns(
            (pl.col("_avg_gain") / pl.col("_avg_loss")).alias("_rs"),
        )
        .with_columns(
            (100.0 - (100.0 / (1.0 + pl.col("_rs")))).alias("rsi_14"),
        )
    )

    # --- Bollinger bands (20, 2σ) ---
    df = (
        df.with_columns(
            pl.col("adj_close").rolling_mean(window_size=20, min_samples=20).over("symbol").alias("_bb_mid"),
            pl.col("adj_close").rolling_std(window_size=20, min_samples=20).over("symbol").alias("_bb_std"),
        )
        .with_columns(
            (pl.col("_bb_mid") + 2 * pl.col("_bb_std")).alias("bb_upper"),
            (pl.col("_bb_mid") - 2 * pl.col("_bb_std")).alias("bb_lower"),
        )
        .with_columns(
            ((pl.col("adj_close") - pl.col("bb_lower")) / (pl.col("bb_upper") - pl.col("bb_lower"))).alias(
                "bb_pctb"
            ),
        )
    )

    # --- ATR(14), Wilder ---
    df = df.with_columns(
        pl.max_horizontal(
            pl.col("high") - pl.col("low"),
            (pl.col("high") - pl.col("close").shift(1).over("symbol")).abs(),
            (pl.col("low") - pl.col("close").shift(1).over("symbol")).abs(),
        ).alias("_tr"),
    ).with_columns(
        (_wilder_rma("_tr", 14) / pl.col("close")).alias("atr_14"),
    )

    # --- volume features ---
    df = df.with_columns(
        (
            (pl.col("volume") - pl.col("volume").rolling_mean(window_size=21, min_samples=21).over("symbol"))
            / pl.col("volume").rolling_std(window_size=21, min_samples=21).over("symbol")
        ).alias("volume_z_21"),
    )

    # OBV: signed cumulative volume; then z-score over 63d to tame unit-size drift
    df = (
        df.with_columns(
            (
                pl.when(pl.col("adj_close") > pl.col("adj_close").shift(1).over("symbol"))
                .then(pl.col("volume").cast(pl.Float64))
                .when(pl.col("adj_close") < pl.col("adj_close").shift(1).over("symbol"))
                .then(-pl.col("volume").cast(pl.Float64))
                .otherwise(0.0)
            ).alias("_obv_delta"),
        )
        .with_columns(
            pl.col("_obv_delta").cum_sum().over("symbol").alias("_obv_raw"),
        )
        .with_columns(
            pl.col("_obv_raw").rolling_mean(window_size=63, min_samples=63).over("symbol").alias("_obv_mean"),
            pl.col("_obv_raw").rolling_std(window_size=63, min_samples=63).over("symbol").alias("_obv_std"),
        )
        .with_columns(
            ((pl.col("_obv_raw") - pl.col("_obv_mean")) / pl.col("_obv_std")).alias("obv"),
        )
    )

    # --- range + gap ---
    df = df.with_columns(
        (
            (
                pl.col("high").rolling_max(window_size=21, min_samples=21).over("symbol")
                - pl.col("low").rolling_min(window_size=21, min_samples=21).over("symbol")
            )
            / pl.col("close")
        ).alias("high_low_range_21"),
        (
            (pl.col("open") - pl.col("close").shift(1).over("symbol"))
            / pl.col("close").shift(1).over("symbol")
        ).alias("gap_overnight"),
    )

    return df.drop([c for c in df.columns if c.startswith("_")])


# ----------------------------------------------------------------
# Canonical feature list — stable key order for DB + model I/O.
# ----------------------------------------------------------------
FEATURE_COLUMNS: tuple[str, ...] = (
    "ret_1d",
    "ret_5d",
    "ret_21d",
    "ret_63d",
    "log_ret_1d",
    "vol_5d",
    "vol_21d",
    "vol_63d",
    "sma_5",
    "sma_20",
    "sma_50",
    "sma_200",
    "ema_12",
    "ema_26",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_upper",
    "bb_lower",
    "bb_pctb",
    "atr_14",
    "volume_z_21",
    "obv",
    "high_low_range_21",
    "gap_overnight",
)

FEATURE_SET_VERSION = "v1.0"


def _require_columns(df: pl.DataFrame, required: tuple[str, ...]) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"input frame missing required columns: {missing}")
