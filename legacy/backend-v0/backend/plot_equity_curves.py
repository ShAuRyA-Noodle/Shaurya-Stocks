# backend/plot_equity_curves.py

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

PLOTS_DIR = Path("reports/plots")
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

cs_curve = pd.read_csv(
    "reports/backtests/cross_sectional_equity_curve.csv",
    header=None
).squeeze()

ens_curve = pd.read_csv(
    "reports/backtests/ensemble_equity_curve.csv",
    header=None
).squeeze()

plt.figure(figsize=(8, 5))

plt.plot(cs_curve.values, label="Cross-Sectional")
plt.plot(ens_curve.values, label="Ensemble")

plt.title("Equity Curve Comparison")
plt.ylabel("Equity")
plt.xlabel("Trades")
plt.legend()
plt.grid(True)

output = PLOTS_DIR / "equity_curves.png"
plt.savefig(output, dpi=150)
plt.close()

print(f"✅ Equity curve plot saved to {output}")
