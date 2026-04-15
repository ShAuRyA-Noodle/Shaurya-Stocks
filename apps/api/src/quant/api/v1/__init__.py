"""v1 API router aggregator."""

from fastapi import APIRouter

from quant.api.v1.auth import router as auth_router
from quant.api.v1.orders import router as orders_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(orders_router)

__all__ = ["api_router"]
