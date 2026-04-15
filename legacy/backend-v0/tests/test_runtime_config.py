from config import CONFIG


def test_runtime_config():
    assert CONFIG.UNIVERSE == ("AAPL", "MSFT")
    assert CONFIG.INITIAL_CAPITAL > 0
    assert CONFIG.TIMEZONE.zone == "US/Eastern"
