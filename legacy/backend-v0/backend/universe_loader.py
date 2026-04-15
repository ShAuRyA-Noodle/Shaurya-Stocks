# backend/universe_loader.py

import pandas as pd
from pathlib import Path
from typing import List

# ============================
# EXPLICIT UNIVERSE (NEW)
# ============================
UNIVERSE = ["AAPL", "MSFT"]

DATA_DIR = Path("data/processed")

FEATURES = [
    "return_1d",
    "return_5d",
    "ma_5",
    "ma_20",
    "volatility_20",
    "rsi_14",
]


# ============================================================
# EXISTING PRODUCTION-GRADE LOADER (UNCHANGED)
# ============================================================
def load_universe(symbols: List[str]) -> pd.DataFrame:
    """
    Load and align feature data across all symbols in the universe.
    Only dates common to all symbols are retained.
    """

    dfs = []

    for symbol in symbols:
        path = DATA_DIR / f"{symbol}_features.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing features for {symbol}")

        df = pd.read_csv(path)
        df["Date"] = pd.to_datetime(df["Date"])
        df["symbol"] = symbol

        keep_cols = ["Date", "symbol"] + FEATURES
        df = df[keep_cols]

        dfs.append(df)

    common_dates = set(dfs[0]["Date"])
    for df in dfs[1:]:
        common_dates &= set(df["Date"])

    if not common_dates:
        raise ValueError("No common dates across universe")

    aligned = []
    for df in dfs:
        aligned.append(df[df["Date"].isin(common_dates)])

    universe_df = pd.concat(aligned, ignore_index=True)
    universe_df = universe_df.sort_values(["Date", "symbol"]).reset_index(drop=True)

    return universe_df


# ============================================================
# RAW PANEL LOADER (UNCHANGED)
# ============================================================
def load_universe_panel(symbols: List[str]) -> pd.DataFrame:
    """
    Load a raw panel of symbol feature data without date alignment.
    """

    frames = []

    for symbol in symbols:
        path = DATA_DIR / f"{symbol}_features.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing features for {symbol}")

        df = pd.read_csv(path)
        df["symbol"] = symbol
        frames.append(df)

    panel = pd.concat(frames, ignore_index=True)
    panel["Date"] = pd.to_datetime(panel["Date"])
    panel = panel.sort_values(["Date", "symbol"]).reset_index(drop=True)

    return panel


# ============================================================
# SANITY CHECK
# ============================================================
if __name__ == "__main__":
    print("=== RAW PANEL ===")
    panel = load_universe_panel(UNIVERSE)
    print(panel.head())
    print("\nRows:", len(panel))
    print("Dates:", panel["Date"].nunique())
    print("Symbols:", panel["symbol"].nunique())

    print("\n=== ALIGNED UNIVERSE ===")
    aligned = load_universe(UNIVERSE)
    print(aligned.head())
    print("\nRows:", len(aligned))
    print("Dates:", aligned["Date"].nunique())
    print("Symbols:", aligned["symbol"].nunique())
