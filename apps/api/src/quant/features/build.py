"""
Feature build orchestrator.

Pipeline:
1. Load OHLCV daily bars from `public.ohlcv_daily` for a set of symbols and
   a lookback window (extra 300d head buffer so 200-day SMAs populate).
2. Run `add_technical_features` via polars.
3. UPSERT one row per (date, symbol, feature_set_version) into
   `feature.features_daily`, dropping any rows whose feature window isn't
   fully populated yet (NaN-bearing — avoids writing junk PIT data).

Idempotent: rerunning overwrites by primary key.
"""

from __future__ import annotations

import logging
import math
from datetime import date, timedelta
from typing import Any

import polars as pl
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from quant.db import AsyncSessionLocal
from quant.db.models import Feature, OHLCVDaily
from quant.features.technical import FEATURE_COLUMNS, FEATURE_SET_VERSION, add_technical_features

log = logging.getLogger("quant.features.build")

# Longest lookback any feature needs (200-day SMA). Plus a buffer for safety.
WARMUP_DAYS = 260


async def _load_ohlcv(session: AsyncSession, symbols: list[str], start: date, end: date) -> pl.DataFrame:
    stmt = (
        select(
            OHLCVDaily.date,
            OHLCVDaily.symbol,
            OHLCVDaily.open,
            OHLCVDaily.high,
            OHLCVDaily.low,
            OHLCVDaily.close,
            OHLCVDaily.volume,
            OHLCVDaily.adj_close,
        )
        .where(OHLCVDaily.symbol.in_(symbols))
        .where(OHLCVDaily.date >= start)
        .where(OHLCVDaily.date <= end)
        .order_by(OHLCVDaily.symbol, OHLCVDaily.date)
    )
    rows = (await session.execute(stmt)).all()
    if not rows:
        return pl.DataFrame(
            schema={
                "date": pl.Date,
                "symbol": pl.Utf8,
                "open": pl.Float64,
                "high": pl.Float64,
                "low": pl.Float64,
                "close": pl.Float64,
                "volume": pl.Int64,
                "adj_close": pl.Float64,
            }
        )
    return pl.DataFrame(
        {
            "date": [r.date for r in rows],
            "symbol": [r.symbol for r in rows],
            "open": [float(r.open) for r in rows],
            "high": [float(r.high) for r in rows],
            "low": [float(r.low) for r in rows],
            "close": [float(r.close) for r in rows],
            "volume": [int(r.volume) for r in rows],
            "adj_close": [float(r.adj_close) for r in rows],
        }
    )


def _row_to_feature_dict(row: dict[str, Any]) -> dict[str, float] | None:
    """Extract the FEATURE_COLUMNS subset; return None if any are null/NaN."""
    out: dict[str, float] = {}
    for c in FEATURE_COLUMNS:
        v = row.get(c)
        if v is None:
            return None
        fv = float(v)
        if math.isnan(fv) or math.isinf(fv):
            return None
        out[c] = fv
    return out


async def build_features(
    symbols: list[str],
    *,
    start: date,
    end: date,
    session: AsyncSession | None = None,
) -> int:
    """Compute + persist features for [start, end]. Returns number of rows upserted."""
    own_session = session is None
    sess = session or AsyncSessionLocal()
    try:
        load_start = start - timedelta(days=WARMUP_DAYS)
        raw = await _load_ohlcv(sess, symbols, load_start, end)
        if raw.is_empty():
            log.warning("no OHLCV found for %d symbols in [%s, %s]", len(symbols), start, end)
            return 0

        enriched = add_technical_features(raw)

        # Keep only target window (drop warmup) and only rows with complete features.
        target = enriched.filter((pl.col("date") >= start) & (pl.col("date") <= end))

        records: list[dict[str, Any]] = []
        for row in target.to_dicts():
            feats = _row_to_feature_dict(row)
            if feats is None:
                continue
            records.append(
                {
                    "date": row["date"],
                    "symbol": row["symbol"],
                    "feature_set_version": FEATURE_SET_VERSION,
                    "features": feats,
                    "point_in_time_safe": True,
                }
            )

        if not records:
            log.warning("no complete feature rows for [%s, %s]", start, end)
            return 0

        stmt = pg_insert(Feature).values(records)
        stmt = stmt.on_conflict_do_update(
            index_elements=["date", "symbol", "feature_set_version"],
            set_={
                "features": stmt.excluded.features,
                "point_in_time_safe": stmt.excluded.point_in_time_safe,
            },
        )
        await sess.execute(stmt)
        await sess.commit()
        log.info(
            "upserted %d feature rows across %d symbols for [%s, %s]",
            len(records),
            len(symbols),
            start,
            end,
        )
        return len(records)
    finally:
        if own_session:
            await sess.close()
