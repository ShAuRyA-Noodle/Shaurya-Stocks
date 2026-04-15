import pandas as pd
import numpy as np
from pathlib import Path


DATA_DIR = Path("data/processed")
MODEL_DIR = Path("models")

SYMBOL = "AAPL"
INITIAL_CAPITAL = 10000
TRANSACTION_COST = 0.001  # 0.1% per trade

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
    return pd.read_pickle(MODEL_DIR / f"{symbol}_xgboost.pkl")


def generate_signals(df: pd.DataFrame, model) -> pd.DataFrame:
    df = df.copy()
    df["signal"] = model.predict(df[FEATURES])

    # Long-only positions (production baseline)
    df["position"] = (df["signal"] == 2).astype(int)

    return df


def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Use adjusted daily returns proxy
    df["market_return"] = df["return_1d"]

    # Shift position to avoid lookahead
    df["position_shifted"] = df["position"].shift(1).fillna(0)

    # Strategy returns
    df["strategy_return"] = df["position_shifted"] * df["market_return"]

    # Transaction cost only on position change
    df["trade"] = df["position_shifted"].diff().abs()
    df["strategy_return"] -= df["trade"] * TRANSACTION_COST

    # Equity curve
    df["equity_curve"] = INITIAL_CAPITAL * (1 + df["strategy_return"]).cumprod()

    return df.dropna().reset_index(drop=True)


def compute_metrics(df: pd.DataFrame):
    total_return = df["equity_curve"].iloc[-1] / INITIAL_CAPITAL - 1
    num_days = len(df)

    cagr = (1 + total_return) ** (252 / num_days) - 1

    sharpe = (
        np.sqrt(252)
        * df["strategy_return"].mean()
        / df["strategy_return"].std()
        if df["strategy_return"].std() > 0 else 0
    )

    rolling_max = df["equity_curve"].cummax()
    drawdown = df["equity_curve"] / rolling_max - 1
    max_drawdown = drawdown.min()

    return {
        "Total Return": total_return,
        "CAGR": cagr,
        "Sharpe Ratio": sharpe,
        "Max Drawdown": max_drawdown,
    }


if __name__ == "__main__":
    df = load_data(SYMBOL)
    model = load_model(SYMBOL)

    df = generate_signals(df, model)
    bt_df = run_backtest(df)

    metrics = compute_metrics(bt_df)

    # -------------------------
    # SAVE BASELINE RESULTS (RESEARCH CONTRACT)
    # -------------------------
    results = pd.DataFrame([metrics])

    output_path = Path("reports/backtests/ts_baseline_results.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(output_path, index=False)

    print(f"\n✅ Baseline results saved to {output_path}")
    print(results)
