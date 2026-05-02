"""
Paper-trading session orchestrator — pure logic, broker-agnostic.

This module is the bridge between a backtested signal and a paper-trading
broker (Alpaca paper, by default). It is deliberately library-grade: takes
the current portfolio, a target weight vector, latest prices, and a
`Broker` instance, and returns the orders that bring the portfolio to the
target. It does not pull data, does not log to a database, does not run
on a schedule. Those responsibilities belong to a worker that wraps this.

Design constraints:

- **Long-only, equal-weight or weighted top-K.** Same risk profile as the
  walk-forward backtest, so paper PnL is comparable to backtest claims.
- **No partial fills modeled.** The broker reports back whatever it does;
  this module only computes intent. Fill bookkeeping is downstream.
- **Position sizing in shares, not dollars.** Quantities are computed from
  target_dollars / price and rounded down to whole shares (Alpaca paper
  supports fractionals but most real venues don't — keep parity).
- **Idempotency.** Re-running with the same inputs produces the same
  orders; `client_order_id` is derived from a stable hash so the broker
  can dedupe duplicate submissions.

What this is NOT:

- Not a strategy. It receives `target_weights` from a caller; it does not
  compute a signal.
- Not a risk manager. The caller is responsible for cap, drawdown, and
  position-limit checks.
- Not a scheduler. Wire it into a Prefect / cron / systemd job upstream.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal
from typing import Any

from quant.execution.broker import Broker, BrokerOrderAck, BrokerOrderRequest


@dataclass(frozen=True)
class Position:
    """Current holding for a single symbol. Quantity is always non-negative
    here (long-only). Price is the latest close used for valuation."""

    symbol: str
    quantity: Decimal
    last_price: Decimal


@dataclass(frozen=True)
class TargetAllocation:
    """Desired portfolio at the next rebalance. Weights must sum to ≤ 1.0;
    the residual is left in cash."""

    weights: Mapping[str, float]  # symbol -> fraction of portfolio_value
    portfolio_value: Decimal


@dataclass(frozen=True)
class ProposedOrder:
    """A computed order before submission. Subset of BrokerOrderRequest plus
    the rationale (the delta in shares it represents)."""

    symbol: str
    side: str  # "BUY" | "SELL"
    quantity: Decimal
    delta_shares: Decimal  # positive for buys, negative for sells
    target_value: Decimal
    current_value: Decimal


# ------------------------------------------------------------------
# Order computation
# ------------------------------------------------------------------
def compute_target_orders(
    *,
    current_positions: list[Position],
    target: TargetAllocation,
    latest_prices: Mapping[str, Decimal],
    min_share_threshold: int = 1,
) -> list[ProposedOrder]:
    """
    Compute the orders that move the portfolio from `current_positions` to
    `target`. Returns proposals — submission is the caller's job.

    `min_share_threshold` is the smallest absolute delta in shares that
    will produce an order. Default 1 means: never submit a fractional-only
    order. Set to 0 if your broker supports fractionals AND you want the
    portfolio to track weights tightly.
    """
    # Validate weight sum.
    weight_sum = sum(target.weights.values())
    if weight_sum < -1e-9 or weight_sum > 1.0 + 1e-9:
        raise ValueError(f"target weights sum to {weight_sum:.4f}, must be in [0, 1]")

    # Index current by symbol; compute current dollar value at latest price.
    current_by_sym = {p.symbol: p for p in current_positions}
    target_symbols = set(target.weights.keys())
    universe = set(current_by_sym.keys()) | target_symbols

    # Validate every traded symbol has a price.
    missing = [s for s in universe if s not in latest_prices]
    if missing:
        raise ValueError(f"latest_prices missing for: {sorted(missing)}")

    proposals: list[ProposedOrder] = []
    threshold = Decimal(min_share_threshold)
    for sym in sorted(universe):
        price = latest_prices[sym]
        if price <= 0:
            raise ValueError(f"non-positive price for {sym}: {price}")
        cur_pos = current_by_sym.get(sym)
        cur_qty = cur_pos.quantity if cur_pos is not None else Decimal(0)
        cur_val = cur_qty * price

        target_weight = Decimal(str(target.weights.get(sym, 0.0)))
        target_val = target_weight * target.portfolio_value
        target_qty = (target_val / price).to_integral_value(rounding=ROUND_DOWN)
        target_val_rounded = target_qty * price

        delta = target_qty - cur_qty
        if delta == 0 or abs(delta) < threshold:
            continue

        side = "BUY" if delta > 0 else "SELL"
        proposals.append(
            ProposedOrder(
                symbol=sym,
                side=side,
                quantity=abs(delta),
                delta_shares=delta,
                target_value=target_val_rounded,
                current_value=cur_val,
            )
        )

    return proposals


def proposed_to_broker_request(
    proposed: ProposedOrder,
    *,
    session_id: str,
) -> BrokerOrderRequest:
    """
    Translate a ProposedOrder into a BrokerOrderRequest with a stable,
    idempotent client_order_id. Hashing (session_id, symbol, side, qty)
    means resubmitting the same proposal in the same session yields the
    same id and the broker dedupes.
    """
    payload = f"{session_id}|{proposed.symbol}|{proposed.side}|{proposed.quantity}"
    cid = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return BrokerOrderRequest(
        symbol=proposed.symbol,
        side=proposed.side,
        quantity=proposed.quantity,
        order_type="market",
        time_in_force="day",
        client_order_id=cid,
    )


# ------------------------------------------------------------------
# Submission
# ------------------------------------------------------------------
async def submit_orders(
    broker: Broker,
    proposals: list[ProposedOrder],
    *,
    session_id: str,
) -> list[BrokerOrderAck]:
    """
    Submit each proposal sequentially. Returns the list of acks. Does NOT
    swallow broker errors — a vendor-side rejection should bubble up so
    the caller can decide whether to retry, alert, or halt.

    Sequential (not concurrent) on purpose: paper-trading volume is small,
    rate-limit headroom matters more than throughput, and order-of-effect
    matters when a portfolio rebalance is constructed as a sequence of
    sells followed by buys.
    """
    acks: list[BrokerOrderAck] = []
    # Sells first: free up buying power before issuing buys.
    for proposal in sorted(proposals, key=lambda p: 0 if p.side == "SELL" else 1):
        req = proposed_to_broker_request(proposal, session_id=session_id)
        ack = await broker.submit(req)
        acks.append(ack)
    return acks


# ------------------------------------------------------------------
# Convenience: full session in one call
# ------------------------------------------------------------------
async def run_session(
    broker: Broker,
    *,
    current_positions: list[Position],
    target: TargetAllocation,
    latest_prices: Mapping[str, Decimal],
    session_id: str,
    min_share_threshold: int = 1,
) -> dict[str, Any]:
    """One-shot helper: compute orders, submit, return summary dict."""
    proposals = compute_target_orders(
        current_positions=current_positions,
        target=target,
        latest_prices=latest_prices,
        min_share_threshold=min_share_threshold,
    )
    acks = await submit_orders(broker, proposals, session_id=session_id)
    return {
        "session_id": session_id,
        "n_proposals": len(proposals),
        "n_submitted": len(acks),
        "proposals": [p.__dict__ for p in proposals],
        "acks": [a.__dict__ for a in acks],
    }


__all__ = [
    "Position",
    "ProposedOrder",
    "TargetAllocation",
    "compute_target_orders",
    "proposed_to_broker_request",
    "run_session",
    "submit_orders",
]
