"""Unit tests for OrderService — broker + session fully mocked."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from quant.db.models import OrderStatus
from quant.execution.broker import BrokerOrderAck
from quant.execution.orders import OrderService
from quant.risk.manager import OrderIntent, RiskCheckResult


def _fake_session() -> MagicMock:
    """A session stub where .add records the Trade and .flush/.commit are no-ops."""
    sess = MagicMock()
    sess.add = MagicMock()
    sess.flush = AsyncMock()
    sess.commit = AsyncMock()
    sess.get = AsyncMock()
    return sess


def _intent() -> OrderIntent:
    return OrderIntent(
        user_id=str(uuid.uuid4()),
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("1"),
        limit_price=None,
        mark_price=Decimal("100"),
    )


@pytest.mark.asyncio
async def test_risk_reject_marks_trade_rejected() -> None:
    sess = _fake_session()
    broker = AsyncMock()
    svc = OrderService(sess, broker)
    svc.risk.check = AsyncMock(  # type: ignore[method-assign]
        return_value=RiskCheckResult(False, "blocked")
    )
    trade = await svc.place(_intent())
    assert trade.status == OrderStatus.rejected
    broker.submit.assert_not_called()
    sess.commit.assert_awaited()


@pytest.mark.asyncio
async def test_happy_path_submits_and_maps_status() -> None:
    sess = _fake_session()
    broker = AsyncMock()
    broker.submit = AsyncMock(
        return_value=BrokerOrderAck(broker_order_id="bk-1", client_order_id="cid", status="accepted")
    )
    svc = OrderService(sess, broker)
    svc.risk.check = AsyncMock(return_value=RiskCheckResult(True))  # type: ignore[method-assign]
    trade = await svc.place(_intent())
    assert trade.status == OrderStatus.submitted
    assert trade.broker_order_id == "bk-1"
    broker.submit.assert_awaited_once()


@pytest.mark.asyncio
async def test_broker_exception_marks_rejected() -> None:
    sess = _fake_session()
    broker = AsyncMock()
    broker.submit = AsyncMock(side_effect=RuntimeError("boom"))
    svc = OrderService(sess, broker)
    svc.risk.check = AsyncMock(return_value=RiskCheckResult(True))  # type: ignore[method-assign]
    trade = await svc.place(_intent())
    assert trade.status == OrderStatus.rejected


@pytest.mark.asyncio
async def test_cancel_terminal_is_noop() -> None:
    from quant.db.models import Trade

    sess = _fake_session()
    fake = Trade(
        user_id=uuid.uuid4(),
        symbol="AAPL",
        side="buy",  # type: ignore[arg-type]
        status=OrderStatus.filled,
        quantity=Decimal("1"),
        trade_date=__import__("datetime").date.today(),
        client_order_id="c",
    )
    sess.get = AsyncMock(return_value=fake)
    broker = AsyncMock()
    svc = OrderService(sess, broker)
    t2 = await svc.cancel(uuid.uuid4())
    assert t2.status == OrderStatus.filled
    broker.cancel.assert_not_called()
