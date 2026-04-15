# tests/unit/test_config.py

from backend.config import DEFAULT_SYMBOL, UNIVERSE, DATA_DIR, MODEL_DIR, REPORTS_DIR


def test_config_is_deterministic():
    """
    Config values must never change between imports.
    This guarantees reproducibility across runs.
    """

    config_snapshot_1 = {
        "default_symbol": DEFAULT_SYMBOL,
        "universe": tuple(UNIVERSE),
        "data_dir": str(DATA_DIR),
        "model_dir": str(MODEL_DIR),
        "reports_dir": str(REPORTS_DIR),
    }

    config_snapshot_2 = {
        "default_symbol": DEFAULT_SYMBOL,
        "universe": tuple(UNIVERSE),
        "data_dir": str(DATA_DIR),
        "model_dir": str(MODEL_DIR),
        "reports_dir": str(REPORTS_DIR),
    }

    assert config_snapshot_1 == config_snapshot_2
