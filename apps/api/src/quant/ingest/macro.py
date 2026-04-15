"""
Macro series ingest from FRED.

Upserts MacroSeries metadata + MacroObservation rows. Idempotent.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from quant.adapters.fred import MACRO_SERIES, FredAdapter
from quant.db import AsyncSessionLocal
from quant.db.models import MacroObservation, MacroSeries

log = logging.getLogger("quant.ingest.macro")

# Series we actually ingest (alias → FRED id)
CANONICAL_SERIES: dict[str, str] = {
    "VIXCLS": "VIXCLS",
    "DGS10": "DGS10",
    "DGS2": "DGS2",
    "DGS3MO": "DGS3MO",
    "DTWEXBGS": "DTWEXBGS",
    "T10Y2Y": "T10Y2Y",
    "T10YIE": "T10YIE",
    "UNRATE": "UNRATE",
    "CPIAUCSL": "CPIAUCSL",
    "FEDFUNDS": "FEDFUNDS",
    "BAMLH0A0HYM2": "BAMLH0A0HYM2",
}


def _parse_value(raw: Any) -> Decimal | None:
    if raw is None or raw == "." or raw == "":
        return None
    try:
        return Decimal(str(raw))
    except (InvalidOperation, ValueError):
        return None


async def ingest_macro_series(
    series_ids: list[str] | None = None,
    *,
    start: date | None = None,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """Fetches each series in full (FRED is cheap) and upserts observations."""
    ids = series_ids or list(CANONICAL_SERIES.values())
    owns = session is None
    db = session or AsyncSessionLocal()
    counts: dict[str, int] = {}
    try:
        async with FredAdapter() as fred:
            for sid in ids:
                try:
                    info = await fred.series_info(sid)
                except Exception as e:
                    log.warning("fred series_info failed for %s: %s", sid, e)
                    continue

                if info:
                    title = info.get("title") or MACRO_SERIES.get(sid, sid)
                    stmt = pg_insert(MacroSeries).values(
                        series_id=sid,
                        title=title,
                        units=info.get("units"),
                        frequency=info.get("frequency_short"),
                        category=info.get("seasonal_adjustment_short"),
                        last_updated=None,
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[MacroSeries.series_id],
                        set_={
                            "title": stmt.excluded.title,
                            "units": stmt.excluded.units,
                            "frequency": stmt.excluded.frequency,
                            "category": stmt.excluded.category,
                        },
                    )
                    await db.execute(stmt)

                try:
                    obs = await fred.observations(sid, start=start)
                except Exception as e:
                    log.warning("fred obs failed for %s: %s", sid, e)
                    counts[sid] = 0
                    continue

                rows = []
                for o in obs:
                    v = _parse_value(o.get("value"))
                    if v is None:
                        continue
                    try:
                        d = date.fromisoformat(o["date"])
                    except (KeyError, ValueError):
                        continue
                    rows.append({"date": d, "series_id": sid, "value": v})

                if rows:
                    stmt = pg_insert(MacroObservation).values(rows)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=[MacroObservation.date, MacroObservation.series_id],
                        set_={"value": stmt.excluded.value},
                    )
                    await db.execute(stmt)
                counts[sid] = len(rows)
                log.info("macro %s: %d obs", sid, len(rows))
                await db.commit()
    finally:
        if owns:
            await db.close()
    return counts
