from enum import Enum


class TradeIntent(Enum):
    OPEN_LONG = "OPEN_LONG"
    CLOSE_POSITION = "CLOSE_POSITION"
    HOLD_POSITION = "HOLD_POSITION"
    DO_NOTHING = "DO_NOTHING"
