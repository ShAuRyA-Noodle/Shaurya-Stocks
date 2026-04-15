# backend/risk_context.py

import pandas as pd
import numpy as np
import json
import argparse
from pathlib import Path

DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("reports/risk")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def compute_risk(df: pd.DataFrame, symbol: str):
    recent = df.tail(252)

    vol = recent["volatility_20"].iloc[-1]
    vol_pct = (
        recent["volatility_20"].rank(pct=True).iloc[-1] * 100
    )

    rolling_max = recent["Close"].cummax()
    drawdown = (recent["Close"] / rolling_max - 1).iloc[-1] * 100

    risk_level = (
        "HIGH" if vol_pct > 70 or drawdown < -10
        else "MEDIUM" if vol_pct > 40
        else "LOW"
    )

    result = {
        "symbol": symbol,
        "volatility_percentile": round(vol_pct, 2),
        "drawdown_30d_pct": round(drawdown, 2),
        "risk_level": risk_level,
    }

    out = OUTPUT_DIR / f"{symbol}_risk.json"
    with open(out, "w") as f:
        json.dump(result, f, indent=2)

    print("✅ Risk context computed")
    print(result)
    print(f"Saved risk context to {out}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()

    df = pd.read_csv(DATA_DIR / f"{args.symbol}_features.csv")
    compute_risk(df, args.symbol)

if __name__ == "__main__":
    main()
