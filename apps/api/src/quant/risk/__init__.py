"""Risk management — pre-trade checks + kill switch."""

from quant.risk.manager import (
    KILL_SWITCH_KEY,
    OrderIntent,
    RiskCheckResult,
    RiskManager,
    RiskViolation,
)

__all__ = [
    "KILL_SWITCH_KEY",
    "OrderIntent",
    "RiskCheckResult",
    "RiskManager",
    "RiskViolation",
]
