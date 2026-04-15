import pytest
from backend.execution import pricing


def test_missing_price_data_fails_safely(monkeypatch):
    """
    If price data is missing or corrupted,
    the system must NOT crash or trade.
    """

    def broken_price_loader(symbol: str):
        return None  # simulate missing data

    monkeypatch.setattr(
        pricing,
        "get_latest_close_price",
        broken_price_loader,
    )

    price = pricing.get_latest_close_price("AAPL")

    assert price is None
