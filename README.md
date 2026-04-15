# Quant Signal Platform

Production-grade, real-data ML trading platform. No mocks, no fake numbers, no synthetic data — every value shown to a user is sourced from a real market feed and backed by a reproducible model run.

## What this is

An end-to-end stack that:

1. **Ingests** real OHLCV, fundamentals, news, macro, and alternative data from 11 integrated providers (Polygon, Alpaca, FRED, Finnhub, Tiingo, Marketaux, NewsAPI, FMP, Groq LLM, Nasdaq Data Link, Alpha Vantage).
2. **Engineers** features across price, momentum, mean-reversion, volume, microstructure, cross-sectional rank, macro, and LLM-scored news sentiment — leakage-free and walk-forward safe.
3. **Trains** a calibrated LightGBM ensemble (per-symbol time-series + cross-sectional ranker + HMM regime + stacked meta-learner) tracked in MLflow with purged K-fold CV.
4. **Backtests** event-driven with realistic costs, slippage, borrow, point-in-time universe, and against SPY / 60-40 / equal-weight benchmarks.
5. **Executes** through a broker-agnostic adapter (Alpaca paper → Alpaca live → IBKR later) with pre-trade risk checks, order state machine, and reconciliation.
6. **Streams** live quotes via WebSocket into Redis → signal workers → SSE to the frontend.
7. **Serves** a real-time Next.js dashboard with live P&L, SHAP explanations, backtest studio, model monitor, and audit log.

## Monorepo layout

```
.
├── apps/
│   ├── api/             # FastAPI backend (Python 3.12)
│   ├── web/             # Next.js 16 frontend (React 19)
│   └── worker/          # Prefect flows (ingest, features, inference, EOD)
├── packages/
│   └── schemas/         # Shared Pydantic + Zod contracts
├── data/
│   ├── raw/             # Raw provider dumps (gitignored)
│   ├── processed/       # Parquet feature stores
│   └── legacy/          # Pre-rewrite artifacts for reference
├── infra/
│   ├── postgres/        # DB init + migrations
│   ├── grafana/         # Dashboards
│   └── mlflow/          # MLflow server config
├── scripts/             # Backfill, seed, ops
└── docs/                # Architecture, runbooks, model cards
```

## Quickstart

```bash
# 1. Copy env template and fill in keys
cp .env.example .env.local
# edit .env.local with your API keys

# 2. Bring up the full stack (postgres+timescale, redis, minio, mlflow, api, web)
make up

# 3. Run migrations
make migrate

# 4. Backfill 10 years of OHLCV for S&P 500 + NASDAQ 100
make backfill

# 5. Train models
make train

# 6. Open the dashboard
open http://localhost:3000
```

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, Polars, LightGBM, SHAP, MLflow, Prefect |
| DB | Postgres 16 + TimescaleDB 2.x (hypertables for OHLCV/features/signals) |
| Cache/Queue/Stream | Redis 7 (streams, pubsub, rate limit) |
| Object store | MinIO (S3-compatible) for model artifacts + reports |
| Frontend | Next.js 16, React 19, Tailwind 4, Radix UI, TanStack Query, Zustand, Recharts |
| Auth | JWT + bcrypt + httpOnly cookies, role-based (viewer/trader/admin) |
| Observability | Structured logs (loguru + pino), Prometheus, Grafana, Sentry |
| CI | GitHub Actions (ruff, mypy, pytest, eslint, tsc, docker build) |

## Decision log

See [docs/decisions/](docs/decisions/) for ADRs. Summary:

- **Universe**: S&P 500 + NASDAQ 100 (~550 unique tickers), point-in-time membership.
- **Hosting**: Docker Compose local-first; cloud path pre-wired for Fly.io + Vercel + Neon + Upstash.
- **Paper vs live**: Broker abstraction from day one. Free users = read-only. Pro = paper with their own Alpaca keys. Premium = live (KYC-gated feature flag).
- **DB**: Postgres + TimescaleDB (single DB for both relational and time-series).
- **Model tracking**: MLflow with Postgres metadata + MinIO artifacts. Every signal carries a `model_run_id` for byte-for-byte replay.

## Anti-fake guarantees (enforced in CI)

- No hardcoded prices, returns, or confidences anywhere in the frontend. A CI check greps for suspicious literals in `apps/web/components/`.
- No `Math.random()` in production code paths. Allowed only in `*.test.tsx`.
- Every feature must declare its `point_in_time_safe: bool` in metadata. CI fails if any feature reads future data.
- Every backtest must output a reproducibility manifest (code hash, data hash, model hash). CI fails if missing.

## Status

**Sprint 1 — Foundation** (in progress)

See [CHANGELOG.md](CHANGELOG.md) for sprint-by-sprint progress.
