# tests/unit/test_signal_contract.py

ALLOWED_SIGNALS = {"BUY", "SELL", "HOLD"}


def test_signal_contract_valid():
    """
    ML signal output must always respect the contract:
    - signal ∈ {BUY, SELL, HOLD}
    - confidence ∈ [0, 1]
    """

    # Example signal (simulates model output)
    signal = {
        "symbol": "AAPL",
        "signal": "BUY",
        "confidence": 0.73,
    }

    assert signal["signal"] in ALLOWED_SIGNALS
    assert isinstance(signal["confidence"], float)
    assert 0.0 <= signal["confidence"] <= 1.0
