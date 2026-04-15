# backend/backtest_ensemble.py

import pandas as pd
import numpy as np
from pathlib import Path

SIGNAL_PATH = Path("reports/signals/final_ensemble_signals.csv")
FEATURE_DIR = Path("data/processed")
OUTPUT_DIR = Path("reports/backtests")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INITIAL_CAPITAL = 10000
TRANSACTION_COST = 0.001


# -------------------------
# METRIC HELPERS
# -------------------------
def compute_max_drawdown(equity: pd.Series):
    rolling_max = equity.cummax()
    drawdown = equity / rolling_max - 1
    return drawdown.min()


def load_prices(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(FEATURE_DIR / f"{symbol}_features.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df[["Date", "return_1d"]]


def main():
    signals = pd.read_csv(SIGNAL_PATH)

    equity = INITIAL_CAPITAL
    equity_curve = []

    # 🔑 Ensemble is a snapshot → apply from NEXT trading day
    for _, row in signals.iterrows():
        symbol = row["symbol"]
        decision = row["decision"]

        if decision != "BUY":
            continue

        price_df = load_prices(symbol)

        # Use next available day
        next_day = price_df.iloc[-1]
        daily_return = next_day["return_1d"] - TRANSACTION_COST

        equity *= (1 + daily_return)
        equity_curve.append(equity)

    if not equity_curve:
        print("⚠️ No trades executed")
        return

    # -------------------------
    # METRICS
    # -------------------------
    equity_curve = pd.Series(equity_curve)

    total_return = equity_curve.iloc[-1] / INITIAL_CAPITAL - 1
    cagr = (1 + total_return) ** (252 / len(equity_curve)) - 1

    returns = equity_curve.pct_change().dropna()
    if returns.std() < 1e-6:
        sharpe = 0.0
    else:
        sharpe = np.sqrt(252) * returns.mean() / returns.std()

    max_drawdown = compute_max_drawdown(equity_curve)

    # -------------------------
    # SAVE EQUITY CURVE
    # -------------------------
    equity_curve.to_csv(
        OUTPUT_DIR / "ensemble_equity_curve.csv",
        index=False
    )

    # -------------------------
    # SAVE RESULTS (PRODUCTION RULE)
    # -------------------------
    results = pd.DataFrame({
        "Total Return": [total_return],
        "CAGR": [cagr],
        "Sharpe": [sharpe],
        "Max Drawdown": [max_drawdown],
    })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(
        OUTPUT_DIR / "ensemble_results.csv",
        index=False
    )

    print("✅ Ensemble backtest results saved to reports/backtests/ensemble_results.csv")


if __name__ == "__main__":
    main()
