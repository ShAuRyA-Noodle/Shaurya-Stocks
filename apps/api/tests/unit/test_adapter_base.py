"""Unit tests for the adapter base — rate limiter, retry/error mapping."""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from quant.adapters.base import HttpAdapter, TokenBucket
from quant.adapters.exceptions import (
    AuthenticationError,
    ProviderError,
    RateLimitError,
    TransientError,
)


# ---------------------------------------------------------------
# TokenBucket
# ---------------------------------------------------------------
class TestTokenBucket:
    async def test_first_acquire_is_immediate(self) -> None:
        b = TokenBucket(capacity=5, per_seconds=1.0)
        t0 = time.monotonic()
        await b.acquire()
        assert time.monotonic() - t0 < 0.05

    async def test_blocks_when_empty(self) -> None:
        b = TokenBucket(capacity=2, per_seconds=0.4)  # 2 per 0.4s → 5/s
        for _ in range(2):
            await b.acquire()
        t0 = time.monotonic()
        await b.acquire()
        elapsed = time.monotonic() - t0
        assert elapsed >= 0.15  # refill wait

    def test_rejects_nonsense_capacity(self) -> None:
        with pytest.raises(ValueError):
            TokenBucket(capacity=0, per_seconds=1.0)
        with pytest.raises(ValueError):
            TokenBucket(capacity=1, per_seconds=0)


# ---------------------------------------------------------------
# HttpAdapter — error mapping via httpx MockTransport
# ---------------------------------------------------------------
class _ProbeAdapter(HttpAdapter):
    name = "probe"
    base_url = "https://probe.test"
    calls_per_minute = 10_000  # effectively unlimited for tests
    max_retries = 2

    def default_headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}


def _make(transport: httpx.MockTransport) -> _ProbeAdapter:
    client = httpx.AsyncClient(transport=transport, base_url="https://probe.test")
    return _ProbeAdapter(client=client)


class TestAdapterErrorMapping:
    async def test_success_returns_json(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"ok": True})

        a = _make(httpx.MockTransport(handler))
        assert await a.get_json("/x") == {"ok": True}
        await a.aclose()

    async def test_401_is_auth_error(self) -> None:
        a = _make(httpx.MockTransport(lambda r: httpx.Response(401, text="nope")))
        with pytest.raises(AuthenticationError):
            await a.get_json("/x")
        await a.aclose()

    async def test_400_is_provider_error(self) -> None:
        a = _make(httpx.MockTransport(lambda r: httpx.Response(400, text="bad")))
        with pytest.raises(ProviderError):
            await a.get_json("/x")
        await a.aclose()

    async def test_429_retries_then_raises(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(429, headers={"Retry-After": "0"}, text="slow down")

        a = _make(httpx.MockTransport(handler))
        with pytest.raises(RateLimitError):
            await a.get_json("/x")
        # max_retries=2 → 2 attempts total
        assert calls["n"] == 2
        await a.aclose()

    async def test_500_retries_then_raises_transient(self) -> None:
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            return httpx.Response(500, text="boom")

        a = _make(httpx.MockTransport(handler))
        with pytest.raises(TransientError):
            await a.get_json("/x")
        assert calls["n"] == 2
        await a.aclose()

    async def test_recovers_after_transient_500(self) -> None:
        state = {"calls": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            state["calls"] += 1
            if state["calls"] == 1:
                return httpx.Response(500)
            return httpx.Response(200, json={"ok": True})

        a = _make(httpx.MockTransport(handler))
        assert await a.get_json("/x") == {"ok": True}
        assert state["calls"] == 2
        await a.aclose()

    async def test_network_error_becomes_transient(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("nope")

        a = _make(httpx.MockTransport(handler))
        with pytest.raises(TransientError):
            await a.get_json("/x")
        await a.aclose()


# ---------------------------------------------------------------
# Param injection — subclasses overriding _params_with_auth
# ---------------------------------------------------------------
class _KeyInQueryAdapter(HttpAdapter):
    name = "kiq"
    base_url = "https://kiq.test"
    calls_per_minute = 10_000

    def default_headers(self) -> dict[str, str]:
        return {}

    def _params_with_auth(self, params):  # type: ignore[no-untyped-def]
        merged = dict(params or {})
        merged["apiKey"] = "secret"
        return merged


async def test_query_key_injection() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://kiq.test")
    a = _KeyInQueryAdapter(client=client)
    await a.get_json("/x", params={"foo": "1"})
    assert seen == {"foo": "1", "apiKey": "secret"}
    await a.aclose()


# ---------------------------------------------------------------
# Rate limit actually gates concurrency
# ---------------------------------------------------------------
class _SlowAdapter(HttpAdapter):
    name = "slow"
    base_url = "https://slow.test"
    calls_per_minute = 60  # 1 per second

    def default_headers(self) -> dict[str, str]:
        return {}


async def test_rate_limit_enforced() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://slow.test")
    a = _SlowAdapter(client=client)
    t0 = time.monotonic()
    # Burst of 3 — first immediate, next two wait ~1s each
    await asyncio.gather(a.get_json("/x"), a.get_json("/x"), a.get_json("/x"))
    elapsed = time.monotonic() - t0
    assert elapsed >= 1.5
    await a.aclose()
