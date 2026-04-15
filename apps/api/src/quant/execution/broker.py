"""
Broker protocol + Alpaca implementation.

The protocol is tight on purpose: anything more specific belongs inside the
concrete adapter. This keeps the order service free of vendor-specific types.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class BrokerOrderRequest:
    symbol: str
    side: str  # "BUY" | "SELL"
    quantity: Decimal
    order_type: str = "market"  # "market" | "limit"
    limit_price: Decimal | None = None
    time_in_force: str = "day"
    client_order_id: str | None = None


@dataclass(frozen=True)
class BrokerOrderAck:
    broker_order_id: str
    client_order_id: str
    status: str  # raw broker status — service maps to OrderStatus


class Broker(Protocol):
    async def submit(self, req: BrokerOrderRequest) -> BrokerOrderAck: ...
    async def cancel(self, broker_order_id: str) -> None: ...
    async def get_status(self, broker_order_id: str) -> str: ...


# ----------------------------------------------------------------
# Alpaca concrete — wraps the existing AlpacaBrokerAdapter
# ----------------------------------------------------------------
class AlpacaBroker:
    def __init__(self) -> None:
        from quant.adapters.alpaca import AlpacaBrokerAdapter

        self._a = AlpacaBrokerAdapter()

    async def submit(self, req: BrokerOrderRequest) -> BrokerOrderAck:
        resp = await self._a.submit_order(
            symbol=req.symbol,
            qty=float(req.quantity),
            side=req.side.lower(),
            type=req.order_type,
            time_in_force=req.time_in_force,
            limit_price=float(req.limit_price) if req.limit_price else None,
            client_order_id=req.client_order_id,
        )
        return BrokerOrderAck(
            broker_order_id=str(resp["id"]),
            client_order_id=str(resp.get("client_order_id", req.client_order_id or "")),
            status=str(resp.get("status", "new")),
        )

    async def cancel(self, broker_order_id: str) -> None:
        await self._a.cancel_order(broker_order_id)

    async def get_status(self, broker_order_id: str) -> str:
        resp = await self._a.get_json(f"/v2/orders/{broker_order_id}")
        return str(resp.get("status", "unknown"))

    async def aclose(self) -> None:
        await self._a.aclose()


# Alpaca's raw statuses → our OrderStatus enum (string values).
ALPACA_STATUS_MAP: dict[str, str] = {
    "new": "SUBMITTED",
    "pending_new": "SUBMITTED",
    "accepted": "SUBMITTED",
    "partially_filled": "PARTIAL",
    "filled": "FILLED",
    "done_for_day": "FILLED",
    "canceled": "CANCELLED",
    "expired": "EXPIRED",
    "rejected": "REJECTED",
    "replaced": "SUBMITTED",
    "pending_cancel": "SUBMITTED",
    "pending_replace": "SUBMITTED",
    "stopped": "CANCELLED",
    "suspended": "REJECTED",
    "calculated": "SUBMITTED",
}
