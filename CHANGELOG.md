# Changelog

All notable changes to this project will be documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Sprint 1 — Foundation (in progress)

- Monorepo consolidation into `apps/`, `packages/`, `infra/`, `data/`, `scripts/`, `docs/`.
- Root `.gitignore`, `README`, `CHANGELOG`, `Makefile`, `.env.example`.
- Docker Compose stack: Postgres 16 + TimescaleDB, Redis 7, MinIO, MLflow, Adminer, API, Web.
- Pydantic v2 `Settings` loading `.env.local` with strict validation of all provider keys.
- FastAPI skeleton with JWT auth scaffolding, structured logging, health endpoints.
- Postgres init script enabling TimescaleDB extension.
- Deleted pre-rewrite leaky models (`models/*.pkl`) — will retrain cleanly in Sprint 3.
- Fixed: stale-price bug in pricing module (freshness check).
- Fixed: `positions_value = 0.0` placeholder in portfolio snapshots (now mark-to-market).
- Fixed: duplicate daily-signal writes (idempotent upserts).
- Skipped (deferred): Reddit API (retail sentiment) and Anthropic API (Groq covers LLM duty).

### Planned

- **Sprint 2** — Real data: 11 provider adapters, 10y OHLCV backfill for S&P 500 + NASDAQ 100, Timescale hypertables, Prefect ingest flows.
- **Sprint 3** — Real ML: polars features, triple-barrier labels, purged K-fold, LightGBM ensemble, MLflow tracking, leakage-free backtest.
- **Sprint 4** — Real execution: broker adapter, order state machine, risk manager, mark-to-market, reconciliation.
- **Sprint 5** — Real streaming: Alpaca WebSocket, Redis streams, SSE endpoints, signal worker.
- **Sprint 6** — Real frontend: every component on real endpoints, TanStack Query, auth, mobile.
- **Sprint 7** — Ops: Prometheus/Grafana/Sentry, backups, kill switch, chaos tests, deploy.
- **Sprint 8** — Quant rigor: deflated Sharpe, PBO, reproducibility manifests, paper-trading proof period.
