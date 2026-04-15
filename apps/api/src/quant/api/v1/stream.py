"""
Server-Sent Events (SSE) endpoint for real-time quote/trade/bar streaming.

A client connects to `/api/v1/stream?symbols=AAPL,MSFT&types=quote,trade` and
receives each message as a `data: {...}\\n\\n` SSE frame. The backend subscribes
to the Redis Pub/Sub channels populated by `AlpacaStreamer`.

We use SSE (not WebSocket) because:
- one-directional (market data only flows server→client)
- survives proxies/load balancers without extra config
- trivially reconnectable from EventSource in the browser
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis

from quant.config import settings
from quant.core.dependencies import get_current_user
from quant.db.models import User

log = logging.getLogger("quant.api.stream")
router = APIRouter(tags=["stream"])

_ALLOWED_TYPES = {"quote", "trade", "bar"}


async def _redis_client() -> Redis:
    return Redis.from_url(settings.redis_url)


async def _event_stream(
    symbols: list[str],
    types: list[str],
    redis: Redis,
) -> AsyncIterator[bytes]:
    channels = [f"{t}:{s}" for t in types for s in symbols]
    pubsub = redis.pubsub()
    await pubsub.subscribe(*channels)
    try:
        # Heartbeat so clients + proxies know the connection is alive.
        yield b": connected\n\n"
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
            if msg is None:
                yield b": ping\n\n"
                continue
            data = msg["data"]
            if isinstance(data, bytes):
                data = data.decode()
            yield f"event: {msg['channel'].decode()}\ndata: {data}\n\n".encode()
    except asyncio.CancelledError:
        raise
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.close()


@router.get("/stream")
async def stream(
    symbols: str = Query(..., description="comma-separated tickers, e.g. AAPL,MSFT"),
    types: str = Query("quote,trade,bar", description="quote|trade|bar"),
    _user: User = Depends(get_current_user),
    redis: Redis = Depends(_redis_client),
) -> StreamingResponse:
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    tys = [t.strip().lower() for t in types.split(",") if t.strip() in _ALLOWED_TYPES]
    if not syms or not tys:
        return StreamingResponse(iter([b"event: error\ndata: bad params\n\n"]), status_code=400)

    return StreamingResponse(
        _event_stream(syms, tys, redis),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
