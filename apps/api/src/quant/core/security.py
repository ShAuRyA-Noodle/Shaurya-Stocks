"""
Password hashing + JWT issuance/verification.

- Passwords: bcrypt via passlib (rounds from settings).
- Access tokens: short-lived JWT (30 min default) carrying sub=user_id, role, tier.
- Refresh tokens: opaque random strings; the raw value is returned to the client
  once, and only a SHA-256 hash is stored server-side. Rotation on every use.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from jose import JWTError, jwt
from passlib.context import CryptContext

from quant.config import settings

# ---------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------
_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)


def hash_password(plain: str) -> str:
    return cast(str, _pwd_context.hash(plain))


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return cast(bool, _pwd_context.verify(plain, hashed))
    except ValueError:
        return False


# ---------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------
class TokenError(Exception):
    """Raised for any JWT decode / validation failure."""


def create_access_token(
    user_id: uuid.UUID | str,
    *,
    role: str,
    tier: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "tier": tier,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_ttl_minutes)).timestamp()),
        "typ": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return cast(
        str,
        jwt.encode(
            payload,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        ),
    )


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as e:
        raise TokenError(f"invalid token: {e}") from e
    if payload.get("typ") != "access":
        raise TokenError("wrong token type")
    return cast(dict[str, Any], payload)


# ---------------------------------------------------------------
# Refresh tokens — opaque random, hashed at rest
# ---------------------------------------------------------------
def generate_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token, sha256_hash, expires_at). Only the hash is stored."""
    raw = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_ttl_days)
    return raw, token_hash, expires_at


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
