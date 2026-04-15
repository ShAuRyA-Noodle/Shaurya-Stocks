# ============================================================
# QUANT PLATFORM — MAKEFILE
# One-command ops for the whole monorepo.
# ============================================================

COMPOSE        := docker compose -f infra/docker-compose.yml --env-file .env.local
API_CONTAINER  := quant-api
WEB_CONTAINER  := quant-web
DB_CONTAINER   := quant-postgres

.DEFAULT_GOAL := help
.PHONY: help up down restart logs ps clean nuke \
        api-shell web-shell db-shell redis-cli \
        migrate migrate-new migrate-down \
        test test-unit test-int lint format typecheck \
        backfill seed train backtest infer \
        web-install web-build web-lint \
        check ci

## ---------- HELP ----------
help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## ---------- STACK LIFECYCLE ----------
up: ## Start the full stack (postgres, redis, minio, mlflow, api, web, prefect)
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  ✅ Stack is up. Services:"
	@echo "     API         http://localhost:8000   (docs: /docs)"
	@echo "     Web         http://localhost:3000"
	@echo "     Adminer     http://localhost:8080   (server: postgres)"
	@echo "     MinIO       http://localhost:9001   (quant / quant_dev_minio)"
	@echo "     MLflow      http://localhost:5000"
	@echo "     Prefect     http://localhost:4200"
	@echo ""

down: ## Stop the stack (keeps volumes)
	$(COMPOSE) down

restart: down up ## Restart the stack

ps: ## List running services
	$(COMPOSE) ps

logs: ## Tail logs (use: make logs s=api)
	$(COMPOSE) logs -f $(s)

clean: ## Stop stack + prune dangling images
	$(COMPOSE) down --remove-orphans
	docker image prune -f

nuke: ## DANGER: Stop stack AND delete all volumes (wipes DB, MinIO, Redis)
	$(COMPOSE) down -v
	@echo "⚠️  All local data wiped."

## ---------- SHELLS ----------
api-shell: ## Bash into the API container
	docker exec -it $(API_CONTAINER) /bin/bash

web-shell: ## Shell into the web container
	docker exec -it $(WEB_CONTAINER) /bin/sh

db-shell: ## psql into the database
	docker exec -it $(DB_CONTAINER) psql -U quant -d quant

redis-cli: ## redis-cli into redis
	docker exec -it quant-redis redis-cli

## ---------- DATABASE MIGRATIONS (Alembic) ----------
migrate: ## Apply all pending migrations
	docker exec $(API_CONTAINER) alembic -c /app/alembic.ini upgrade head

migrate-new: ## Generate a new migration (use: make migrate-new m="add_users_table")
	docker exec $(API_CONTAINER) alembic -c /app/alembic.ini revision --autogenerate -m "$(m)"

migrate-down: ## Roll back one migration
	docker exec $(API_CONTAINER) alembic -c /app/alembic.ini downgrade -1

## ---------- TESTING / QUALITY ----------
test: ## Run all tests (pytest + vitest)
	docker exec $(API_CONTAINER) pytest -x --cov=src/quant --cov-report=term-missing
	docker exec $(WEB_CONTAINER) npm test --silent || true

test-unit: ## Run unit tests only
	docker exec $(API_CONTAINER) pytest tests/unit -x

test-int: ## Run integration tests
	docker exec $(API_CONTAINER) pytest tests/integration -x

lint: ## Lint Python + TypeScript
	docker exec $(API_CONTAINER) ruff check src tests
	docker exec $(WEB_CONTAINER) npm run lint --silent || true

format: ## Auto-format Python + TypeScript
	docker exec $(API_CONTAINER) ruff format src tests
	docker exec $(API_CONTAINER) ruff check --fix src tests

typecheck: ## Static type checks
	docker exec $(API_CONTAINER) mypy src
	docker exec $(WEB_CONTAINER) npx tsc --noEmit

check: lint typecheck test ## Run lint + typecheck + tests

ci: check ## Full CI pipeline (used in GitHub Actions)

## ---------- DATA / ML OPERATIONS ----------
backfill: ## Backfill 10y of OHLCV for S&P 500 + NASDAQ 100
	docker exec $(API_CONTAINER) python -m quant.workers.backfill_ohlcv

seed: ## Seed initial universe + macro series
	docker exec $(API_CONTAINER) python -m quant.workers.seed_universe
	docker exec $(API_CONTAINER) python -m quant.workers.seed_macro

train: ## Train the full model ensemble (tracked in MLflow)
	docker exec $(API_CONTAINER) python -m quant.workers.train_all

backtest: ## Run walk-forward backtest against the current model ensemble
	docker exec $(API_CONTAINER) python -m quant.workers.backtest_ensemble

infer: ## Run daily inference flow (features → predict → signals → risk)
	docker exec $(API_CONTAINER) python -m quant.workers.daily_inference

## ---------- WEB ----------
web-install: ## Install frontend dependencies
	docker exec $(WEB_CONTAINER) npm install

web-build: ## Build production frontend bundle
	docker exec $(WEB_CONTAINER) npm run build

web-lint:
	docker exec $(WEB_CONTAINER) npm run lint
