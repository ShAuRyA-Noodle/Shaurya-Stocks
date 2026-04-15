"""
Quant Signal Platform — FastAPI entry point.

Wires: settings, logging, CORS, routers, health, lifespan.
Sprint 1 scope: skeleton only (health + settings-bound + version).
Sprint 2+: real routers under /v1.
"""

from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from quant import __version__
from quant.api.v1 import api_router
from quant.config import settings
from quant.db import dispose_engines


# ---------------------------------------------------------------
# Logging (loguru comes in Sprint 6 — stdlib for now)
# ---------------------------------------------------------------
def _configure_logging() -> None:
    logging.basicConfig(
        level=settings.app_log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        stream=sys.stdout,
    )


# ---------------------------------------------------------------
# Lifespan: startup / shutdown hooks
# ---------------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    _configure_logging()
    log = logging.getLogger("quant.boot")
    log.info("Starting %s v%s in %s mode", settings.app_name, __version__, settings.app_env)

    providers = settings.provider_summary()
    configured = [k for k, v in providers.items() if v]
    missing = [k for k, v in providers.items() if not v]
    log.info("Providers configured: %s", ", ".join(configured) if configured else "NONE")
    if missing:
        log.warning("Providers NOT configured: %s", ", ".join(missing))

    yield

    log.info("Shutting down %s", settings.app_name)
    await dispose_engines()


# ---------------------------------------------------------------
# App factory
# ---------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title="Quant Signal Platform",
        version=__version__,
        description=(
            "Production-grade, real-data ML trading platform. "
            "Every value shown to a user is sourced from a real market feed."
        ),
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Health & meta ----
    @app.get("/", tags=["meta"])
    def root() -> dict[str, str]:
        return {"service": settings.app_name, "version": __version__, "env": settings.app_env}

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, object]:
        return {
            "status": "ok",
            "version": __version__,
            "env": settings.app_env,
            "providers": settings.provider_summary(),
        }

    @app.get("/readyz", tags=["meta"])
    def ready() -> dict[str, str]:
        # Sprint 2+: ping DB, Redis, broker, MLflow
        return {"status": "ready"}

    app.include_router(api_router)

    return app


app = create_app()
