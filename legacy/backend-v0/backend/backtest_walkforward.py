import pandas as pd
import numpy as np
from pathlib import Path
import pickle

from backend.config import SYMBOL


DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")

INITIAL_CAPITAL = 10000
TRANSACTION_COST = 0.001
TRAIN_WINDOW = 252 * 2   # 2 years
TEST_WINDOW = 1          # predict 1 day at a time

FEATURES = [
    "return_1d",
    "return_5d",
    "ma_5",
    "ma_20",
    "volatility_20",
    "rsi_14",
]


def load_data():
    return pd.read_csv(DATA_DIR / f"{SYMBOL}_features.csv")


# =======================
# LOAD REGIMES
# =======================
def load_regimes(symbol: str) -> pd.DataFrame:
    path = Path("reports/regimes") / f"{symbol}_regimes.csv"
    if not path.exists():
        raise FileNotFoundError("Regime file not found. Run market_regime.py first.")
    return pd.read_csv(path)


# =======================
# WALK-FORWARD BACKTEST
# =======================
def run_walkforward(df: pd.DataFrame):
    # -------- LOAD & MERGE REGIMES --------
    regimes = load_regimes(SYMBOL)

    df = df.merge(
        regimes[["Date", "regime_label"]],
        on="Date",
        how="left"
    )

    df["regime_label"] = df["regime_label"].fillna("NEUTRAL")

    equity = INITIAL_CAPITAL
    equity_curve = []
    positions = []
    strategy_returns = []

    # -------- TRADE COOLDOWN --------
    cooldown = 3
    days_since_trade = cooldown

    for i in range(TRAIN_WINDOW, len(df) - TEST_WINDOW - 5):
        train = df.iloc[i - TRAIN_WINDOW:i].copy()
        test = df.iloc[i:i + TEST_WINDOW].copy()

        # -------- CREATE LABELS (NO LEAKAGE) --------
        future_return = train["return_5d"].shift(-5)

        train["label"] = 1  # HOLD
        train.loc[future_return > 0.01, "label"] = 2   # BUY
        train.loc[future_return < -0.01, "label"] = 0  # SELL

        train = train.dropna(subset=["label"])

        X_train = train[FEATURES]
        y_train = train["label"]

        from xgboost import XGBClassifier
        model = XGBClassifier(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            eval_metric="mlogloss",
            random_state=42
        )
        model.fit(X_train, y_train)

        # -------- CONFIDENCE-WEIGHTED POSITION SIZE --------
        X_test = test[FEATURES]
        proba = model.predict_proba(X_test)[0]
        buy_confidence = proba[2]

        if buy_confidence > 0.6:
            position = min(1.0, (buy_confidence - 0.6) / 0.4)
        else:
            position = 0.0

        # -------- REGIME FILTER --------
        if df.iloc[i]["regime_label"] == "HIGH_VOL_CHOPPY":
            position = 0.0

        # -------- TRADE COOLDOWN LOGIC --------
        if days_since_trade < cooldown:
            position = 0.0
            days_since_trade += 1
        else:
            if position != 0.0:
                days_since_trade = 0

        positions.append(position)

        daily_return = test["return_1d"].values[0]
        strategy_return = position * daily_return

        if len(positions) > 1 and positions[-1] != positions[-2]:
            strategy_return -= TRANSACTION_COST

        strategy_returns.append(strategy_return)

        equity *= (1 + strategy_return)
        equity_curve.append(equity)

    return pd.DataFrame({
        "equity": equity_curve,
        "strategy_return": strategy_returns
    })


# =======================
# METRICS
# =======================
def compute_metrics(df: pd.DataFrame):
    total_return = df["equity"].iloc[-1] / INITIAL_CAPITAL - 1
    cagr = (1 + total_return) ** (252 / len(df)) - 1

    if df["strategy_return"].std() < 1e-6:
        sharpe = 0.0
    else:
        sharpe = (
            np.sqrt(252)
            * df["strategy_return"].mean()
            / df["strategy_return"].std()
        )

    rolling_max = df["equity"].cummax()
    drawdown = df["equity"] / rolling_max - 1

    return {
        "Total Return": total_return,
        "CAGR": cagr,
        "Sharpe": sharpe,
        "Max Drawdown": drawdown.min()
    }


if __name__ == "__main__":
    df = load_data()
    result = run_walkforward(df)
    metrics = compute_metrics(result)

    print("\n📊 WALK-FORWARD BACKTEST RESULTS")
    for k, v in metrics.items():
        print(f"{k}: {v:.2%}")
