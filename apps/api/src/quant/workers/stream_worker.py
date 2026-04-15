"""
Standalone worker that runs the Alpaca WS → Redis pipeline.

Usage:
    python -m quant.workers.stream_worker

Symbols come from the universe table (`market.tickers` where is_active = true).
If the universe is empty, we exit with a clear error — we never hallucinate
tickers.
"""

from __future__ import annotations

import asyncio
import logging
import signal

from redis.asyncio import Redis
from sqlalchemy import select

from quant.config import settings
from quant.db import get_session
from quant.db.models import Ticker
from quant.streaming import AlpacaStreamer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("quant.workers.stream")


async def _load_symbols() -> list[str]:
    async for session in get_session():
        rows = (
            (
                await session.execute(
                    select(Ticker.symbol).where(Ticker.is_active.is_(True)).order_by(Ticker.symbol)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)
    return []


async def main() -> None:
    symbols = await _load_symbols()
    if not symbols:
        raise SystemExit("No active tickers in market.tickers — seed the universe first.")

    log.info("streaming %d symbols", len(symbols))
    redis = Redis.from_url(settings.redis_url)
    streamer = AlpacaStreamer(symbols, redis=redis)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(streamer.stop()))

    try:
        await streamer.run()
    finally:
        await redis.close()


if __name__ == "__main__":
    asyncio.run(main())
