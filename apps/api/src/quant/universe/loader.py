"""
Bootstrap the universe: upsert Ticker rows + record universe membership.

Flow:
1. Fetch SP500 + NDX100 constituents from public sources.
2. Upsert each into `market.tickers` (name/sector/industry from the source).
3. Optionally enrich with Polygon `ticker_details` (exchange, country, listed_at).
4. Insert into `market.universe_membership` with effective_from=today,
   effective_to=NULL — i.e. currently a member. Historical PIT rows should
   come from a vendor feed later; this loader is idempotent and safe to rerun.

Usage:
    from quant.universe import bootstrap_universe
    await bootstrap_universe(enrich_with_polygon=False)
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from quant.adapters.polygon import PolygonAdapter
from quant.db import AsyncSessionLocal
from quant.db.models import Ticker, UniverseMembership
from quant.universe.constituents import fetch_ndx100, fetch_sp500

log = logging.getLogger("quant.universe")


async def _upsert_tickers(db: AsyncSession, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    stmt = pg_insert(Ticker).values([
        {
            "symbol": r["symbol"],
            "name": r.get("name") or None,
            "sector": r.get("sector") or None,
            "industry": r.get("industry") or None,
            "asset_class": "equity",
            "currency": "USD",
        }
        for r in rows
    ])
    stmt = stmt.on_conflict_do_update(
        index_elements=[Ticker.symbol],
        set_={
            "name": stmt.excluded.name,
            "sector": stmt.excluded.sector,
            "industry": stmt.excluded.industry,
            "updated_at": datetime.now(UTC),
        },
    )
    await db.execute(stmt)


async def _record_membership(
    db: AsyncSession, universe: str, symbols: list[str], effective_from: date
) -> None:
    if not symbols:
        return
    # Insert-if-absent: the (universe, symbol, effective_from) unique constraint
    # makes this idempotent.
    stmt = pg_insert(UniverseMembership).values([
        {"universe": universe, "symbol": s, "effective_from": effective_from}
        for s in symbols
    ]).on_conflict_do_nothing(constraint="uq_universe_member")
    await db.execute(stmt)


async def _enrich_with_polygon(db: AsyncSession, symbols: list[str]) -> None:
    """Fill in exchange + listed_at + country from Polygon ticker_details."""
    async with PolygonAdapter() as poly:
        for sym in symbols:
            try:
                info = await poly.ticker_details(sym)
            except Exception as e:  # noqa: BLE001 — enrichment is best-effort
                log.warning("polygon enrichment failed for %s: %s", sym, e)
                continue
            if not info:
                continue
            t = await db.get(Ticker, sym)
            if t is None:
                continue
            t.exchange = info.get("primary_exchange") or t.exchange
            t.country = (info.get("locale") or "us")[:8]
            listed = info.get("list_date")
            if listed:
                try:
                    t.listed_at = date.fromisoformat(listed)
                except ValueError:
                    pass


async def bootstrap_universe(
    *,
    enrich_with_polygon: bool = False,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """
    Idempotent bootstrap. Returns {"sp500": N, "ndx100": M, "unique": U}.
    """
    sp500 = await fetch_sp500()
    ndx100 = await fetch_ndx100()

    log.info("fetched %d SP500 symbols, %d NDX100 symbols", len(sp500), len(ndx100))
    if len(sp500) < 450:
        raise RuntimeError(f"SP500 fetch returned only {len(sp500)} rows — source may be stale")
    if len(ndx100) < 90:
        raise RuntimeError(f"NDX100 fetch returned only {len(ndx100)} rows — source may be stale")

    # Merge by symbol, NDX100 entries don't overwrite SP500 sector if SP500 had it
    by_symbol: dict[str, dict[str, str]] = {r["symbol"]: dict(r) for r in sp500}
    for r in ndx100:
        if r["symbol"] not in by_symbol:
            by_symbol[r["symbol"]] = dict(r)
    all_rows = list(by_symbol.values())

    today = date.today()
    owns_session = session is None
    db = session or AsyncSessionLocal()
    try:
        await _upsert_tickers(db, all_rows)
        await _record_membership(db, "SP500", [r["symbol"] for r in sp500], today)
        await _record_membership(db, "NDX100", [r["symbol"] for r in ndx100], today)
        await db.commit()

        if enrich_with_polygon:
            await _enrich_with_polygon(db, [r["symbol"] for r in all_rows])
            await db.commit()
    finally:
        if owns_session:
            await db.close()

    return {"sp500": len(sp500), "ndx100": len(ndx100), "unique": len(all_rows)}


async def active_universe_symbols(
    universe: str, *, as_of: date | None = None, session: AsyncSession | None = None
) -> list[str]:
    """Symbols that were members of `universe` on `as_of` (defaults to today)."""
    as_of = as_of or date.today()
    owns = session is None
    db = session or AsyncSessionLocal()
    try:
        stmt = select(UniverseMembership.symbol).where(
            UniverseMembership.universe == universe,
            UniverseMembership.effective_from <= as_of,
            (UniverseMembership.effective_to.is_(None))
            | (UniverseMembership.effective_to > as_of),
        ).distinct()
        rows = (await db.execute(stmt)).scalars().all()
        return sorted(set(rows))
    finally:
        if owns:
            await db.close()
