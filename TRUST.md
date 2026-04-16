# TRUST — why you can believe the numbers

**Date:** 2026-04-16
**Scope:** every published result from this repo.

This document answers two questions, in order:

1. **What is actually running under the hood?** (What ML method is used? What isn't?)
2. **Why should anyone believe a Sharpe or win-rate that comes out of it?**

No marketing language. If a thing is listed here, it is in `main` and you can
grep the code path. If a thing is *not* used, it is said plainly.

---

## 1. What ML is used — and what is not

### Used

- **LightGBM gradient-boosted decision trees** — `apps/api/src/quant/models/lightgbm_trainer.py`.
  - `objective: "multiclass"`, `num_class: 3`, labels ∈ {−1, 0, +1}.
  - Default params: `learning_rate: 0.05`, `num_leaves: 31`, `min_data_in_leaf: 50`,
    `feature_fraction: 0.8`, `bagging_fraction: 0.8`, L1/L2 = 0.1, `seed: 42`, `deterministic: True`.
  - Early stopping on validation log-loss (`early_stopping_rounds: 50`).
  - One booster per CV fold → inference averages `predict_proba` across folds.
- **scikit-learn** for metrics (`log_loss`, `accuracy_score`) and for the K-Fold primitive we extend.
- **Polars + NumPy** for feature pipelines and arithmetic.
- **MLflow** for experiment tracking, parameter logging, and metric history.

### Not used

- **No transformers.** No attention layers. No Keras/PyTorch/TensorFlow weights anywhere in the repo.
- **No LSTMs, GRUs, RNNs, CNNs.** No deep neural networks of any kind.
- **No generative AI in the signal path.** Groq/OpenAI keys exist for the news summarizer only; they never produce a trade decision or a number reported in a backtest.
- **No reinforcement learning.** No bandits, no policy-gradient, no Q-learning.
- **No hand-tuned technical-analysis oracles.** The model sees features; the tree splits decide.

You can verify this in ~5 seconds:

```bash
# Every ML entry point in the codebase:
ls apps/api/src/quant/models/            # → lightgbm_trainer.py only

# No deep-learning libraries anywhere:
grep -RE "torch|tensorflow|keras|transformers" apps/api/ || echo "clean"
```

There is exactly one model. It is LightGBM. Everything downstream of it
(ranking, signal writing, backtest, risk gate) is deterministic logic.

---

## 2. Why the results are believable

A Sharpe ratio pulled from a backtest is worth nothing on its own. The question
is: *what does this pipeline prevent?* Each mechanism below blocks a specific,
well-documented way that hobbyist quant results get inflated.

### 2.1 Triple-barrier labels — `apps/api/src/quant/labels/triple_barrier.py`

From each bar, three barriers are placed forward in time:

- upper = `close · (1 + pt_σ · σ_t)`
- lower = `close · (1 − sl_σ · σ_t)`
- vertical = `t + horizon` trading days

`σ_t` is the rolling std of log returns (default 21 days). The label is +1 /
−1 / 0 depending on which barrier the path touches first. This matters
because:

- The label is **path-dependent**, not `sign(ret_{t+N})`. Same-sized moves are
  stronger signals in a quiet regime than in a loud one — barriers scale with
  local vol, so the *meaning* of a label is stable across regimes.
- The model is not trained to predict a number; it is trained to discriminate
  upward-breakout paths from downward-breakout paths from drifts. That's a
  cleaner supervision target than raw forward returns.

Source: López de Prado, *Advances in Financial Machine Learning*, ch. 3.

### 2.2 Purged K-Fold CV + embargo — `apps/api/src/quant/cv/purged_kfold.py`

Plain K-Fold leaks information when labels overlap in time. A training bar
whose triple-barrier window ends *inside* a validation block shares path
information with that block — the model is effectively seeing the future.
This splitter does two things:

1. **Purge.** Any training sample whose `[start_i, end_i]` overlaps the
   validation block is dropped (`overlap = (ends >= val_start) & (starts < val_end)`).
2. **Embargo.** `embargo_frac` of bars (default 1%) immediately before and
   after each validation block are also dropped from training. This prevents
   leakage through serial correlation in returns.

If you remove either of those, you get a prettier Sharpe, but it is wrong.

Source: López de Prado, *AFML*, ch. 7.

### 2.3 Walk-forward backtest — `apps/api/src/quant/backtest/engine.py`

Train 252 trading days / test 21 trading days, rolled forward. Bar cost model
in basis points. Equal-weight top-K. No shorting. The engine never looks
beyond the current test window, so there is no in-sample tuning leaking into
the reported equity curve. The result is not a "fit" — it is a simulation of
what the pipeline would have produced in real time.

### 2.4 Deflated Sharpe Ratio — `apps/api/src/quant/backtest/statistics.py`

If you try `N` strategies and report the Sharpe of the best one, the reported
Sharpe is biased upward regardless of the underlying truth. DSR (Bailey &
López de Prado 2014) computes:

- `E[max_N]` — expected max of N iid standard normals, via the
  Euler-Mascheroni approximation `(1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(Ne))`.
- A non-normality adjustment using the returns' skew and kurtosis.
- `P(SR* > 0)` after the deflation.

Concretely: if you tried 100 strategies and picked the one with Sharpe 1.5,
DSR might say `P(SR* > 0) = 0.62`. That's a much more honest number than the
raw 1.5. The test at `tests/unit/test_backtest_statistics.py` proves
DSR **decreases** as `n_trials` grows — the more you searched, the harder it
is to beat selection bias.

### 2.5 Probability of Backtest Overfitting (PBO) via CSCV

Same file, `probability_of_backtest_overfitting`. Given a `(T × N)` matrix of
returns for `N` candidate strategies over `T` periods:

1. Cut `T` into `S` equal contiguous slices (default S = 16).
2. For every `C(S, S/2)` split of slices into in-sample / out-of-sample, find
   the best IS strategy; rank it in OOS.
3. Convert each rank to a logit; `PBO = fraction of negative logits`.

Interpretation: `PBO > 0.5` means the IS winner is *more likely than not* to
be a below-median performer out of sample — i.e. the selection pipeline is
overfitting. On pure iid noise with C(8,4)=70 trials the test returns
PBO ≈ 0.5 (proven in the unit test). On a strategy that actually dominates,
PBO is low.

### 2.6 Reproducibility manifest — `apps/api/src/quant/backtest/reproducibility.py`

Every published number ships with a manifest:

- `code_sha` — git HEAD at run time.
- `config_hash` — sha256 of canonical JSON of the run config.
- `data_fingerprint` — sha256 of sorted `(date, symbol, adj_close)` tuples.
- `python_version`, `package_versions` — environment snapshot.
- `created_at` — UTC timestamp.

House rule: **no manifest → no publish.** If a Sharpe is not attached to a
manifest, it is not a real Sharpe.

### 2.7 The zero-synthetic-data guard — CI

All eleven market-data providers hit real APIs with real keys. The CI
no-fake-data guard scans the whole repo for denylisted patterns:
`synthetic`, `fake_`, `dummy_data`, `mock_data`, `Math.random`, `faker.`,
`mulberry32`. Any match fails the build. A commit that invents numbers
cannot reach `main`.

### 2.8 Type safety

`mypy --strict` across every file under `apps/api/src/quant` (68 files).
Strict type-checking catches an entire class of silent bugs — wrong-shape
arrays, dropped nulls, mistyped metric units — that would otherwise corrupt a
reported number without anyone noticing.

---

## 3. How to authenticate a specific result

Given a claim like *"walk-forward Sharpe 1.7 on SP500 + NDX100 from 2018-2024"*:

1. Ask for the **manifest** (code_sha, config_hash, data_fingerprint).
2. `git checkout <code_sha>` → rerun the backtest with the same config → the
   data fingerprint of your re-pulled data must match.
3. The report must carry a **Deflated Sharpe P-value** alongside the raw
   Sharpe. If it says *"Sharpe 1.7, DSR P = 0.91, n_trials = 40"* — that's a
   real claim. If it just says *"Sharpe 1.7"* — reject it.
4. The report must carry a **PBO**. PBO < 0.3 is strong, 0.3–0.5 is
   marginal, > 0.5 is the model telling you the selection is overfit.
5. The report must carry an **MLflow run ID**. Every fold-level metric,
   hyperparameter, and artifact is logged there — you can re-walk the entire
   training trajectory.

If any of those four artifacts (manifest, DSR, PBO, MLflow run) is missing,
the number hasn't cleared the bar this repo sets for itself.

---

## 4. What this platform does not — and will not — claim

- It does not claim *predictive* power in the forecasting sense; it claims a
  *statistical edge* that survives purged CV, walk-forward simulation, and
  selection-bias deflation.
- It does not claim alpha on any specific symbol or date. Signals are
  ranked; the rank is the edge, not any one conviction number.
- It does not claim live-trading PnL. The broker path is real (Alpaca paper +
  live), the risk gate is real, but no results in this repo come from live
  executions — they come from walk-forward backtests on real historical
  provider data.
- It does not claim to be AI in any generative / LLM / transformer sense. The
  only learning algorithm in the trade-decision path is gradient-boosted
  trees.

---

## 5. The one-line summary

Gradient-boosted trees on triple-barrier labels, trained with purged K-Fold +
embargo, evaluated with walk-forward backtests, reported with Deflated Sharpe
and PBO, shipped with a reproducibility manifest. On real market data from
eleven keyed providers. No fake data, no deep-learning theatre, no numbers
without a manifest attached.
