# backend/run_inference.py

import argparse
import json
from datetime import datetime, UTC
from pathlib import Path
import pandas as pd
import pickle

DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("reports/signals")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "return_1d",
    "return_5d",
    "ma_5",
    "ma_20",
    "volatility_20",
    "rsi_14",
]


def load_latest_features(symbol: str):
    df = pd.read_csv(DATA_DIR / f"{symbol}_features.csv")
    return df.iloc[-1:][FEATURES]


# --------------------------------------------------
# 🔑 CALLABLE INFERENCE WRAPPER (NO LOGIC CHANGES)
# --------------------------------------------------
def run_inference_for_symbol(symbol: str) -> dict:
    """
    Programmatic entry point for daily automation.
    Returns the final signal dict.
    """
    model = pickle.load(open(MODEL_DIR / f"{symbol}_xgboost.pkl", "rb"))
    X = load_latest_features(symbol)

    proba = model.predict_proba(X)[0]
    signal = ["SELL", "HOLD", "BUY"][proba.argmax()]

    output = {
        "symbol": symbol,
        "date": datetime.now(UTC).strftime("%Y-%m-%d"),
        "signal": signal,
        "confidence": float(proba.max()),
    }

    out_path = OUTPUT_DIR / f"{symbol}_latest_signal.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()

    output = run_inference_for_symbol(args.symbol)

    print("📈 DAILY SIGNAL GENERATED")
    print(output)


if __name__ == "__main__":
    main()
