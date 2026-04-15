# backend/cross_sectional_features.py

import pandas as pd
from pathlib import Path
from backend.universe_loader import load_universe_panel, UNIVERSE

OUTPUT_PATH = Path("data/processed/universe_features.csv")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

RELATIVE_FEATURES = [
    "return_1d",
    "return_5d",
    "volatility_20",
    "rsi_14",
]


def add_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    universe_means = (
        df.groupby("Date")[RELATIVE_FEATURES]
        .mean()
        .reset_index()
        .rename(columns={f: f"{f}_universe_mean" for f in RELATIVE_FEATURES})
    )

    df = df.merge(universe_means, on="Date", how="left")

    for f in RELATIVE_FEATURES:
        df[f"{f}_rel"] = df[f] - df[f"{f}_universe_mean"]

    return df


def main():
    panel = load_universe_panel(UNIVERSE)
    panel = add_relative_features(panel)

    panel.to_csv(OUTPUT_PATH, index=False)

    print("✅ Cross-sectional features saved")
    print(f"Path: {OUTPUT_PATH}")
    print("\nColumns:")
    print([c for c in panel.columns if c.endswith("_rel")])


if __name__ == "__main__":
    main()
