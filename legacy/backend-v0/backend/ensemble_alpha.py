# backend/ensemble_alpha.py

import pandas as pd
from pathlib import Path
import sys


SIGNAL_DIR = Path("reports/signals")
OUTPUT_DIR = Path("reports/signals")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ✅ EXPLICIT UNIVERSE (NO config imports)
UNIVERSE = ["AAPL", "MSFT"]


def load_time_series_signal(symbol):
    return pd.read_json(
        SIGNAL_DIR / f"{symbol}_latest_signal.json",
        typ="series"
    )


def load_cross_sectional_signal(symbol):
    df = pd.read_csv(SIGNAL_DIR / "cross_sectional_alpha.csv")
    return df.loc[df["symbol"] == symbol].iloc[-1]


# 🔑 SINGLE SOURCE OF TRUTH — RISK FILE
def load_risk(symbol):
    return pd.read_json(
        f"reports/risk/{symbol}_risk.json",
        typ="series"
    )


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "full_ensemble"

    ensemble_signals = []

    # ✅ ALWAYS LOOP OVER UNIVERSE
    for symbol in UNIVERSE:
        ts = load_time_series_signal(symbol)
        cs = load_cross_sectional_signal(symbol)
        risk = load_risk(symbol)

        cs_prob = cs["alpha_prob"]
        ts_conf = ts["confidence"]

        # -------------------------
        # ENSEMBLE SCORE
        # -------------------------
        if mode == "time_series_only":
            score = ts_conf
        elif mode == "cross_sectional_only":
            score = cs_prob
        else:
            score = 0.5 * cs_prob + 0.5 * ts_conf

        # Risk gate (UNCHANGED)
        if risk["risk_level"] == "HIGH":
            decision = "HOLD"
        else:
            decision = "BUY" if score > 0.50 else "HOLD"

        ensemble_signals.append({
            "symbol": symbol,
            "ensemble_score": round(score, 3),
            "decision": decision,
            "risk_level": risk["risk_level"],
        })

    df = pd.DataFrame(ensemble_signals)
    df.to_csv(OUTPUT_DIR / "ensemble_signals.csv", index=False)

    print("✅ Ensemble alpha signals generated")
    print(df)

    # ==================================================
    # ✅ FINAL SINGLE SOURCE OF TRUTH
    # ==================================================
    OUTPUT_PATH = Path("reports/signals/final_ensemble_signals.csv")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\n✅ Final ensemble signals saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
