import pandas as pd
import pickle
from pathlib import Path

from backend.config import SYMBOL

DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("reports/stability")
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

def load_models():
    models = {}
    with open(MODEL_DIR / f"{SYMBOL}_logreg.pkl", "rb") as f:
        models["logreg"] = pickle.load(f)
    with open(MODEL_DIR / f"{SYMBOL}_xgboost.pkl", "rb") as f:
        models["xgboost"] = pickle.load(f)
    return models

def compute_agreement(models, X_latest):
    predictions = {}
    for name, model in models.items():
        predictions[name] = model.predict(X_latest)[0]

    values = list(predictions.values())
    agreement = values.count(values[0]) / len(values)

    return predictions, agreement

def compute_stability(signal_series):
    """
    Number of consecutive days the current signal persisted
    """
    latest_signal = signal_series.iloc[-1]
    count = 0

    for sig in reversed(signal_series):
        if sig == latest_signal:
            count += 1
        else:
            break

    return count

def main():
    df = load_data()
    models = load_models()

    X = df[FEATURES]
    X_latest = X.tail(1)

    preds, agreement_score = compute_agreement(models, X_latest)

    df["signal"] = df[FEATURES].apply(
        lambda row: SIGNAL_MAP[
            models["xgboost"].predict(pd.DataFrame([row]))[0]
        ],
        axis=1
    )

    stability_days = compute_stability(df["signal"])

    result = {
        "latest_signal": SIGNAL_MAP[preds["xgboost"]],
        "agreement_score": round(agreement_score, 2),
        "stability_days": stability_days
    }

    output_file = OUTPUT_DIR / f"{SYMBOL}_signal_stability.json"
    pd.Series(result).to_json(output_file)

    print("✅ Signal stability analysis completed")
    print(result)

if __name__ == "__main__":
    main()
