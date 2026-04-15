"""
Order service — takes an intent, runs risk checks, submits to broker,
persists the Trade row, and returns the resulting order state.

State machine:
    PENDING → (risk block)        → REJECTED
    PENDING → (broker accept)     → SUBMITTED
    SUBMITTED → (broker fill)     → PARTIAL → FILLED
    SUBMITTED → (user cancel)     → CANCELLED
    SUBMITTED → (broker reject)   → REJECTED

The Trade row is the single source of truth. Position rows are
reconciled separately via `portfolio.reconcile`.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from quant.db.models import OrderSide, OrderStatus, Trade
from quant.execution.broker import ALPACA_STATUS_MAP, Broker, BrokerOrderRequest
from quant.risk.manager import OrderIntent, RiskManager

log = logging.getLogger("quant.execution.orders")


class OrderService:
    def __init__(self, session: AsyncSession, broker: Broker) -> None:
        self.session = session
        self.broker = broker
        self.risk = RiskManager(session)

    async def place(self, intent: OrderIntent, *, order_type: str = "market") -> Trade:
        # Risk gate
        check = await self.risk.check(intent)
        client_order_id = f"q-{uuid.uuid4().hex[:24]}"
        trade = Trade(
            user_id=uuid.UUID(intent.user_id),
            symbol=intent.symbol,
            side=OrderSide[intent.side.lower()],
            status=OrderStatus.pending,
            quantity=intent.quantity,
            limit_price=intent.limit_price,
            trade_date=datetime.now(UTC).date(),
            client_order_id=client_order_id,
        )
        self.session.add(trade)
        await self.session.flush()

        if not check.ok:
            trade.status = OrderStatus.rejected
            log.warning(
                "risk rejected order user=%s sym=%s qty=%s reason=%s",
                intent.user_id,
                intent.symbol,
                intent.quantity,
                check.reason,
            )
            await self.session.commit()
            return trade

        # Submit to broker
        try:
            ack = await self.broker.submit(
                BrokerOrderRequest(
                    symbol=intent.symbol,
                    side=intent.side,
                    quantity=intent.quantity,
                    order_type=order_type,
                    limit_price=intent.limit_price,
                    client_order_id=client_order_id,
                )
            )
        except Exception as e:
            trade.status = OrderStatus.rejected
            log.exception("broker submit failed: %s", e)
            await self.session.commit()
            return trade

        trade.broker_order_id = ack.broker_order_id
        trade.submitted_at = datetime.now(UTC)
        trade.status = OrderStatus[ALPACA_STATUS_MAP.get(ack.status.lower(), "SUBMITTED").lower()]
        await self.session.commit()
        return trade

    async def cancel(self, trade_id: uuid.UUID) -> Trade:
        t = await self.session.get(Trade, trade_id)
        if t is None:
            raise ValueError(f"trade {trade_id} not found")
        if t.status in (OrderStatus.filled, OrderStatus.cancelled, OrderStatus.rejected):
            return t  # terminal state, nothing to do
        if t.broker_order_id:
            try:
                await self.broker.cancel(t.broker_order_id)
            except Exception as e:
                log.warning("broker cancel failed for %s: %s", t.broker_order_id, e)
        t.status = OrderStatus.cancelled
        await self.session.commit()
        return t

    async def refresh_status(self, trade_id: uuid.UUID) -> Trade:
        t = await self.session.get(Trade, trade_id)
        if t is None or t.broker_order_id is None:
            raise ValueError("trade not found or never submitted")
        raw = await self.broker.get_status(t.broker_order_id)
        mapped = ALPACA_STATUS_MAP.get(raw.lower(), t.status.value)
        t.status = OrderStatus[mapped.lower()]
        if t.status == OrderStatus.filled and t.filled_at is None:
            t.filled_at = datetime.now(UTC)
            # In a real impl we'd pull fill_price + filled_qty from the broker payload.
            t.filled_quantity = t.quantity
            t.fill_price = t.limit_price or Decimal("0")
        await self.session.commit()
        return t
