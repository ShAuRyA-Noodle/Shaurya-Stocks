"""
Corporate actions (splits + dividends) ingest via Polygon.

Idempotent upsert on (symbol, ex_date, action_type).
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from quant.adapters.polygon import PolygonAdapter
from quant.db import AsyncSessionLocal
from quant.db.models import CorporateAction

log = logging.getLogger("quant.ingest.corp_actions")


def _split_row(symbol: str, r: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "action_type": "split",
        "ex_date": date.fromisoformat(r["execution_date"]),
        "ratio": Decimal(str(r["split_to"])) / Decimal(str(r["split_from"])),
        "cash_amount": None,
        "currency": "USD",
    }


def _div_row(symbol: str, r: dict[str, Any]) -> dict[str, Any]:
    ex_date = r.get("ex_dividend_date")
    if not ex_date:
        return {}
    return {
        "symbol": symbol,
        "action_type": "dividend",
        "ex_date": date.fromisoformat(ex_date),
        "record_date": date.fromisoformat(r["record_date"]) if r.get("record_date") else None,
        "pay_date": date.fromisoformat(r["pay_date"]) if r.get("pay_date") else None,
        "ratio": None,
        "cash_amount": Decimal(str(r["cash_amount"])) if r.get("cash_amount") is not None else None,
        "currency": r.get("currency") or "USD",
    }


async def ingest_corporate_actions(
    symbols: list[str],
    *,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    owns = session is None
    db = session or AsyncSessionLocal()
    counts: dict[str, int] = {}
    try:
        async with PolygonAdapter() as poly:
            for i, sym in enumerate(symbols, 1):
                try:
                    splits = await poly.splits(sym)
                    divs = await poly.dividends(sym)
                except Exception as e:
                    log.warning("corp actions fetch failed for %s: %s", sym, e)
                    counts[sym] = 0
                    continue

                rows: list[dict[str, Any]] = [_split_row(sym, r) for r in splits]
                rows.extend([r for r in (_div_row(sym, d) for d in divs) if r])
                if not rows:
                    counts[sym] = 0
                    continue

                stmt = (
                    pg_insert(CorporateAction)
                    .values(rows)
                    .on_conflict_do_nothing(constraint="uq_corp_action")
                )
                await db.execute(stmt)
                counts[sym] = len(rows)

                if i % 20 == 0:
                    await db.commit()
                    log.info("corp actions: %d / %d", i, len(symbols))
        await db.commit()
    finally:
        if owns:
            await db.close()
    return counts
