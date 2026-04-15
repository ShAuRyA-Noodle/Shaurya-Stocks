"""
Alpaca market-data WebSocket consumer.

Subscribes to trade/quote/bar streams, parses messages, and publishes them
to Redis Pub/Sub channels `quote:{symbol}`, `trade:{symbol}`, `bar:{symbol}`
so the API layer can fan them out to SSE subscribers.

Ref: https://docs.alpaca.markets/docs/real-time-stock-pricing-data
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Iterable
from typing import Any

import websockets
from redis.asyncio import Redis
from websockets import ConnectionClosed
from websockets.asyncio.client import ClientConnection

from quant.config import settings

log = logging.getLogger("quant.streaming.alpaca_ws")

# IEX feed is free for paper accounts; SIP requires the paid plan.
ALPACA_WS_URL = "wss://stream.data.alpaca.markets/v2/iex"


class AlpacaStreamer:
    def __init__(
        self,
        symbols: Iterable[str],
        *,
        redis: Redis,
        url: str = ALPACA_WS_URL,
        reconnect_max: int = 60,
    ) -> None:
        self.symbols = [s.upper() for s in symbols]
        self.redis = redis
        self.url = url
        self.reconnect_max = reconnect_max
        self._stop = asyncio.Event()

    async def stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        """Consume forever with exponential backoff on disconnect."""
        delay = 1
        while not self._stop.is_set():
            try:
                async with websockets.connect(self.url) as ws:
                    await self._authenticate(ws)
                    await self._subscribe(ws)
                    delay = 1
                    await self._consume(ws)
            except ConnectionClosed as e:
                log.warning("alpaca ws closed: %s — reconnecting in %ss", e, delay)
            except Exception:
                log.exception("alpaca ws error — reconnecting in %ss", delay)
            if self._stop.is_set():
                break
            await asyncio.sleep(delay)
            delay = min(delay * 2, self.reconnect_max)

    async def _authenticate(self, ws: ClientConnection) -> None:
        msg = {
            "action": "auth",
            "key": settings.alpaca_api_key_id.get_secret_value(),
            "secret": settings.alpaca_api_secret_key.get_secret_value(),
        }
        await ws.send(json.dumps(msg))
        raw = await ws.recv()
        data = json.loads(raw)
        if not any(m.get("T") == "success" and m.get("msg") == "authenticated" for m in data):
            raise RuntimeError(f"alpaca ws auth failed: {data}")

    async def _subscribe(self, ws: ClientConnection) -> None:
        msg = {
            "action": "subscribe",
            "trades": self.symbols,
            "quotes": self.symbols,
            "bars": self.symbols,
        }
        await ws.send(json.dumps(msg))
        # Server replies with a subscription confirmation — drain it.
        await ws.recv()
        log.info("alpaca ws subscribed to %d symbols", len(self.symbols))

    async def _consume(self, ws: ClientConnection) -> None:
        async for raw in ws:
            if self._stop.is_set():
                break
            for msg in json.loads(raw):
                await self._publish(msg)

    async def _publish(self, msg: dict[str, Any]) -> None:
        t = msg.get("T")
        sym = msg.get("S")
        if not sym:
            return
        channel = {"t": "trade", "q": "quote", "b": "bar"}.get(t or "")
        if channel is None:
            return
        await self.redis.publish(f"{channel}:{sym}", json.dumps(msg))
