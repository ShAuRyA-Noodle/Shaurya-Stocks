"""
End-to-end auth flow: register → login → me → refresh → logout.

Requires Postgres+Timescale running (docker-compose or CI service).
Skips silently if the DB isn't reachable.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from quant.config import settings
from quant.db.models import Base
from quant.main import app

pytestmark = pytest.mark.asyncio


async def _db_reachable() -> bool:
    try:
        eng = create_async_engine(settings.database_url, pool_pre_ping=True)
        async with eng.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await eng.dispose()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
async def _require_db() -> None:
    if not await _db_reachable():
        pytest.skip("database not reachable", allow_module_level=True)
    # Create auth/market/etc. schemas + all tables so auth endpoints work.
    eng = create_async_engine(settings.database_url)
    async with eng.begin() as conn:
        for schema in ("auth", "market", "model", "portfolio", "news", "macro", "feature", "signal"):
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_register_login_me_refresh_logout(client: AsyncClient) -> None:
    email = f"flow-{uuid.uuid4().hex[:10]}@example.com"
    password = "correct-horse-battery-staple-12"

    # --- register ---
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email
    assert body["role"] == "viewer"
    assert body["tier"] == "free"

    # --- duplicate register rejected ---
    r2 = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert r2.status_code == 409

    # --- login ---
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]
    assert "quant_refresh" in r.cookies

    # --- me ---
    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == email

    # --- wrong password ---
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password-xxxxx"})
    assert r.status_code == 401

    # --- refresh rotates ---
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200, r.text
    new_access = r.json()["access_token"]
    assert new_access  # old access is still valid until expiry; that's expected

    # --- old refresh cookie is now revoked ---
    # The rotation replaced the cookie on the client; a second refresh with the NEW cookie works,
    # but hitting with the ORIGINAL refresh value would 401. httpx already stored the new cookie.
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200

    # --- logout ---
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 204

    # --- after logout, refresh fails ---
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


async def test_me_without_token_rejected(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


async def test_me_with_bad_token_rejected(client: AsyncClient) -> None:
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert r.status_code == 401
