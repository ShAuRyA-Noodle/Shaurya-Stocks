"""Unit tests for the paper-trading session orchestrator."""

from __future__ import annotations

from decimal import Decimal

import pytest

from quant.execution.broker import BrokerOrderAck, BrokerOrderRequest
from quant.execution.paper_session import (
    Position,
    ProposedOrder,
    TargetAllocation,
    compute_target_orders,
    proposed_to_broker_request,
    run_session,
    submit_orders,
)


# ------------------------------------------------------------------
# In-memory fake broker — test infra only, never imported by prod code
# ------------------------------------------------------------------
class _RecordingBroker:
    def __init__(self) -> None:
        self.submitted: list[BrokerOrderRequest] = []

    async def submit(self, req: BrokerOrderRequest) -> BrokerOrderAck:
        self.submitted.append(req)
        return BrokerOrderAck(
            broker_order_id=f"id-{len(self.submitted)}",
            client_order_id=req.client_order_id or "",
            status="accepted",
        )

    async def cancel(self, broker_order_id: str) -> None:  # pragma: no cover
        pass

    async def get_status(self, broker_order_id: str) -> str:  # pragma: no cover
        return "accepted"


# ------------------------------------------------------------------
# compute_target_orders
# ------------------------------------------------------------------
def test_compute_target_orders_buys_when_holding_nothing() -> None:
    target = TargetAllocation(
        weights={"AAPL": 0.6, "MSFT": 0.4},
        portfolio_value=Decimal("100000"),
    )
    prices = {"AAPL": Decimal("200"), "MSFT": Decimal("400")}

    out = compute_target_orders(current_positions=[], target=target, latest_prices=prices)
    by_sym = {p.symbol: p for p in out}
    # 60_000 / 200 = 300 shares; 40_000 / 400 = 100 shares
    assert by_sym["AAPL"].quantity == Decimal(300)
    assert by_sym["AAPL"].side == "BUY"
    assert by_sym["MSFT"].quantity == Decimal(100)
    assert by_sym["MSFT"].side == "BUY"


def test_compute_target_orders_sells_when_target_zero() -> None:
    """A symbol dropped from the target is liquidated."""
    current = [Position(symbol="OLD", quantity=Decimal(50), last_price=Decimal("10"))]
    target = TargetAllocation(weights={"NEW": 1.0}, portfolio_value=Decimal("1000"))
    prices = {"OLD": Decimal("10"), "NEW": Decimal("100")}

    out = compute_target_orders(current_positions=current, target=target, latest_prices=prices)
    by_sym = {p.symbol: p for p in out}
    assert by_sym["OLD"].side == "SELL"
    assert by_sym["OLD"].quantity == Decimal(50)
    assert by_sym["NEW"].side == "BUY"
    assert by_sym["NEW"].quantity == Decimal(10)


def test_compute_target_orders_partial_rebalance() -> None:
    """Holding 250 AAPL, target 300 → buy 50."""
    current = [Position(symbol="AAPL", quantity=Decimal(250), last_price=Decimal("200"))]
    target = TargetAllocation(weights={"AAPL": 0.6}, portfolio_value=Decimal("100000"))
    prices = {"AAPL": Decimal("200")}
    out = compute_target_orders(current_positions=current, target=target, latest_prices=prices)
    assert len(out) == 1
    assert out[0].side == "BUY"
    assert out[0].quantity == Decimal(50)


def test_compute_target_orders_skips_below_threshold() -> None:
    """Single-share delta is ignored when min_share_threshold > 1."""
    current = [Position(symbol="AAPL", quantity=Decimal(299), last_price=Decimal("200"))]
    target = TargetAllocation(weights={"AAPL": 0.6}, portfolio_value=Decimal("100000"))
    prices = {"AAPL": Decimal("200")}
    # Without threshold: 1-share buy. With threshold 5: skipped.
    default = compute_target_orders(current_positions=current, target=target, latest_prices=prices)
    elevated = compute_target_orders(
        current_positions=current,
        target=target,
        latest_prices=prices,
        min_share_threshold=5,
    )
    assert len(default) == 1
    assert default[0].quantity == Decimal(1)
    assert len(elevated) == 0


def test_compute_target_orders_rejects_overweight() -> None:
    target = TargetAllocation(weights={"AAPL": 0.6, "MSFT": 0.5}, portfolio_value=Decimal("100000"))
    prices = {"AAPL": Decimal("200"), "MSFT": Decimal("400")}
    with pytest.raises(ValueError, match="weights sum to"):
        compute_target_orders(current_positions=[], target=target, latest_prices=prices)


def test_compute_target_orders_rejects_missing_price() -> None:
    target = TargetAllocation(weights={"AAPL": 1.0}, portfolio_value=Decimal("1000"))
    prices: dict[str, Decimal] = {}  # missing AAPL
    with pytest.raises(ValueError, match="latest_prices missing"):
        compute_target_orders(current_positions=[], target=target, latest_prices=prices)


def test_compute_target_orders_rejects_non_positive_price() -> None:
    target = TargetAllocation(weights={"AAPL": 1.0}, portfolio_value=Decimal("1000"))
    with pytest.raises(ValueError, match="non-positive price"):
        compute_target_orders(
            current_positions=[],
            target=target,
            latest_prices={"AAPL": Decimal(0)},
        )


# ------------------------------------------------------------------
# Idempotency: same input → same client_order_id
# ------------------------------------------------------------------
def test_proposed_to_broker_request_is_idempotent_within_session() -> None:
    p = ProposedOrder(
        symbol="AAPL",
        side="BUY",
        quantity=Decimal(10),
        delta_shares=Decimal(10),
        target_value=Decimal("2000"),
        current_value=Decimal(0),
    )
    a = proposed_to_broker_request(p, session_id="2026-05-03T09:30:00Z")
    b = proposed_to_broker_request(p, session_id="2026-05-03T09:30:00Z")
    assert a.client_order_id == b.client_order_id

    # Different session → different id
    c = proposed_to_broker_request(p, session_id="2026-05-03T15:30:00Z")
    assert c.client_order_id != a.client_order_id


# ------------------------------------------------------------------
# Submission ordering: sells before buys
# ------------------------------------------------------------------
async def test_submit_orders_sells_before_buys() -> None:
    proposals = [
        ProposedOrder(
            symbol="AAPL",
            side="BUY",
            quantity=Decimal(10),
            delta_shares=Decimal(10),
            target_value=Decimal("2000"),
            current_value=Decimal(0),
        ),
        ProposedOrder(
            symbol="OLD",
            side="SELL",
            quantity=Decimal(5),
            delta_shares=Decimal(-5),
            target_value=Decimal(0),
            current_value=Decimal("500"),
        ),
    ]
    broker = _RecordingBroker()
    acks = await submit_orders(broker, proposals, session_id="t")
    assert len(acks) == 2
    assert broker.submitted[0].side == "SELL"
    assert broker.submitted[1].side == "BUY"


async def test_run_session_end_to_end() -> None:
    broker = _RecordingBroker()
    target = TargetAllocation(weights={"AAPL": 0.5, "MSFT": 0.5}, portfolio_value=Decimal("100000"))
    prices = {"AAPL": Decimal("200"), "MSFT": Decimal("400")}
    summary = await run_session(
        broker,
        current_positions=[],
        target=target,
        latest_prices=prices,
        session_id="2026-05-03T09:30:00Z",
    )
    assert summary["n_proposals"] == 2
    assert summary["n_submitted"] == 2
    assert summary["session_id"] == "2026-05-03T09:30:00Z"
    assert len(broker.submitted) == 2
