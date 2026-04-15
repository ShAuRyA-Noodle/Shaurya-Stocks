import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans

from backend.config import SYMBOL


DATA_DIR = Path("data/processed")
OUTPUT_DIR = Path("reports/regimes")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REGIME_FEATURES = [
    "return_1d",
    "volatility_20"
]

def load_data(symbol: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{symbol}_features.csv")

def detect_regimes(df: pd.DataFrame, n_regimes: int = 3) -> pd.DataFrame:
    df = df.copy()

    X = df[REGIME_FEATURES].dropna()

    kmeans = KMeans(
        n_clusters=n_regimes,
        random_state=42,
        n_init="auto"
    )

    regimes = kmeans.fit_predict(X)

    df = df.loc[X.index]
    df["regime_id"] = regimes

    return df, kmeans

def label_regimes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Human-readable regime labeling (post-hoc, interpretable)
    """
    regime_stats = (
        df.groupby("regime_id")[REGIME_FEATURES]
        .agg(["mean", "std"])
    )

    labels = {}

    for regime_id, stats in regime_stats.iterrows():
        vol = stats[("volatility_20", "mean")]
        ret = stats[("return_1d", "mean")]

        if vol < 0.01 and ret > 0:
            label = "LOW_VOL_TRENDING"
        elif vol > 0.02:
            label = "HIGH_VOL_CHOPPY"
        else:
            label = "NEUTRAL"

        labels[regime_id] = label

    df["regime_label"] = df["regime_id"].map(labels)
    return df

def main():
    df = load_data(SYMBOL)
    df_regime, model = detect_regimes(df)

    df_labeled = label_regimes(df_regime)

    output_file = OUTPUT_DIR / f"{SYMBOL}_regimes.csv"
    df_labeled.to_csv(output_file, index=False)

    print("✅ Market regimes detected")
    print(df_labeled["regime_label"].value_counts())
    print(f"Saved regime data to {output_file}")

if __name__ == "__main__":
    main()
