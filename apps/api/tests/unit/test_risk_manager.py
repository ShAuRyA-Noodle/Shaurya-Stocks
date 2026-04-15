"""Unit tests for RiskManager.

We mock the session with a small stub rather than spinning Postgres — we are
testing the decision logic, not SQLAlchemy's query builder. The helper
methods on RiskManager are patched directly so the tests stay focused.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from quant.risk.manager import OrderIntent, RiskManager


def _intent(qty: str = "10", mark: str = "100", side: str = "BUY") -> OrderIntent:
    return OrderIntent(
        user_id="00000000-0000-0000-0000-000000000001",
        symbol="AAPL",
        side=side,  # type: ignore[arg-type]
        quantity=Decimal(qty),
        limit_price=None,
        mark_price=Decimal(mark),
    )


@pytest.fixture
def rm() -> RiskManager:
    return RiskManager(session=AsyncMock())


async def _allow_all(rm: RiskManager) -> None:
    rm._current_equity = AsyncMock(return_value=Decimal("100000"))  # type: ignore[method-assign]
    rm._open_position_count = AsyncMock(return_value=0)  # type: ignore[method-assign]
    rm._has_position = AsyncMock(return_value=False)  # type: ignore[method-assign]
    rm._sector_of = AsyncMock(return_value=None)  # type: ignore[method-assign]
    rm._sector_exposure = AsyncMock(return_value=Decimal("0"))  # type: ignore[method-assign]
    rm._today_realized_pnl = AsyncMock(return_value=Decimal("0"))  # type: ignore[method-assign]
    rm._current_drawdown = AsyncMock(return_value=Decimal("0"))  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_kill_switch_blocks_everything(rm: RiskManager) -> None:
    await _allow_all(rm)
    with patch("quant.risk.manager._kill_switch_engaged", AsyncMock(return_value=True)):
        res = await rm.check(_intent())
    assert not res.ok
    assert res.reason and "kill switch" in res.reason.lower()


@pytest.mark.asyncio
async def test_happy_path(rm: RiskManager) -> None:
    await _allow_all(rm)
    with patch("quant.risk.manager._kill_switch_engaged", AsyncMock(return_value=False)):
        res = await rm.check(_intent(qty="10", mark="100"))  # $1k < 5% of $100k
    assert res.ok, res.reason


@pytest.mark.asyncio
async def test_position_size_cap(rm: RiskManager) -> None:
    await _allow_all(rm)
    # 5% of $100k = $5000. A $10000 order must be blocked.
    with patch("quant.risk.manager._kill_switch_engaged", AsyncMock(return_value=False)):
        res = await rm.check(_intent(qty="100", mark="100"))
    assert not res.ok
    assert res.reason and "max_position_pct" in res.reason


@pytest.mark.asyncio
async def test_zero_quantity_rejected(rm: RiskManager) -> None:
    await _allow_all(rm)
    intent = OrderIntent(
        user_id="u",
        symbol="AAPL",
        side="BUY",
        quantity=Decimal("0"),
        limit_price=None,
        mark_price=Decimal("100"),
    )
    with patch("quant.risk.manager._kill_switch_engaged", AsyncMock(return_value=False)):
        res = await rm.check(intent)
    assert not res.ok
    assert res.reason and "positive" in res.reason


@pytest.mark.asyncio
async def test_max_positions_blocks_new_symbol(rm: RiskManager) -> None:
    await _allow_all(rm)
    rm._open_position_count = AsyncMock(return_value=9999)  # type: ignore[method-assign]
    rm._has_position = AsyncMock(return_value=False)  # type: ignore[method-assign]
    with patch("quant.risk.manager._kill_switch_engaged", AsyncMock(return_value=False)):
        res = await rm.check(_intent())
    assert not res.ok
    assert res.reason and "max_positions" in res.reason


@pytest.mark.asyncio
async def test_max_positions_allows_existing_symbol(rm: RiskManager) -> None:
    await _allow_all(rm)
    rm._open_position_count = AsyncMock(return_value=9999)  # type: ignore[method-assign]
    rm._has_position = AsyncMock(return_value=True)  # already hold it
    with patch("quant.risk.manager._kill_switch_engaged", AsyncMock(return_value=False)):
        res = await rm.check(_intent())
    assert res.ok, res.reason


@pytest.mark.asyncio
async def test_drawdown_kill(rm: RiskManager) -> None:
    await _allow_all(rm)
    rm._current_drawdown = AsyncMock(return_value=Decimal("0.99"))  # type: ignore[method-assign]
    with patch("quant.risk.manager._kill_switch_engaged", AsyncMock(return_value=False)):
        res = await rm.check(_intent())
    assert not res.ok
    assert res.reason and "drawdown" in res.reason
