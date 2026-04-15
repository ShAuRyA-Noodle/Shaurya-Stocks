# backend/backtest_cross_sectional.py

import pandas as pd
import numpy as np
from pathlib import Path

SIGNAL_PATH = Path("reports/signals/cross_sectional_alpha.csv")
FEATURE_DIR = Path("data/processed")

OUTPUT_DIR = Path("reports/backtests")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

INITIAL_CAPITAL = 10000
TRANSACTION_COST = 0.001  # 10 bps


def load_prices(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(FEATURE_DIR / f"{symbol}_features.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df[["Date", "return_1d"]]


def main():
    signals = pd.read_csv(SIGNAL_PATH)
    signals["Date"] = pd.to_datetime(signals["Date"])

    equity = INITIAL_CAPITAL
    equity_curve = []
    chosen_symbols = []

    for date, daily in signals.groupby("Date"):
        top = daily.sort_values("rank").iloc[0]
        symbol = top["symbol"]

        price_df = load_prices(symbol)
        row = price_df[price_df["Date"] == date]

        if row.empty:
            continue

        daily_return = row["return_1d"].values[0]

        # ✅ STEP A1 — TRANSACTION COSTS
        strategy_return = daily_return - TRANSACTION_COST

        equity *= (1 + strategy_return)
        equity_curve.append(equity)
        chosen_symbols.append(symbol)

    equity_curve = pd.Series(equity_curve)

    total_return = equity_curve.iloc[-1] / INITIAL_CAPITAL - 1
    cagr = (1 + total_return) ** (252 / len(equity_curve)) - 1
    sharpe = (
        np.sqrt(252)
        * equity_curve.pct_change().mean()
        / equity_curve.pct_change().std()
    )

    # ✅ STEP A2 — TURNOVER METRIC
    symbol_series = pd.Series(chosen_symbols)
    turnover = (symbol_series != symbol_series.shift()).mean()

    print("\n📊 CROSS-SECTIONAL BACKTEST RESULTS")
    print(f"Total Return: {total_return:.2%}")
    print(f"CAGR: {cagr:.2%}")
    print(f"Sharpe: {sharpe:.2f}")
    print(f"Turnover: {turnover:.2%}")

    # ✅ STEP A3 — SAVE RESULTS AS CSV
    results = pd.DataFrame({
        "equity": equity_curve.values,
        "symbol": chosen_symbols,
    })

    output_path = OUTPUT_DIR / "cross_sectional_results.csv"
    results.to_csv(output_path, index=False)

    print(f"\n✅ Backtest results saved to {output_path}")

    # -------------------------
    # SAVE EQUITY CURVE
    # -------------------------
    equity_curve.to_csv(
        "reports/backtests/cross_sectional_equity_curve.csv",
        index=False
    )

    print("✅ Cross-sectional equity curve saved")


if __name__ == "__main__":
    main()
