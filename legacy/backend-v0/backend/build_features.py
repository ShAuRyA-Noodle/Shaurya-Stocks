import pandas as pd
import numpy as np
from pathlib import Path

from backend.config import SYMBOL


RAW_DATA_DIR = Path("data/raw")
PROCESSED_DATA_DIR = Path("data/processed")
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Ensure proper datetime and sorting
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date").reset_index(drop=True)

    # Dynamically detect numeric columns (PRODUCTION SAFE)
    expected_numeric_cols = ["Open", "High", "Low", "Close", "Volume"]
    numeric_cols = [col for col in expected_numeric_cols if col in df.columns]

    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows where Close is missing (critical price anchor)
    df = df.dropna(subset=["Close"]).reset_index(drop=True)

    # --------------------
    # Feature Engineering
    # --------------------

    # Returns
    df["return_1d"] = df["Close"].pct_change()
    df["return_5d"] = df["Close"].pct_change(5)

    # Moving averages
    df["ma_5"] = df["Close"].rolling(window=5).mean()
    df["ma_20"] = df["Close"].rolling(window=20).mean()

    # Volatility
    df["volatility_20"] = df["return_1d"].rolling(window=20).std()

    # RSI (14-day)
    delta = df["Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    df["rsi_14"] = 100 - (100 / (1 + rs))

    # Drop rows created by rolling calculations
    df = df.dropna().reset_index(drop=True)

    return df

def process_symbol(symbol: str):
    raw_file = RAW_DATA_DIR / f"{symbol}_raw.csv"

    if not raw_file.exists():
        raise FileNotFoundError(f"Raw data not found for {symbol}")

    df = pd.read_csv(raw_file)
    features_df = build_features(df)

    output_file = PROCESSED_DATA_DIR / f"{symbol}_features.csv"
    features_df.to_csv(output_file, index=False)

    print(f"✅ Saved processed features to {output_file}")

if __name__ == "__main__":
    process_symbol(SYMBOL)
