# backend/infer_cross_sectional.py

import pandas as pd
import pickle
from pathlib import Path

MODEL_PATH = Path("models/cross_sectional_xgb.pkl")
FEATURE_PATH = Path("data/processed/universe_features.csv")

# 🔧 OUTPUT CONTRACT
OUTPUT_DIR = Path("reports/signals")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "return_1d_rel",
    "return_5d_rel",
    "volatility_20_rel",
    "rsi_14_rel",
]

TOP_K = 1  # top asset per day (scale later)


def main():
    df = pd.read_csv(FEATURE_PATH)
    df["Date"] = pd.to_datetime(df["Date"])

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    # Predict alpha probability
    df["alpha_prob"] = model.predict_proba(df[FEATURES])[:, 1]

    # Rank assets per day
    df["rank"] = df.groupby("Date")["alpha_prob"].rank(
        ascending=False, method="first"
    )

    signals = df[df["rank"] <= TOP_K].copy()
    signals = signals.sort_values(["Date", "rank"])

    # 🔧 CRITICAL: SAVE CONTRACTED ARTIFACT
    output_path = OUTPUT_DIR / "cross_sectional_alpha.csv"
    signals.to_csv(output_path, index=False)

    print(f"✅ Cross-sectional alpha signals saved to {output_path}")
    print(signals[["Date", "symbol", "alpha_prob", "rank"]].head())


if __name__ == "__main__":
    main()
