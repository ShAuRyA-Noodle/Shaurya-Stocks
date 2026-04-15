import pandas as pd
import numpy as np
from pathlib import Path
from xgboost import XGBClassifier
from sklearn.metrics import classification_report

from backend.config import SYMBOL

DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "return_1d",
    "return_5d",
    "ma_5",
    "ma_20",
    "volatility_20",
    "rsi_14",
]

def load_data(symbol: str) -> pd.DataFrame:
    path = DATA_DIR / f"{symbol}_features.csv"
    if not path.exists():
        raise FileNotFoundError("Processed features not found.")
    return pd.read_csv(path)

def create_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["future_return"] = df["Close"].pct_change().shift(-1)

    upper = df["future_return"].quantile(0.66)
    lower = df["future_return"].quantile(0.33)

    df["label"] = df["future_return"].apply(
        lambda x: 2 if x > upper else (0 if x < lower else 1)
    )

    return df.dropna().reset_index(drop=True)

def walk_forward_split(df, train_size=0.7):
    split = int(len(df) * train_size)
    return df.iloc[:split], df.iloc[split:]

def train_xgboost(df: pd.DataFrame):
    train_df, test_df = walk_forward_split(df)

    X_train, y_train = train_df[FEATURES], train_df["label"]
    X_test, y_test = test_df[FEATURES], test_df["label"]

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="multi:softmax",
        num_class=3,
        random_state=42,
        eval_metric="mlogloss",
    )

    model.fit(X_train, y_train)

    preds = model.predict(X_test)

    print("📊 XGBoost Classification Report:")
    print(classification_report(y_test, preds))

    return model

if __name__ == "__main__":
    df = load_data(SYMBOL)
    df = create_labels(df)

    model = train_xgboost(df)

    model_path = MODEL_DIR / f"{SYMBOL}_xgboost.pkl"
    pd.to_pickle(model, model_path)

    print(f"✅ XGBoost model saved to {model_path}")
