# backend/train_cross_sectional.py

import pandas as pd
import pickle
from pathlib import Path
from xgboost import XGBClassifier

# ============================
# PATHS
# ============================
FEATURE_PATH = Path("data/processed/universe_features.csv")
LABEL_PATH = Path("data/processed/universe_labeled.csv")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)

# ============================
# FEATURES
# ============================
FEATURES = [
    "return_1d_rel",
    "return_5d_rel",
    "volatility_20_rel",
    "rsi_14_rel",
]

def main():
    # ----------------------------
    # LOAD DATA
    # ----------------------------
    features = pd.read_csv(FEATURE_PATH)
    labels = pd.read_csv(LABEL_PATH)

    features["Date"] = pd.to_datetime(features["Date"])
    labels["Date"] = pd.to_datetime(labels["Date"])

    # ----------------------------
    # MERGE FEATURES + LABELS
    # ----------------------------
    df = features.merge(
        labels[["Date", "symbol", "label"]],
        on=["Date", "symbol"],
        how="inner"
    )

    # ----------------------------
    # BINARY ALPHA LABEL
    # Top-ranked asset = 1
    # ----------------------------
    df["alpha_label"] = (df["label"] == 2).astype(int)

    # ----------------------------
    # TRAINING MATRICES
    # ----------------------------
    X = df[FEATURES]
    y = df["alpha_label"]

    # ----------------------------
    # MODEL
    # ----------------------------
    model = XGBClassifier(
        n_estimators=400,
        max_depth=3,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="logloss",
        random_state=42,
    )

    model.fit(X, y)

    # ----------------------------
    # SAVE
    # ----------------------------
    with open(MODEL_DIR / "cross_sectional_xgb.pkl", "wb") as f:
        pickle.dump(model, f)

    print("✅ Cross-sectional alpha model trained and saved")

    print("\nTraining summary:")
    print(df["alpha_label"].value_counts(normalize=True))

if __name__ == "__main__":
    main()
