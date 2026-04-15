"""
OHLCV daily-bar ingest.

Strategy:
1. Primary source = Polygon (/v2/aggs). Returns adjusted bars.
2. Fallback on provider failure = Tiingo /tiingo/daily/{sym}/prices (uses adjClose).
3. Last-resort = Alpha Vantage TIME_SERIES_DAILY_ADJUSTED.

Writes to `public.ohlcv_daily` (Timescale hypertable) via UPSERT on
(date, symbol). Idempotent — safe to re-run for the same window.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from quant.adapters.alphavantage import AlphaVantageAdapter
from quant.adapters.exceptions import AdapterError
from quant.adapters.polygon import PolygonAdapter
from quant.adapters.tiingo import TiingoAdapter
from quant.db import AsyncSessionLocal
from quant.db.models import OHLCVDaily

log = logging.getLogger("quant.ingest.ohlcv")


# ------------------------------------------------------------------
# Source adapters — each returns a uniform list of dicts:
#   {date, open, high, low, close, adj_close, volume, vwap, source}
# ------------------------------------------------------------------
def _polygon_row(raw: dict[str, Any]) -> dict[str, Any]:
    ts = datetime.fromtimestamp(raw["t"] / 1000).date()
    close = Decimal(str(raw["c"]))
    return {
        "date": ts,
        "open": Decimal(str(raw["o"])),
        "high": Decimal(str(raw["h"])),
        "low": Decimal(str(raw["l"])),
        "close": close,
        "adj_close": close,  # Polygon v2 aggs are already split+div adjusted when adjusted=true
        "volume": int(raw["v"]),
        "vwap": Decimal(str(raw["vw"])) if raw.get("vw") is not None else None,
        "trade_count": int(raw["n"]) if raw.get("n") is not None else None,
        "source": "polygon",
    }


def _tiingo_row(raw: dict[str, Any]) -> dict[str, Any]:
    d = raw["date"][:10]
    return {
        "date": date.fromisoformat(d),
        "open": Decimal(str(raw["open"])),
        "high": Decimal(str(raw["high"])),
        "low": Decimal(str(raw["low"])),
        "close": Decimal(str(raw["close"])),
        "adj_close": Decimal(str(raw["adjClose"])),
        "volume": int(raw["volume"]),
        "vwap": None,
        "trade_count": None,
        "source": "tiingo",
    }


def _alphavantage_row(dt: str, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": date.fromisoformat(dt),
        "open": Decimal(raw["1. open"]),
        "high": Decimal(raw["2. high"]),
        "low": Decimal(raw["3. low"]),
        "close": Decimal(raw["4. close"]),
        "adj_close": Decimal(raw["5. adjusted close"]),
        "volume": int(raw["6. volume"]),
        "vwap": None,
        "trade_count": None,
        "source": "alphavantage",
    }


# ------------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------------
async def _fetch_bars(symbol: str, start: date, end: date) -> list[dict[str, Any]]:
    last_err: Exception | None = None
    try:
        async with PolygonAdapter() as poly:
            rows = await poly.daily_bars(symbol, start, end, adjusted=True)
        if rows:
            return [_polygon_row(r) for r in rows]
    except AdapterError as e:
        last_err = e
        log.warning("polygon failed for %s (%s → %s): %s", symbol, start, end, e)

    try:
        async with TiingoAdapter() as t:
            rows = await t.daily_prices(symbol, start=start, end=end)
        if rows:
            return [_tiingo_row(r) for r in rows]
    except AdapterError as e:
        last_err = e
        log.warning("tiingo failed for %s: %s", symbol, e)

    try:
        async with AlphaVantageAdapter() as av:
            ts = await av.daily_adjusted(symbol, full=True)
        if ts:
            out = []
            for dt, raw in ts.items():
                d = date.fromisoformat(dt)
                if start <= d <= end:
                    out.append(_alphavantage_row(dt, raw))
            out.sort(key=lambda r: r["date"])
            if out:
                return out
    except AdapterError as e:
        last_err = e
        log.warning("alphavantage failed for %s: %s", symbol, e)

    if last_err:
        raise last_err
    return []


async def _upsert_bars(db: AsyncSession, symbol: str, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    for r in rows:
        r["symbol"] = symbol
    stmt = pg_insert(OHLCVDaily).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[OHLCVDaily.date, OHLCVDaily.symbol],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adj_close": stmt.excluded.adj_close,
            "volume": stmt.excluded.volume,
            "vwap": stmt.excluded.vwap,
            "trade_count": stmt.excluded.trade_count,
            "source": stmt.excluded.source,
        },
    )
    await db.execute(stmt)
    return len(rows)


async def backfill_ohlcv_daily(
    symbols: list[str],
    *,
    start: date,
    end: date | None = None,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """
    Idempotent backfill for the given window. Returns {symbol: row_count}.
    """
    end = end or date.today() - timedelta(days=1)
    owns = session is None
    db = session or AsyncSessionLocal()
    result: dict[str, int] = {}
    try:
        for i, sym in enumerate(symbols, 1):
            try:
                rows = await _fetch_bars(sym, start, end)
                n = await _upsert_bars(db, sym, rows)
                result[sym] = n
                if i % 10 == 0:
                    await db.commit()
                    log.info("ohlcv backfill: %d / %d  (last=%s, rows=%d)", i, len(symbols), sym, n)
            except Exception as e:  # noqa: BLE001 — keep going per-symbol
                log.exception("ohlcv backfill failed for %s: %s", sym, e)
                result[sym] = 0
        await db.commit()
    finally:
        if owns:
            await db.close()
    return result
