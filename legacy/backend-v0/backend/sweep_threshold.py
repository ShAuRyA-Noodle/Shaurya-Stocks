# backend/sweep_threshold.py

import pandas as pd
import numpy as np
from pathlib import Path

SIGNALS = pd.read_csv("reports/signals/final_ensemble_signals.csv")

thresholds = np.arange(0.45, 0.65, 0.02)

rows = []

for t in thresholds:
    trades = SIGNALS[SIGNALS["ensemble_score"] > t]

    if len(trades) == 0:
        continue

    avg_score = trades["ensemble_score"].mean()

    rows.append({
        "threshold": round(t, 2),
        "num_trades": len(trades),
        "avg_score": round(avg_score, 3),
    })

df = pd.DataFrame(rows)

out = Path("reports/ablation/threshold_sweep.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)

print("✅ Threshold sweep saved to", out)
print(df)
