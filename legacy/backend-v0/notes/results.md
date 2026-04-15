# Results Interpretation

This section interprets the empirical results of the time-series (TS), cross-sectional (CS), and ensemble strategies, with an emphasis on *why* certain approaches outperform others and what trade-offs are introduced by risk-aware decision making.

---

## Why does the Cross-Sectional (CS) strategy outperform the Time-Series (TS) strategy?

The cross-sectional strategy consistently outperforms the time-series strategy because it exploits **relative mispricing across assets**, rather than attempting to forecast absolute returns.

Key reasons:

- **Noise cancellation:** Cross-sectional ranking removes common market noise that affects all assets simultaneously.
- **Stronger signal-to-noise ratio:** Selecting the best asset *relative to peers* is statistically easier than predicting direction in isolation.
- **Implicit market neutrality:** CS strategies naturally reduce exposure to broad market regimes.
- **Higher opportunity frequency:** Each trading day produces a ranking, whereas TS signals may remain neutral for long periods.

This aligns with well-established empirical finance results that cross-sectional alphas are more stable and persistent than pure time-series forecasts.

---

## Why does the Ensemble underperform the Cross-Sectional strategy?

The ensemble strategy intentionally underperforms in raw returns because it is **more conservative by design**.

Key factors:

- **Risk gating suppresses trades** during high-volatility or drawdown regimes.
- **Confidence thresholds reduce marginal trades** that may be profitable in hindsight but are statistically weak.
- **Signal agreement requirement:** Trades only occur when multiple independent signals align.

This is a deliberate trade-off: the ensemble sacrifices short-term return for **robustness, capital preservation, and regime awareness**.

Importantly, the ensemble avoids many of the worst periods experienced by the CS strategy, which is visible in the drawdown analysis.

---

## What does the Risk Gating mechanism trade off?

Risk gating trades **activity and aggressiveness** for **downside protection**.

Specifically:
- Fewer trades
- Lower turnover
- Reduced exposure during stress regimes

In exchange:
- Lower tail risk
- Fewer large drawdowns
- More stable behavior across regimes

This reflects real-world institutional constraints, where avoiding large losses is often more important than maximizing returns.

---

## Why does fewer trades NOT indicate a bad system?

In professional trading systems:
- **Capital preservation > activity**
- Many profitable systems trade infrequently
- “No trade” is a valid and often optimal decision

A system that always trades is usually:
- Overfit
- Regime-blind
- Fragile under stress

The ensemble’s ability to produce *zero-trade periods* demonstrates:
- Correct risk awareness
- Absence of forced behavior
- Honest signal uncertainty handling

---

## When would this system fail?

The system is expected to underperform in the following scenarios:

1. **Strong single-asset momentum markets**
   - Buy-and-hold strategies may outperform due to low diversification benefit.

2. **Highly correlated assets**
   - Cross-sectional ranking loses power when assets move identically.

3. **Sudden regime shifts**
   - Risk gating may react with lag during abrupt market transitions.

4. **Low volatility environments**
   - Conservative thresholds may suppress otherwise profitable trades.

These failure modes are acceptable and well-understood, and they reflect the system’s emphasis on robustness rather than aggressiveness.

---

## Summary

Overall, the results demonstrate a clear hierarchy:

- Cross-sectional signals provide the strongest raw alpha
- Ensemble logic improves robustness and risk control
- Risk gating reduces drawdowns at the cost of short-term returns
- Fewer trades reflect discipline, not weakness

This behavior is consistent with institutional-grade quantitative systems.


## Results Interpretation

### Why does the Time-Series baseline perform so well?
The time-series ML baseline benefits from persistent trends in a single high-quality asset (AAPL).
It exploits autocorrelation and momentum effects while remaining fully invested during favorable regimes.
However, it is exposed to concentration risk and regime shifts.

### Why does the Cross-Sectional strategy outperform in robustness?
The cross-sectional model ranks assets relative to each other, allowing capital to rotate into
the strongest opportunity each day. This reduces exposure to single-asset drawdowns and
improves stability at the cost of lower absolute returns.

### Why does the Ensemble underperform in raw returns?
The ensemble introduces explicit risk gating and confidence thresholds.
This reduces trade frequency and drawdowns but sacrifices short-term returns.
The result is a more conservative, capital-preserving strategy.

### Why are fewer trades not a weakness?
In production systems, inactivity is often a feature, not a bug.
Avoiding low-confidence environments prevents drawdowns and volatility spikes.
The ensemble is designed to trade only when multiple signals align.

### When would this system fail?
- Extended sideways markets with low dispersion
- Structural breaks invalidating historical relationships
- Regimes where cross-sectional relationships collapse

These limitations motivate ongoing monitoring and adaptive thresholds.


Overall, the cross-sectional strategy outperforms a single-asset time-series baseline
in risk-adjusted terms, while the ensemble further improves capital preservation
through explicit risk controls.
