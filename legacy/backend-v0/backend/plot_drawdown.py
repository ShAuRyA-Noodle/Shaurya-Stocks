# backend/plot_drawdown.py

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

PLOTS_DIR = Path("reports/plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

equity = pd.read_csv(
    "reports/backtests/cross_sectional_equity_curve.csv",
    header=None
).squeeze()

rolling_max = equity.cummax()
drawdown = equity / rolling_max - 1

plt.figure(figsize=(8, 5))
plt.plot(drawdown, color="red")
plt.title("Drawdown Curve (Cross-Sectional)")
plt.ylabel("Drawdown")
plt.xlabel("Time")
plt.grid(True)

out = PLOTS_DIR / "drawdown_curve.png"
plt.savefig(out, dpi=150)
plt.close()

print(f"✅ Drawdown curve saved to {out}")
