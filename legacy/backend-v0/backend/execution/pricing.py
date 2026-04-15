# backend/execution/pricing.py

import pandas as pd
from config import CONFIG


def get_latest_close_price(symbol: str) -> float:
    """
    Returns the latest CLOSE price used by inference & execution.
    Deterministic. No API calls.
    """
    features_path = CONFIG.DATA_DIR / "processed" / f"{symbol}_features.csv"

    if not features_path.exists():
        raise FileNotFoundError(f"No features file for {symbol}")

    df = pd.read_csv(features_path)

    if df.empty:
        raise ValueError(f"Features file empty for {symbol}")

    if "Close" not in df.columns:
        raise KeyError(
            f"'Close' column not found for {symbol}. "
            f"Available columns: {df.columns.tolist()}"
        )

    price = df.iloc[-1]["Close"]

    if pd.isna(price):
        raise ValueError(f"Latest Close price is NaN for {symbol}")

    return float(price)
