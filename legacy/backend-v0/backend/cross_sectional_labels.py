# backend/cross_sectional_labels.py

import pandas as pd
from pathlib import Path
from backend.universe_loader import load_universe

# ============================
# CONFIG
# ============================
UNIVERSE = ["AAPL", "MSFT"]
OUTPUT_DIR = Path("data/processed")
HORIZON = 5  # days forward
TOP_Q = 0.8
BOTTOM_Q = 0.2


def add_cross_sectional_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Future returns per symbol
    df["future_return"] = (
        df.groupby("symbol")["return_5d"]
        .shift(-HORIZON)
    )

    # Rank within each date
    df["rank"] = (
        df.groupby("Date")["future_return"]
        .rank(method="first", pct=True)
    )

    # Label assignment
    df["label"] = 1  # HOLD
    df.loc[df["rank"] >= TOP_Q, "label"] = 2   # BUY
    df.loc[df["rank"] <= BOTTOM_Q, "label"] = 0  # SELL

    return df.dropna().reset_index(drop=True)


if __name__ == "__main__":
    df = load_universe(UNIVERSE)
    labeled = add_cross_sectional_labels(df)

    print(labeled[["Date", "symbol", "future_return", "rank", "label"]].head())

    output_path = OUTPUT_DIR / "universe_labeled.csv"
    labeled.to_csv(output_path, index=False)

    print(f"\n✅ Cross-sectional labels saved to {output_path}")
