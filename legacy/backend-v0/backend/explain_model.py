import pandas as pd
import shap
import matplotlib.pyplot as plt
from pathlib import Path
import pickle

from backend.config import SYMBOL


# Directories
DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
OUTPUT_DIR = Path("reports/explainability")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Config

FEATURES = [
    "return_1d",
    "return_5d",
    "ma_5",
    "ma_20",
    "volatility_20",
    "rsi_14",
]

def load_data(symbol: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / f"{symbol}_features.csv")

def load_model(symbol: str):
    with open(MODEL_DIR / f"{symbol}_xgboost.pkl", "rb") as f:
        return pickle.load(f)

def main():
    # Load data and model
    df = load_data(SYMBOL)
    model = load_model(SYMBOL)

    # Feature matrix
    X = df[FEATURES]

    # SHAP explainer
    explainer = shap.Explainer(model, X)
    shap_values = explainer(X)

    # ---- Global feature importance ----
    plt.figure()
    shap.summary_plot(shap_values, X, show=False)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f"{SYMBOL}_shap_summary.png")
    plt.close()

    print(
        f"✅ SHAP summary saved to "
        f"{OUTPUT_DIR / f'{SYMBOL}_shap_summary.png'}"
    )

    # ---- Local explanation (most recent prediction) ----
    idx = -1

    # Get predicted class for this row
    X_latest = X.iloc[[idx]]
    predicted_class = model.predict(X_latest)[0]

    # Extract SHAP values for the predicted class
    local_shap = shap_values[idx, :, predicted_class]

    shap.plots.waterfall(local_shap, show=False)
    plt.savefig(OUTPUT_DIR / f"{SYMBOL}_shap_local_latest.png")
    plt.close()


    print(
        f"✅ SHAP local explanation saved to "
        f"{OUTPUT_DIR / f'{SYMBOL}_shap_local_latest.png'}"
    )

if __name__ == "__main__":
    main()
