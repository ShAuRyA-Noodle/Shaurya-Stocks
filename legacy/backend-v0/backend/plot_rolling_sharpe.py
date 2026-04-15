# backend/plot_rolling_sharpe.py

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

WINDOW = 20  # trading days

PLOTS_DIR = Path("reports/plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

equity = pd.read_csv(
    "reports/backtests/cross_sectional_equity_curve.csv",
    header=None
).squeeze()

returns = equity.pct_change().dropna()

rolling_sharpe = (
    returns.rolling(WINDOW).mean()
    / returns.rolling(WINDOW).std()
) * (252 ** 0.5)

plt.figure(figsize=(8, 5))
plt.plot(rolling_sharpe)
plt.title("Rolling Sharpe Ratio (Cross-Sectional)")
plt.ylabel("Sharpe")
plt.xlabel("Time")
plt.grid(True)

out = PLOTS_DIR / "rolling_sharpe.png"
plt.savefig(out, dpi=150)
plt.close()

print(f"✅ Rolling Sharpe plot saved to {out}")
