# Quant Research Platform

Real-data, reproducible quantitative research infrastructure. Walk-forward backtests on real S&P 500 daily closes, gradient-boosted-tree ML, point-in-time membership reconstruction, Deflated Sharpe, Probability of Backtest Overfitting. Every published number ships with a reproducibility manifest.

This is **research infrastructure**, not a fund. It does not place trades, does not forecast tomorrow's prices, and does not promise returns. See [TRUST.md](TRUST.md) for the credibility contract and what this repo refuses to claim.

## Headline numbers

All real, all reproducible. Run the demos in [REPRODUCE.md](REPRODUCE.md) to verify byte-for-byte.

| Run | Universe | Sharpe | DSR P | AnnRet | Max DD | Notes |
|---|---|---:|---:|---:|---:|---|
| `sp500_momentum_126`     | survivors-only (505) | 1.725 | 0.998 | 22.48% | 8.4%  | Headline momentum baseline |
| `sp500_momentum_126_pit` | point-in-time S&P 500 | 1.112 | 0.927 | 14.74% | 10.0% | Same strategy, joined-after bias removed |
| `sp500_ml_predictions_v1`| 100-symbol training subset | 1.408 | 1.000 | 16.06% | 8.0%  | LightGBM signal, calibrated probs |
| `sp500_momentum_sweep`   | 13 configs, raw universe | — | — | — | —    | **PBO = 0.557** (cross-config selection bias) |
| `sp500_momentum_sweep_pit` | 13 configs, PIT universe | — | — | — | —    | **PBO = 0.629** (selection bias under PIT) |

The honest reading: the headline 1.725 Sharpe inherits ~0.6 units of survivorship bias. The same strategy on a point-in-time universe is 1.112. The cross-config sweep PBO is borderline overfit. None of these numbers are alpha; all of them are honest.

## What's built

- **Walk-forward backtest engine** (`quant.backtest.engine`) — train 252 / test 21 days, equal-weight top-K, bps cost model, no shorting.
- **Multi-strategy signals** — `MomentumSignal`, `LowVolSignal`, `MeanReversionSignal`, `MLPredictionsSignal`. The ML signal replays a trained LightGBM model's OOF predictions through the same engine.
- **LightGBM trainer** (`quant.ml.trainer`) — triple-barrier labels (López de Prado AFML ch. 3), purged K-fold CV with embargo (AFML ch. 7), MLflow-tracked. One model, gradient-boosted decision trees, 26 features, 3-class output.
- **Probability calibration** (`quant.ml.calibration`) — isotonic per-class, ECE diagnostic raw + calibrated. Real macro ECE 0.0098 → 0.0056 on the demo run.
- **Deflated Sharpe Ratio** (Bailey & López de Prado 2014) — `quant.backtest.statistics.deflated_sharpe_ratio`.
- **Probability of Backtest Overfitting via CSCV** (López de Prado 2016) — `quant.backtest.statistics.probability_of_backtest_overfitting`.
- **Point-in-time S&P 500 membership** (`quant.universe.point_in_time`) — Wikipedia changes table → reverse-walk reconstruction → `members_as_of(date)`. Free, accurate from ~2000.
- **Universe filter wired into walk_forward** — backtest engine honors a `UniverseFilter` callable; `universe: sp500_pit` in any config enforces point-in-time at every rebalance.
- **Multi-config sweep** (`quant backtest sweep`) — runs N configs, computes cross-config PBO via CSCV.
- **Reproducibility manifest** (`quant.backtest.reproducibility`) — `code_sha + config_hash + data_fingerprint + python_version + package_versions + created_at`. House rule: no manifest, no publish.
- **FastAPI endpoints** — `/api/v1/backtests`, `/{name}`, `/{name}/equity`, `/{name}/manifest`, `/{name}/config`. Read-only, path-traversal hardened.
- **Web `/results` page** — Next.js 16, GSAP/Lenis motion, real numbers from on-disk artifacts (no runtime fetch). Renders KPI grid, PBO panel, 3-way strategy comparison, brutal disclaimer, equity curve, click-to-copy manifest, link to TRUST.md/REPRODUCE.md.
- **Paper-trading scaffold** (`quant.execution.paper_session` + `quant paper plan`) — broker-agnostic order computation, idempotent client_order_ids, sells-before-buys, JSON plan output. No live submission yet.
- **CI** — ruff, mypy --strict, pytest, eslint, tsc, next build, docker build (api + web), and a no-fake-data regex guard that fails the build on `Math.random` / `faker.` / `synthetic_data` / `mock_data` / etc. in production source paths.

## What's NOT built

Brutally:

- No live paper trading. `quant.execution.paper_session` computes orders; the daily worker that calls it on a schedule is unbuilt and needs an Alpaca paper API key.
- No public deploy. Locally-runnable; nothing is on the open internet at a domain.
- No live PnL track record. Backtest numbers only.
- No user accounts surfaced. Auth scaffolding exists; no signup UI.
- No mobile app, no native iOS/Android.
- No multi-asset (US equities only). No tick data.
- The "exited-and-removed-from-data" piece of survivorship bias is unfixed — kills the joined-after part for free via Wikipedia, but closing the rest needs Polygon Stocks / Sharadar / Norgate ($50–200/mo).

## Quickstart

```bash
# 1. Get the source data (Kaggle S&P 500 5y, ~28MB)
#    Place at: data/legacy/all_stocks_5yr.csv

# 2. Set up the API venv
cd apps/api
uv pip install --system -e ".[dev]"        # or: pip install -e ".[dev]"

# 3. Run the demo backtest
.venv/bin/python examples/backtest/prepare_sp500_5yr.py
.venv/bin/python -m quant.cli backtest run examples/backtest/sp500_momentum.yaml
# → Sharpe=1.725  DSR P=0.998  DD=8.4%  AnnRet=22.48%

# 4. Run the multi-config sweep
.venv/bin/python -m quant.cli backtest sweep examples/backtest/sp500_momentum_sweep.yaml
# → PBO=0.557  best mom_126_top10 Sharpe=1.753

# 5. Train a real LightGBM model end-to-end
MLFLOW_TRACKING_URI=file:///tmp/mlruns \
  .venv/bin/python -m quant.cli ml train examples/ml/sp500_lightgbm.yaml
# → logloss=0.9817  bal_acc=0.3643  macro_auc_ovr=0.6213

# 6. See what the model would buy on a given date
.venv/bin/python -m quant.cli paper plan examples/backtest/sp500_momentum.yaml \
  --as-of 2018-01-31 --portfolio-value 100000
# → 25 buy orders (NFLX, NVDA, AMZN, BA, ABBV, ...)

# 7. Reconstruct point-in-time S&P 500 membership for any date
.venv/bin/python -m quant.cli universe point-in-time --as-of 2014-01-02
# → 505 symbols (vs 503 today) — free, Wikipedia-sourced

# 8. Run the web app
cd ../web
npm ci && npm run build && npm run start
# → http://localhost:3000/results
```

Full reproducibility steps (recompute every manifest field, verify byte-exactness): see [REPRODUCE.md](REPRODUCE.md).

## Repository layout

```
apps/
  api/                    # FastAPI + Python 3.12
    src/quant/
      backtest/           # walk_forward, statistics, sweep, runner, signals, universe_filter
      ml/                 # trainer, calibration, config
      universe/           # constituents, point_in_time
      execution/          # broker, paper_session
      labels/             # triple_barrier
      cv/                 # purged_kfold
      features/           # technical features
      api/v1/             # FastAPI routers (auth, backtests, market, signals, admin)
    examples/
      backtest/           # YAML configs + tracked artifact bundles
      ml/                 # YAML configs + tracked artifact bundles
    tests/                # ruff + mypy strict + 100+ unit + integration tests
apps/
  web/                    # Next.js 16 + React 19 + Tailwind v4
    app/
      page.tsx            # marketing landing
      results/page.tsx    # /results — renders real backtest from artifact JSON
    components/oracle/    # KpiGrid, EquityCurve, HonestyBlock, ReproBlock, TrustFootnote
    lib/oracle/           # build-time artifact loader
    scripts/              # sync-oracle-artifacts.mjs (prebuild)
data/legacy/              # source CSV (gitignored, regenerable)
TRUST.md                  # credibility contract
REPRODUCE.md              # cold-start reproduction guide
FINAL_REPORT.md           # honest gap audit
```

## Math sources

- López de Prado, *Advances in Financial Machine Learning* (Wiley 2018) — chapters 3 (triple-barrier labels), 7 (purged K-fold + embargo), 12 (PBO via CSCV).
- Bailey & López de Prado, *The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality* (Journal of Portfolio Management, 2014).

## License

This is research infrastructure. It is not investment advice. Past backtest performance does not predict future returns. The platform does not place trades on your behalf. See [TRUST.md](TRUST.md) §4 for what this platform does not — and will not — claim.
