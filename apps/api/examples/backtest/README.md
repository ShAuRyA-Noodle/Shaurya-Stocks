# Backtest runner — example

End-to-end demo of `quant backtest run` against the real
Kaggle [S&P 500 5-year OHLCV](https://www.kaggle.com/datasets/camnugent/sandp500) snapshot
that ships in `data/legacy/all_stocks_5yr.csv` (2013-02-08 → 2018-02-07, 505 symbols).

This is real arithmetic on real daily closes — no synthetic data.

## Steps

```bash
cd apps/api

# 1. Adapt the Kaggle schema (`close`, `Name`) to the runner schema (`adj_close`, `symbol`)
.venv/bin/python examples/backtest/prepare_sp500_5yr.py

# 2. Run the walk-forward backtest + publish the four-file artifact bundle
.venv/bin/python -m quant.cli backtest run examples/backtest/sp500_momentum.yaml
```

## Artifact bundle

Under `examples/backtest/artifacts/sp500_momentum_126/`:

| File | What |
| --- | --- |
| `report.json`         | headline metrics (Sharpe, Deflated Sharpe p, max DD, turnover, skew, kurt) |
| `equity_curve.csv`    | date → equity pairs across rebalances |
| `manifest.json`       | `code_sha`, `config_hash`, `data_fingerprint`, package versions |
| `config.snapshot.json` | exact config used — diffable, the source of truth for "what did we run" |

If any of those four files is missing, the run did not ship.

## How to authenticate a result

Cross-reference with `/TRUST.md` — a verified result carries:
- `manifest.json` with a non-empty `code_sha` and a 64-char `data_fingerprint`
- `report.json.metrics.deflated_sharpe_p` ≥ 0.95 (if `stats.n_trials` was set honestly)
- The config in `config.snapshot.json` must match the committed YAML (no drift).

Anything else is a story, not a result.
