import pandas as pd
import numpy as np
import pickle
from pathlib import Path

from backend.config import SYMBOL


DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("reports/counterfactuals")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "return_1d",
    "return_5d",
    "ma_5",
    "ma_20",
    "volatility_20",
    "rsi_14",
]

SIGNAL_MAP = {
    0: "SELL",
    1: "HOLD",
    2: "BUY"
}

def load_data():
    return pd.read_csv(DATA_DIR / f"{SYMBOL}_features.csv")

def load_model():
    with open(MODEL_DIR / f"{SYMBOL}_xgboost.pkl", "rb") as f:
        return pickle.load(f)

def main():
    df = load_data()
    model = load_model()

    latest = df.iloc[-1].copy()
    X_latest = latest[FEATURES].to_frame().T

    # 🔒 PRODUCTION SAFETY: enforce numeric dtypes
    X_latest = X_latest.apply(pd.to_numeric, errors="coerce")


    original_pred = model.predict(X_latest)[0]
    original_signal = SIGNAL_MAP[original_pred]

    counterfactual = None

    for feature in FEATURES:
        base_value = latest[feature]

        # Sweep small perturbations
        for delta in np.linspace(-2, 2, 41):
            perturbed = X_latest.copy()
            perturbed[feature] = base_value * (1 + delta / 100)

            new_pred = model.predict(perturbed)[0]

            if new_pred != original_pred:
                counterfactual = {
                    "feature": feature,
                    "current_value": round(float(base_value), 4),
                    "counterfactual_value": round(float(perturbed[feature].iloc[0]), 4),
                    "new_signal": SIGNAL_MAP[new_pred]
                }
                break

        if counterfactual:
            break

    result = {
    "symbol": SYMBOL,
    "current_signal": original_signal,
    "counterfactual": counterfactual,
    "interpretation": (
        "Decision is locally robust; no minimal single-feature change "
        "within tested bounds alters the signal."
        if counterfactual is None
        else "Decision is locally sensitive to feature changes."
    )
}


    output_file = OUTPUT_DIR / f"{SYMBOL}_counterfactual.json"
    pd.Series(result).to_json(output_file)

    print("✅ Counterfactual explanation computed")
    print(result)

if __name__ == "__main__":
    main()
