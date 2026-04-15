"""
News ingest — fans out across Polygon, Marketaux, Tiingo, Finnhub, NewsAPI.

For each provider:
1. Fetch articles (per-symbol or global window).
2. Normalize into NewsArticle rows.
3. Upsert on (source, provider_id). Sentiment scoring is a separate step
   (see quant.ingest.sentiment — Sprint 3).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from quant.adapters.finnhub import FinnhubAdapter
from quant.adapters.marketaux import MarketauxAdapter
from quant.adapters.newsapi import NewsApiAdapter
from quant.adapters.polygon import PolygonAdapter
from quant.adapters.tiingo import TiingoAdapter
from quant.db import AsyncSessionLocal
from quant.db.models import NewsArticle

log = logging.getLogger("quant.ingest.news")


# ------------------------------------------------------------------
# Normalizers — each returns a NewsArticle row dict or None
# ------------------------------------------------------------------
def _iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _polygon_row(r: dict[str, Any]) -> dict[str, Any] | None:
    pub = _iso(r.get("published_utc"))
    if not pub or not r.get("id") or not r.get("article_url"):
        return None
    return {
        "source": "polygon",
        "provider_id": r["id"],
        "url": r["article_url"],
        "title": r.get("title") or "",
        "description": r.get("description"),
        "published_at": pub,
        "symbols": list(r.get("tickers") or []),
    }


def _tiingo_row(r: dict[str, Any]) -> dict[str, Any] | None:
    pub = _iso(r.get("publishedDate") or r.get("crawlDate"))
    if not pub or not r.get("id") or not r.get("url"):
        return None
    return {
        "source": "tiingo",
        "provider_id": str(r["id"]),
        "url": r["url"],
        "title": r.get("title") or "",
        "description": r.get("description"),
        "published_at": pub,
        "symbols": [t.upper() for t in (r.get("tickers") or [])],
    }


def _marketaux_row(r: dict[str, Any]) -> dict[str, Any] | None:
    pub = _iso(r.get("published_at"))
    if not pub or not r.get("uuid") or not r.get("url"):
        return None
    syms = [e.get("symbol") for e in (r.get("entities") or []) if e.get("symbol")]
    return {
        "source": "marketaux",
        "provider_id": r["uuid"],
        "url": r["url"],
        "title": r.get("title") or "",
        "description": r.get("description"),
        "published_at": pub,
        "symbols": syms,
    }


def _finnhub_row(r: dict[str, Any], symbol: str) -> dict[str, Any] | None:
    ts = r.get("datetime")
    if not ts or not r.get("id") or not r.get("url"):
        return None
    pub = datetime.fromtimestamp(int(ts), tz=UTC)
    return {
        "source": "finnhub",
        "provider_id": str(r["id"]),
        "url": r["url"],
        "title": r.get("headline") or "",
        "description": r.get("summary"),
        "published_at": pub,
        "symbols": [symbol],
    }


def _newsapi_row(r: dict[str, Any]) -> dict[str, Any] | None:
    pub = _iso(r.get("publishedAt"))
    url = r.get("url")
    if not pub or not url:
        return None
    return {
        "source": "newsapi",
        "provider_id": url,  # NewsAPI has no stable ID — URL is the natural key
        "url": url,
        "title": r.get("title") or "",
        "description": r.get("description"),
        "published_at": pub,
        "symbols": [],
    }


# ------------------------------------------------------------------
# Upsert helper
# ------------------------------------------------------------------
async def _upsert(db: AsyncSession, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(NewsArticle).values(rows)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_news_source_providerid",
        set_={
            "title": stmt.excluded.title,
            "description": stmt.excluded.description,
            "url": stmt.excluded.url,
            "symbols": stmt.excluded.symbols,
        },
    )
    await db.execute(stmt)
    return len(rows)


# ------------------------------------------------------------------
# Orchestrator — run all providers within a recent window
# ------------------------------------------------------------------
async def ingest_news(
    *,
    symbols: list[str],
    lookback_hours: int = 24,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    since = datetime.now(UTC) - timedelta(hours=lookback_hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    today = date.today()
    yday = today - timedelta(days=1)

    owns = session is None
    db = session or AsyncSessionLocal()
    counts: dict[str, int] = {}
    try:
        # --- Polygon: per-symbol ---
        async with PolygonAdapter() as poly:
            rows: list[dict[str, Any]] = []
            for sym in symbols:
                try:
                    arts = await poly.news(ticker=sym, published_gte=since_iso, limit=50)
                except Exception as e:  # noqa: BLE001
                    log.warning("polygon news failed for %s: %s", sym, e)
                    continue
                for a in arts:
                    row = _polygon_row(a)
                    if row:
                        rows.append(row)
            counts["polygon"] = await _upsert(db, rows)

        # --- Tiingo: batch endpoint across the universe ---
        try:
            async with TiingoAdapter() as t:
                arts = await t.news(tickers=symbols, limit=500)
            rows = [r for a in arts if (r := _tiingo_row(a))]
            counts["tiingo"] = await _upsert(db, rows)
        except Exception as e:  # noqa: BLE001
            log.warning("tiingo news failed: %s", e)
            counts["tiingo"] = 0

        # --- Marketaux: low rate limit, chunked ---
        try:
            async with MarketauxAdapter() as m:
                arts = await m.news(symbols=symbols[:25], published_after=since_iso, limit=3)
            rows = [r for a in arts if (r := _marketaux_row(a))]
            counts["marketaux"] = await _upsert(db, rows)
        except Exception as e:  # noqa: BLE001
            log.warning("marketaux news failed: %s", e)
            counts["marketaux"] = 0

        # --- Finnhub: per-symbol for the window ---
        try:
            async with FinnhubAdapter() as f:
                rows = []
                for sym in symbols:
                    try:
                        arts = await f.company_news(sym, start=yday, end=today)
                    except Exception:  # noqa: BLE001
                        continue
                    for a in arts:
                        row = _finnhub_row(a, sym)
                        if row:
                            rows.append(row)
                counts["finnhub"] = await _upsert(db, rows)
        except Exception as e:  # noqa: BLE001
            log.warning("finnhub news failed: %s", e)
            counts["finnhub"] = 0

        # --- NewsAPI: optional, query by top symbols ---
        try:
            async with NewsApiAdapter() as n:
                arts = await n.top_headlines(category="business", country="us", page_size=50)
            rows = [r for a in arts if (r := _newsapi_row(a))]
            counts["newsapi"] = await _upsert(db, rows)
        except Exception as e:  # noqa: BLE001
            log.info("newsapi skipped: %s", e)
            counts["newsapi"] = 0

        await db.commit()
    finally:
        if owns:
            await db.close()
    return counts
