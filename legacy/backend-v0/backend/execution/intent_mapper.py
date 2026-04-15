from backend.execution.intent import TradeIntent


def map_signal_to_intent(
    signal: str,
    has_position: bool,
) -> TradeIntent:
    if signal == "BUY" and not has_position:
        return TradeIntent.OPEN_LONG

    if signal == "BUY" and has_position:
        return TradeIntent.HOLD_POSITION

    if signal == "SELL" and has_position:
        return TradeIntent.CLOSE_POSITION

    return TradeIntent.DO_NOTHING
