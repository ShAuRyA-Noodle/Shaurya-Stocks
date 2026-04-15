import pandas as pd
import numpy as np
import pickle
from pathlib import Path
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss

from backend.config import SYMBOL


DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("reports/calibration")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "return_1d",
    "return_5d",
    "ma_5",
    "ma_20",
    "volatility_20",
    "rsi_14",
]

def load_data(symbol: str):
    df = pd.read_csv(DATA_DIR / f"{symbol}_features.csv")
    return df

def load_model(symbol: str):
    with open(MODEL_DIR / f"{symbol}_xgboost.pkl", "rb") as f:
        return pickle.load(f)

def prepare_labels(df: pd.DataFrame):
    # Same labeling logic used during training
    df = df.copy()
    future_return = df["return_1d"].shift(-1)

    df["label"] = 1  # HOLD
    df.loc[future_return > 0.005, "label"] = 2  # BUY
    df.loc[future_return < -0.005, "label"] = 0  # SELL

    df = df.dropna().reset_index(drop=True)
    return df

def main():
    df = load_data(SYMBOL)
    df = prepare_labels(df)

    X = df[FEATURES]
    y = df["label"]

    base_model = load_model(SYMBOL)

    # Calibrate probabilities
    calibrator = CalibratedClassifierCV(
        base_model,
        method="isotonic",
        cv=3
    )

    calibrator.fit(X, y)

    # Evaluate calibration
    probs = calibrator.predict_proba(X)
    brier = brier_score_loss(
        y == probs.argmax(axis=1),
        probs.max(axis=1)
    )

    with open(MODEL_DIR / f"{SYMBOL}_calibrated_model.pkl", "wb") as f:
        pickle.dump(calibrator, f)

    print("✅ Confidence calibration completed")
    print(f"Brier score (lower is better): {brier:.4f}")
    print("Saved calibrated model")

if __name__ == "__main__":
    main()
