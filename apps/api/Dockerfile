# ============================================================
# QUANT API — Dockerfile (Python 3.12, slim)
# Uses uv for fast, reproducible installs.
# ============================================================

FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src

# System deps: compiler toolchain for numpy/lightgbm, libgomp, postgres client
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libgomp1 \
        libpq-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast pip replacement)
RUN pip install --no-cache-dir uv==0.5.11

WORKDIR /app

# ---- Dependency layer (cached on pyproject.toml changes) ----
COPY pyproject.toml ./
RUN uv pip install --system --no-cache -e ".[dev]"

# ---- Source ----
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

# Healthcheck target
EXPOSE 8000

CMD ["uvicorn", "quant.main:app", "--host", "0.0.0.0", "--port", "8000"]
