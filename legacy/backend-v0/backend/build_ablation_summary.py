# backend/build_ablation_summary.py

import pandas as pd
from pathlib import Path

OUT = Path("reports/ablation/summary.csv")

rows = []

sources = {
    "TS Baseline (AAPL)": "reports/backtests/ts_baseline_results.csv",
    "Cross-Sectional": "reports/backtests/cross_sectional_results.csv",
    "Ensemble": "reports/backtests/ensemble_results.csv",
}

for name, path in sources.items():
    df = pd.read_csv(path)
    row = df.iloc[0].to_dict()
    row["Strategy"] = name
    rows.append(row)

summary = pd.DataFrame(rows)

# -------------------------
# KEEP ONLY COMMON COLUMNS
# -------------------------
summary = summary[
    ["Strategy", "Total Return", "CAGR", "Sharpe Ratio", "Max Drawdown"]
]

OUT.parent.mkdir(parents=True, exist_ok=True)
summary.to_csv(OUT, index=False)

print("✅ Ablation summary saved to", OUT)
print(summary)
