import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report

from backend.config import SYMBOL


DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

def load_data(symbol: str) -> pd.DataFrame:
    file_path = DATA_DIR / f"{symbol}_features.csv"
    if not file_path.exists():
        raise FileNotFoundError("Processed features not found.")
    return pd.read_csv(file_path)

def create_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Buy / Hold / Sell labeling using future returns (quantile-based)
    """
    df = df.copy()

    # Future 1-day return
    df["future_return"] = df["Close"].pct_change().shift(-1)

    # Quantile thresholds
    upper = df["future_return"].quantile(0.66)
    lower = df["future_return"].quantile(0.33)

    def label_fn(x):
        if x > upper:
            return 2   # Buy
        elif x < lower:
            return 0   # Sell
        else:
            return 1   # Hold

    df["label"] = df["future_return"].apply(label_fn)

    df = df.dropna().reset_index(drop=True)
    return df

def walk_forward_split(df, train_size=0.7):
    split_idx = int(len(df) * train_size)
    return df.iloc[:split_idx], df.iloc[split_idx:]

def train_baseline_model(df: pd.DataFrame):
    features = [
        "return_1d",
        "return_5d",
        "ma_5",
        "ma_20",
        "volatility_20",
        "rsi_14",
    ]

    X = df[features]
    y = df["label"]

    train_df, test_df = walk_forward_split(df)

    X_train, y_train = train_df[features], train_df["label"]
    X_test, y_test = test_df[features], test_df["label"]

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000))
    ])

    model.fit(X_train, y_train)
    import pickle
    from pathlib import Path

    MODEL_DIR = Path("models")
    MODEL_DIR.mkdir(exist_ok=True)

    with open(MODEL_DIR / f"{SYMBOL}_logreg.pkl", "wb") as f:
        pickle.dump(model, f)
    print("✅ Logistic Regression model saved")


    preds = model.predict(X_test)

    print("📊 Classification Report (Walk-Forward Validation):")
    print(classification_report(y_test, preds))

    return model

if __name__ == "__main__":
    df = load_data(SYMBOL)
    df = create_labels(df)
    model = train_baseline_model(df)

    model_path = MODEL_DIR / f"{SYMBOL}_baseline_logreg.pkl"
    pd.to_pickle(model, model_path)

    print(f"✅ Baseline model saved to {model_path}")
