"""
Portfolio reconciliation.

Two jobs:
1. `mark_to_market(user_id, marks)` — update last_mark_price + unrealized_pnl on
   every open position using the latest quotes.
2. `end_of_day_snapshot(user_id)` — roll up cash + positions into one daily
   Snapshot row. Idempotent on (date, user_id).

We don't try to be clever — positions are driven by Trade rows (portfolio.trades).
A filled BUY adds/extends; a filled SELL reduces/closes.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from quant.db.models import OrderSide, Position, Snapshot, Trade


async def mark_to_market(
    session: AsyncSession, user_id: uuid.UUID, marks: Mapping[str, Decimal]
) -> int:
    """Set last_mark_price and unrealized_pnl on open positions. Returns rows updated."""
    stmt = select(Position).where(Position.user_id == user_id)
    positions = (await session.execute(stmt)).scalars().all()
    now = datetime.now(UTC)
    updated = 0
    for p in positions:
        m = marks.get(p.symbol)
        if m is None:
            continue
        p.last_mark_price = m
        p.last_mark_at = now
        sign = Decimal("1") if p.side == OrderSide.buy else Decimal("-1")
        p.unrealized_pnl = sign * (m - p.avg_entry_price) * p.quantity
        updated += 1
    await session.commit()
    return updated


async def end_of_day_snapshot(
    session: AsyncSession, user_id: uuid.UUID, *, cash: Decimal, as_of: date | None = None
) -> Snapshot:
    as_of = as_of or date.today()
    stmt = select(Position).where(Position.user_id == user_id)
    positions = (await session.execute(stmt)).scalars().all()

    positions_value = Decimal("0")
    unrealized = Decimal("0")
    gross = Decimal("0")
    net = Decimal("0")
    for p in positions:
        mark = p.last_mark_price or p.avg_entry_price
        signed_qty = p.quantity if p.side == OrderSide.buy else -p.quantity
        value = mark * signed_qty
        positions_value += mark * p.quantity  # absolute value
        unrealized += p.unrealized_pnl
        gross += abs(value)
        net += value

    # Realized PnL (cumulative) = sum of all filled trades' realized_pnl.
    stmt_pnl = select(Trade.realized_pnl).where(Trade.user_id == user_id)
    pnl_rows = (await session.execute(stmt_pnl)).scalars().all()
    realized_cum = sum((Decimal(str(v)) for v in pnl_rows), Decimal("0"))

    total_equity = cash + positions_value
    row = {
        "date": as_of,
        "user_id": user_id,
        "cash": cash,
        "positions_value": positions_value,
        "total_equity": total_equity,
        "realized_pnl_cum": realized_cum,
        "unrealized_pnl": unrealized,
        "num_positions": len(positions),
        "gross_exposure": gross,
        "net_exposure": net,
    }
    stmt_up = pg_insert(Snapshot).values(**row)
    stmt_up = stmt_up.on_conflict_do_update(
        index_elements=["date", "user_id"],
        set_={k: stmt_up.excluded[k] for k in row if k not in ("date", "user_id")},
    )
    await session.execute(stmt_up)
    await session.commit()
    snap = await session.get(Snapshot, {"date": as_of, "user_id": user_id})
    assert snap is not None
    return snap
