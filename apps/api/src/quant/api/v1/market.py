"""
Market data read endpoints — OHLCV bars, latest quote, macro series, news.

All reads are gated by auth so we can attribute usage per user.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quant.core.dependencies import get_current_user, get_db
from quant.db.models import (
    MacroObservation,
    MacroSeries,
    NewsArticle,
    OHLCVDaily,
    Ticker,
    User,
)

router = APIRouter(tags=["market"])


# ---------------- schemas ----------------
class BarOut(BaseModel):
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    adj_close: Decimal
    volume: int


class LatestBarOut(BaseModel):
    symbol: str
    bar: BarOut | None


class TickerOut(BaseModel):
    symbol: str
    name: str | None
    sector: str | None
    industry: str | None
    exchange: str | None
    is_active: bool


class MacroObsOut(BaseModel):
    series_id: str
    title: str | None
    date: date
    value: Decimal | None


class NewsOut(BaseModel):
    id: str
    symbols: list[str]
    published_at: datetime
    title: str
    url: str
    source: str
    sentiment_score: Decimal | None
    sentiment_label: str | None


# ---------------- endpoints ----------------
@router.get("/tickers", response_model=list[TickerOut])
async def list_tickers(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    active_only: bool = Query(True),
    limit: int = Query(500, ge=1, le=5000),
) -> list[TickerOut]:
    stmt = select(Ticker).order_by(Ticker.symbol).limit(limit)
    if active_only:
        stmt = stmt.where(Ticker.is_active.is_(True))
    rows = (await db.execute(stmt)).scalars().all()
    return [
        TickerOut(
            symbol=t.symbol,
            name=t.name,
            sector=t.sector,
            industry=t.industry,
            exchange=t.exchange,
            is_active=t.is_active,
        )
        for t in rows
    ]


@router.get("/bars/{symbol}", response_model=list[BarOut])
async def bars(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    start: date | None = Query(None),
    end: date | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
) -> list[BarOut]:
    sym = symbol.upper()
    end = end or date.today()
    start = start or (end - timedelta(days=365))
    stmt = (
        select(OHLCVDaily)
        .where(OHLCVDaily.symbol == sym, OHLCVDaily.date >= start, OHLCVDaily.date <= end)
        .order_by(OHLCVDaily.date)
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [
        BarOut(
            date=r.date,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            adj_close=r.adj_close,
            volume=r.volume,
        )
        for r in rows
    ]


@router.get("/bars/{symbol}/latest", response_model=LatestBarOut)
async def latest_bar(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LatestBarOut:
    sym = symbol.upper()
    stmt = select(OHLCVDaily).where(OHLCVDaily.symbol == sym).order_by(OHLCVDaily.date.desc()).limit(1)
    r = (await db.execute(stmt)).scalar_one_or_none()
    bar = (
        BarOut(
            date=r.date,
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            adj_close=r.adj_close,
            volume=r.volume,
        )
        if r is not None
        else None
    )
    return LatestBarOut(symbol=sym, bar=bar)


@router.get("/macro/{series_id}", response_model=list[MacroObsOut])
async def macro_observations(
    series_id: str,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    start: date | None = Query(None),
    end: date | None = Query(None),
) -> list[MacroObsOut]:
    sid = series_id.upper()
    series = (await db.execute(select(MacroSeries).where(MacroSeries.series_id == sid))).scalar_one_or_none()
    if series is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"series {sid} not found")

    end = end or date.today()
    start = start or (end - timedelta(days=3 * 365))
    stmt = (
        select(MacroObservation)
        .where(
            MacroObservation.series_id == sid,
            MacroObservation.date >= start,
            MacroObservation.date <= end,
        )
        .order_by(MacroObservation.date)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [MacroObsOut(series_id=sid, title=series.title, date=r.date, value=r.value) for r in rows]


@router.get("/news", response_model=list[NewsOut])
async def news(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
    symbol: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> list[NewsOut]:
    from sqlalchemy.dialects.postgresql import JSONB  # noqa: F401 — gin index hint only

    stmt = select(NewsArticle).order_by(NewsArticle.published_at.desc()).limit(limit)
    if symbol:
        # JSONB array containment: symbols @> '["AAPL"]'
        stmt = stmt.where(NewsArticle.symbols.contains([symbol.upper()]))
    rows = (await db.execute(stmt)).scalars().all()
    return [
        NewsOut(
            id=str(r.id),
            symbols=list(r.symbols or []),
            published_at=r.published_at,
            title=r.title,
            url=r.url,
            source=r.source,
            sentiment_score=r.sentiment_score,
            sentiment_label=r.sentiment_label,
        )
        for r in rows
    ]
