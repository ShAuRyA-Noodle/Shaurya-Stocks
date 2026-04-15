"""
Order + portfolio endpoints.

POST   /orders           — submit an order (risk-checked, routed to broker)
GET    /orders           — list the user's trades (paginated)
GET    /orders/{id}      — single trade
DELETE /orders/{id}      — cancel (if still cancellable)
GET    /positions        — open positions
GET    /account          — cash + equity + exposure (latest snapshot)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quant.core.dependencies import get_current_user, get_db
from quant.db.models import OrderSide, OrderStatus, Position, Snapshot, Trade, User
from quant.execution import AlpacaBroker, Broker, OrderService
from quant.risk import OrderIntent

router = APIRouter(tags=["trading"])


# ---------------- schemas ----------------
class OrderIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    side: Literal["BUY", "SELL"]
    quantity: Decimal = Field(gt=Decimal("0"))
    limit_price: Decimal | None = Field(default=None, gt=Decimal("0"))
    mark_price: Decimal = Field(gt=Decimal("0"))  # last quote, client-provided
    order_type: Literal["market", "limit"] = "market"


class TradeOut(BaseModel):
    id: uuid.UUID
    symbol: str
    side: OrderSide
    status: OrderStatus
    quantity: Decimal
    filled_quantity: Decimal
    limit_price: Decimal | None
    fill_price: Decimal | None
    trade_date: date
    submitted_at: datetime | None
    filled_at: datetime | None
    broker_order_id: str | None
    client_order_id: str

    @classmethod
    def from_orm_trade(cls, t: Trade) -> TradeOut:
        return cls(
            id=t.id,
            symbol=t.symbol,
            side=t.side,
            status=t.status,
            quantity=t.quantity,
            filled_quantity=t.filled_quantity,
            limit_price=t.limit_price,
            fill_price=t.fill_price,
            trade_date=t.trade_date,
            submitted_at=t.submitted_at,
            filled_at=t.filled_at,
            broker_order_id=t.broker_order_id,
            client_order_id=t.client_order_id,
        )


class PositionOut(BaseModel):
    symbol: str
    side: OrderSide
    quantity: Decimal
    avg_entry_price: Decimal
    last_mark_price: Decimal | None
    unrealized_pnl: Decimal
    entry_date: date


class AccountOut(BaseModel):
    date: date
    cash: Decimal
    positions_value: Decimal
    total_equity: Decimal
    realized_pnl_cum: Decimal
    unrealized_pnl: Decimal
    num_positions: int
    gross_exposure: Decimal
    net_exposure: Decimal


# ---------------- broker dependency ----------------
_broker_singleton: Broker | None = None


def get_broker() -> Broker:
    global _broker_singleton
    if _broker_singleton is None:
        _broker_singleton = AlpacaBroker()
    return _broker_singleton


# ---------------- endpoints ----------------
@router.post("/orders", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
async def place_order(
    payload: OrderIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    broker: Broker = Depends(get_broker),
) -> TradeOut:
    svc = OrderService(db, broker)
    intent = OrderIntent(
        user_id=str(user.id),
        symbol=payload.symbol.upper(),
        side=payload.side,
        quantity=payload.quantity,
        limit_price=payload.limit_price,
        mark_price=payload.mark_price,
    )
    trade = await svc.place(intent, order_type=payload.order_type)
    if trade.status == OrderStatus.rejected:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "order rejected")
    return TradeOut.from_orm_trade(trade)


@router.get("/orders", response_model=list[TradeOut])
async def list_orders(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[TradeOut]:
    stmt = (
        select(Trade)
        .where(Trade.user_id == user.id)
        .order_by(Trade.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [TradeOut.from_orm_trade(t) for t in rows]


@router.get("/orders/{trade_id}", response_model=TradeOut)
async def get_order(
    trade_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TradeOut:
    t = await db.get(Trade, trade_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "trade not found")
    return TradeOut.from_orm_trade(t)


@router.delete("/orders/{trade_id}", response_model=TradeOut)
async def cancel_order(
    trade_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    broker: Broker = Depends(get_broker),
) -> TradeOut:
    t = await db.get(Trade, trade_id)
    if t is None or t.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "trade not found")
    svc = OrderService(db, broker)
    t = await svc.cancel(trade_id)
    return TradeOut.from_orm_trade(t)


@router.get("/positions", response_model=list[PositionOut])
async def list_positions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PositionOut]:
    stmt = select(Position).where(Position.user_id == user.id).order_by(Position.symbol)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        PositionOut(
            symbol=p.symbol,
            side=p.side,
            quantity=p.quantity,
            avg_entry_price=p.avg_entry_price,
            last_mark_price=p.last_mark_price,
            unrealized_pnl=p.unrealized_pnl,
            entry_date=p.entry_date,
        )
        for p in rows
    ]


@router.get("/account", response_model=AccountOut)
async def get_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AccountOut:
    stmt = (
        select(Snapshot)
        .where(Snapshot.user_id == user.id)
        .order_by(Snapshot.date.desc())
        .limit(1)
    )
    s = (await db.execute(stmt)).scalar_one_or_none()
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no snapshots yet — trade first")
    return AccountOut(
        date=s.date,
        cash=s.cash,
        positions_value=s.positions_value,
        total_equity=s.total_equity,
        realized_pnl_cum=s.realized_pnl_cum,
        unrealized_pnl=s.unrealized_pnl,
        num_positions=s.num_positions,
        gross_exposure=s.gross_exposure,
        net_exposure=s.net_exposure,
    )
