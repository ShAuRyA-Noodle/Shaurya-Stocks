import json
import csv
from pathlib import Path
from config import CONFIG
from datetime import date, datetime
from backend.execution.pricing import get_latest_close_price


# -------------------------
# STATE + LEDGER FILES
# -------------------------
STATE_FILE = CONFIG.STATE_DIR / "portfolio_state.json"
TRADES_FILE = CONFIG.STATE_DIR / "trades.csv"
SNAPSHOTS_FILE = CONFIG.STATE_DIR / "daily_snapshots.csv"
DAILY_SIGNALS_FILE = CONFIG.STATE_DIR / "daily_signals.csv"
DAILY_INTENTS_FILE = CONFIG.STATE_DIR / "daily_intents.csv"


def load_portfolio_state():
    if not STATE_FILE.exists():
        return None

    with open(STATE_FILE, "r") as f:
        return json.load(f)


# -------------------------
# ATOMIC WRITE HELPER
# -------------------------
import tempfile
import os


def _atomic_write_json(path: Path, data: dict):
    """
    Atomically write JSON to disk.
    Prevents partial writes and is crash-safe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False
    ) as tmp:
        json.dump(data, tmp, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        temp_name = tmp.name

    os.replace(temp_name, path)


# -------------------------
# LEDGER (APPEND-ONLY)
# -------------------------
def record_trade(
    symbol: str,
    side: str,
    quantity: int,
    price: float,
    cash_after: float,
    realized_pnl: float,
):
    TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = TRADES_FILE.exists()

    with open(TRADES_FILE, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "timestamp",
                "run_date",
                "symbol",
                "side",
                "quantity",
                "price",
                "cash_after",
                "realized_pnl",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "timestamp": datetime.utcnow().isoformat(),
            "run_date": datetime.utcnow().date().isoformat(),
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "cash_after": cash_after,
            "realized_pnl": realized_pnl,
        })


# -------------------------
# DAILY SNAPSHOT (APPEND-ONLY)
# -------------------------
def record_daily_snapshot(state: dict):
    SNAPSHOTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = SNAPSHOTS_FILE.exists()

    positions_value = 0.0  # placeholder for now
    total_equity = state["cash"] + positions_value

    with open(SNAPSHOTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "cash",
                "positions_value",
                "total_equity",
                "open_positions",
                "realized_pnl",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "date": date.today().isoformat(),
            "cash": state["cash"],
            "positions_value": positions_value,
            "total_equity": total_equity,
            "open_positions": len(state["positions"]),
            "realized_pnl": state["realized_pnl"],
        })


# -------------------------
# DAILY SIGNALS (APPEND-ONLY)
# -------------------------
def record_daily_signal(signal: dict, source: str = "inference"):
    DAILY_SIGNALS_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = DAILY_SIGNALS_FILE.exists()

    with open(DAILY_SIGNALS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "symbol",
                "signal",
                "confidence",
                "source",
                "run_timestamp",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "date": signal["date"],
            "symbol": signal["symbol"],
            "signal": signal["signal"],
            "confidence": signal["confidence"],
            "source": source,
            "run_timestamp": datetime.utcnow().isoformat(),
        })


# -------------------------
# DAILY INTENTS (APPEND-ONLY)
# -------------------------
def record_daily_intent(
    date_str: str,
    symbol: str,
    signal: str,
    intent: str,
    has_position: bool,
):
    DAILY_INTENTS_FILE.parent.mkdir(parents=True, exist_ok=True)

    file_exists = DAILY_INTENTS_FILE.exists()

    with open(DAILY_INTENTS_FILE, "a", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "symbol",
                "signal",
                "intent",
                "has_position",
                "run_timestamp",
            ],
        )

        if not file_exists:
            writer.writeheader()

        writer.writerow({
            "date": date_str,
            "symbol": symbol,
            "signal": signal,
            "intent": intent,
            "has_position": has_position,
            "run_timestamp": datetime.utcnow().isoformat(),
        })


# -------------------------
# PORTFOLIO INITIALIZER
# -------------------------
def initialize_portfolio_state():
    if STATE_FILE.exists():
        return load_portfolio_state()

    initial_state = {
        "as_of_date": date.today().isoformat(),
        "cash": CONFIG.INITIAL_CAPITAL,
        "positions": {},
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "last_run_date": None,
    }

    _atomic_write_json(STATE_FILE, initial_state)
    return initial_state


# -------------------------
# DAILY RUN GUARDS
# -------------------------
def has_already_run_today(state: dict) -> bool:
    today = date.today().isoformat()
    return state.get("last_run_date") == today


def mark_run_complete(state: dict):
    state["last_run_date"] = date.today().isoformat()
    _atomic_write_json(STATE_FILE, state)
    record_daily_snapshot(state)


# -------------------------
# POSITION HELPERS
# -------------------------
def create_position(
    symbol: str,
    quantity: int,
    entry_price: float,
    entry_date: str,
    side: str = "LONG",
) -> dict:
    return {
        "symbol": symbol,
        "quantity": quantity,
        "entry_price": entry_price,
        "entry_date": entry_date,
        "side": side,
    }


def add_position(state: dict, position: dict):
    symbol = position["symbol"]

    if symbol in state["positions"]:
        raise ValueError(f"Position already exists for {symbol}")

    trade_value = position["quantity"] * position["entry_price"]

    if state["cash"] < trade_value:
        raise ValueError("Insufficient cash to open position")

    state["cash"] -= trade_value
    state["positions"][symbol] = position
    _atomic_write_json(STATE_FILE, state)

    record_trade(
        symbol=symbol,
        side="BUY",
        quantity=position["quantity"],
        price=position["entry_price"],
        cash_after=state["cash"],
        realized_pnl=0.0,
    )


# -------------------------
# POSITION CLOSE
# -------------------------
def close_position(
    state: dict,
    symbol: str,
    exit_price: float,
    realized_pnl: float = 0.0,
):
    if symbol not in state["positions"]:
        raise ValueError(f"No open position for {symbol}")

    position = state["positions"][symbol]
    trade_value = position["quantity"] * exit_price

    state["cash"] += trade_value
    del state["positions"][symbol]
    state["realized_pnl"] += realized_pnl

    record_trade(
        symbol=symbol,
        side="SELL",
        quantity=position["quantity"],
        price=exit_price,
        cash_after=state["cash"],
        realized_pnl=realized_pnl,
    )

    _atomic_write_json(STATE_FILE, state)


# -------------------------
# MARK-TO-MARKET VALUATION
# -------------------------
from backend.execution.pricing import get_latest_close_price


def update_unrealized_pnl(state: dict):
    """
    Mark open positions to market and update unrealized PnL.
    """
    total_unrealized = 0.0

    for symbol, position in state["positions"].items():
        current_price = get_latest_close_price(symbol)

        pnl = (
            current_price - position["entry_price"]
        ) * position["quantity"]

        total_unrealized += pnl

    state["unrealized_pnl"] = total_unrealized
    _atomic_write_json(STATE_FILE, state)


def reset_last_run_date_for_testing():
    """
    DEV ONLY.
    Allows re-running run_daily.py on the same day.
    """
    state = load_portfolio_state()
    if state is None:
        return

    state["last_run_date"] = None
    _atomic_write_json(STATE_FILE, state)
