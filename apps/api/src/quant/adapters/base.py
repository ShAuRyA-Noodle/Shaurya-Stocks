"""
Base class for every HTTP provider adapter.

Gives each adapter:
- async httpx.AsyncClient with connection pooling
- token-bucket rate limiter (per-adapter calls-per-minute budget)
- tenacity retry with exponential backoff on TransientError + RateLimitError
- uniform error mapping (401/403 → AuthenticationError, 429 → RateLimitError,
  5xx / network → TransientError, other non-2xx → ProviderError)

Subclasses set `name`, `base_url`, `default_headers()`, and `calls_per_minute`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping
from types import TracebackType
from typing import Any, Self

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from quant.adapters.exceptions import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    TransientError,
)

log = logging.getLogger("quant.adapters")


# ================================================================
# Token-bucket rate limiter — simple, monotonic-clock based
# ================================================================
class TokenBucket:
    """Refills `capacity` tokens evenly over `per_seconds`. Async-safe."""

    def __init__(self, capacity: int, per_seconds: float) -> None:
        if capacity <= 0 or per_seconds <= 0:
            raise ValueError("capacity and per_seconds must be positive")
        self.capacity = float(capacity)
        self.per_seconds = float(per_seconds)
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: float = 1.0) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(
                    self.capacity,
                    self._tokens + elapsed * (self.capacity / self.per_seconds),
                )
                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return
                # sleep until we'd have enough
                need = tokens - self._tokens
                wait_s = need * (self.per_seconds / self.capacity)
                await asyncio.sleep(wait_s)


# ================================================================
# Base adapter
# ================================================================
class HttpAdapter(ABC):
    """Concrete adapters subclass this."""

    name: str = "provider"
    base_url: str = ""
    calls_per_minute: int = 60
    timeout_seconds: float = 30.0
    max_retries: int = 4

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout_seconds),
            limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
            headers=self.default_headers(),
        )
        self._bucket = TokenBucket(self.calls_per_minute, per_seconds=60.0)

    # ---------- subclass hooks ----------
    @abstractmethod
    def default_headers(self) -> dict[str, str]:
        """Auth/accept headers. Called once at client construction."""

    def _params_with_auth(self, params: Mapping[str, Any] | None) -> dict[str, Any]:
        """Override for APIs that put the key in the query string (Polygon, FRED, …)."""
        return dict(params or {})

    # ---------- context manager ----------
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    # ---------- HTTP ----------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        async for attempt in AsyncRetrying(
            reraise=True,
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=30),
            retry=retry_if_exception_type((TransientError, RateLimitError)),
        ):
            with attempt:
                await self._bucket.acquire()
                try:
                    resp = await self._client.request(
                        method,
                        path,
                        params=self._params_with_auth(params),
                        json=json,
                        headers=dict(headers) if headers else None,
                    )
                except (httpx.TimeoutException, httpx.NetworkError) as e:
                    raise TransientError(f"[{self.name}] network: {e}") from e

                if resp.is_success:
                    return resp

                body = resp.text
                if resp.status_code in (401, 403):
                    raise AuthenticationError(self.name, resp.status_code, body)
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    if retry_after:
                        with contextlib.suppress(ValueError):
                            await asyncio.sleep(min(float(retry_after), 60))
                    raise RateLimitError(self.name, resp.status_code, body)
                if 500 <= resp.status_code < 600:
                    raise TransientError(f"[{self.name}] HTTP {resp.status_code}: {body[:200]}")
                raise ProviderError(self.name, resp.status_code, body)
        raise TransientError(f"[{self.name}] retries exhausted")  # pragma: no cover

    async def get_json(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        resp = await self._request("GET", path, params=params, headers=headers)
        return resp.json()

    async def post_json(
        self,
        path: str,
        *,
        json: Any,
        headers: Mapping[str, str] | None = None,
    ) -> Any:
        resp = await self._request("POST", path, json=json, headers=headers)
        return resp.json()
