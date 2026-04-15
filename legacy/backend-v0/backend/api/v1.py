from fastapi import APIRouter

from backend.api.metrics import router as metrics_router
from backend.api.signals import router as signals_router
from backend.api.trades import router as trades_router

v1_router = APIRouter(prefix="/v1")

v1_router.include_router(metrics_router)
v1_router.include_router(signals_router)
v1_router.include_router(trades_router)
