# backend/execution/engine.py

from datetime import date
from backend.execution.intent import TradeIntent
from backend.execution.pricing import get_latest_close_price
from backend.execution.sizing import compute_position_size
from backend.state.portfolio import (
    create_position,
    add_position,
    close_position,
)


class ExecutionEngine:
    """
    Execution engine with optional dry-run mode.
    All state mutations are explicit and injected.
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    def execute_intent(
        self,
        symbol: str,
        intent: TradeIntent,
        state: dict,
    ):
        if intent == TradeIntent.OPEN_LONG:
            self._open_long(symbol, state)

        elif intent == TradeIntent.CLOSE_POSITION:
            self._close_position(symbol, state)

        else:
            self._do_nothing(symbol)

    # -------------------------
    # ENABLED: OPEN LONG
    # -------------------------
    def _open_long(self, symbol: str, state: dict):
        if self.dry_run:
            print(f"[DRY-RUN] Would OPEN position for {symbol}")
            return

        try:
            entry_price = get_latest_close_price(symbol)
        except Exception as e:
            print(f"[ERROR] Cannot get price for {symbol}: {e}")
            return

        quantity = compute_position_size(
            cash=state["cash"],
            price=entry_price,
            risk_fraction=0.10,
        )

        if quantity <= 0:
            print(f"[SKIP] Not enough cash to open position for {symbol}")
            return

        position = create_position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            entry_date=date.today().isoformat(),
        )

        add_position(state, position)

        print(
            f"[LIVE] OPENED position for {symbol} | "
            f"qty={quantity} @ {entry_price}"
        )

    # -------------------------
    # ENABLED: CLOSE POSITION
    # -------------------------
    def _close_position(self, symbol: str, state: dict):
        if self.dry_run:
            print(f"[DRY-RUN] Would CLOSE position for {symbol}")
            return

        try:
            exit_price = get_latest_close_price(symbol)
        except Exception as e:
            print(f"[ERROR] Cannot get price for {symbol}: {e}")
            return

        close_position(
            state=state,
            symbol=symbol,
            exit_price=exit_price,
            realized_pnl=(
                exit_price - state["positions"][symbol]["entry_price"]
            ) * state["positions"][symbol]["quantity"],
        )

        print(f"[LIVE] CLOSED position for {symbol} @ {exit_price}")

    # -------------------------
    # NO ACTION
    # -------------------------
    def _do_nothing(self, symbol: str):
        print(f"[NO-OP] No action for {symbol}")
