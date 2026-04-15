from backend.run_inference import run_inference_for_symbol
from backend.execution.intent_mapper import map_signal_to_intent
from backend.execution.engine import ExecutionEngine
from backend.execution.intent import TradeIntent
from backend.state.portfolio import (
    initialize_portfolio_state,
    has_already_run_today,
    update_unrealized_pnl,
    mark_run_complete,
    record_daily_signal,
    record_daily_intent,
)
from config import CONFIG

# -------------------------
# DEV ONLY — FORCE OVERRIDES
# -------------------------
FORCE_BUY_SYMBOL = None    # e.g. "AAPL" to force OPEN_LONG
FORCE_SELL_SYMBOL = None  # e.g. "AAPL" to force CLOSE_POSITION


def main(dry_run: bool = False):
    state = initialize_portfolio_state()

    if has_already_run_today(state):
        print("Already ran today. Exiting.")
        return {"status": "already_ran"}

    print("Daily run starting...")

    # -------------------------
    # DRY-RUN SHORT CIRCUIT
    # -------------------------
    if dry_run:
        print("[DRY-RUN] No state changes applied")
        return {"status": "ok", "dry_run": True}

    # 🔓 LIVE MODE (ENGINE CONTROLS SAFETY)
    engine = ExecutionEngine(dry_run=False)

    signals = {}

    for symbol in CONFIG.UNIVERSE:
        signal = run_inference_for_symbol(symbol)
        signals[symbol] = signal

        has_position = symbol in state["positions"]

        intent = map_signal_to_intent(
            signal=signal["signal"],
            has_position=has_position,
        )

        # -------------------------
        # DEV ONLY: FORCE BUY
        # -------------------------
        if FORCE_BUY_SYMBOL == symbol:
            intent = TradeIntent.OPEN_LONG

        # -------------------------
        # DEV ONLY: FORCE SELL
        # -------------------------
        if FORCE_SELL_SYMBOL == symbol:
            intent = TradeIntent.CLOSE_POSITION

        record_daily_signal(signal, source="ts_model")

        record_daily_intent(
            date_str=signal["date"],
            symbol=symbol,
            signal=signal["signal"],
            intent=intent.value,
            has_position=has_position,
        )

        engine.execute_intent(symbol, intent, state)

        print(f"{symbol} | Signal={signal['signal']} | Intent={intent.value}")

    # -------------------------
    # END-OF-DAY VALUATION
    # -------------------------
    update_unrealized_pnl(state)
    mark_run_complete(state)

    print("Daily run complete.")
    return {"status": "ok", "dry_run": False}


if __name__ == "__main__":
    main(dry_run=False)
