"""Unit tests for core/security.py — password hashing + JWT + refresh tokens."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from quant.config import settings
from quant.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


# ---------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------
class TestPasswordHashing:
    def test_hash_is_not_plaintext(self) -> None:
        h = hash_password("correct horse battery staple")
        assert h != "correct horse battery staple"
        assert h.startswith("$2")  # bcrypt signature

    def test_verify_accepts_correct(self) -> None:
        h = hash_password("s3cret-passphrase-12")
        assert verify_password("s3cret-passphrase-12", h) is True

    def test_verify_rejects_wrong(self) -> None:
        h = hash_password("s3cret-passphrase-12")
        assert verify_password("s3cret-passphrase-13", h) is False

    def test_verify_is_constant_time_shape(self) -> None:
        # passlib wraps bcrypt which is inherently constant-time; just sanity-check it returns bool
        assert isinstance(verify_password("x", hash_password("y")), bool)

    def test_two_hashes_of_same_password_differ(self) -> None:
        a = hash_password("hello-world-1234")
        b = hash_password("hello-world-1234")
        assert a != b  # salts differ


# ---------------------------------------------------------------
# JWT access tokens
# ---------------------------------------------------------------
class TestAccessTokens:
    def test_roundtrip(self) -> None:
        uid = uuid.uuid4()
        tok = create_access_token(uid, role="viewer", tier="free")
        payload = decode_access_token(tok)
        assert payload["sub"] == str(uid)
        assert payload["role"] == "viewer"
        assert payload["tier"] == "free"
        assert payload["typ"] == "access"

    def test_extra_claims(self) -> None:
        tok = create_access_token(uuid.uuid4(), role="trader", tier="pro", extra_claims={"scope": "read"})
        assert decode_access_token(tok)["scope"] == "read"

    def test_rejects_tampered_token(self) -> None:
        tok = create_access_token(uuid.uuid4(), role="viewer", tier="free")
        with pytest.raises(TokenError):
            decode_access_token(tok + "x")

    def test_rejects_wrong_type(self) -> None:
        # Hand-craft a non-access token
        bad = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "typ": "refresh",
                "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
            },
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(TokenError):
            decode_access_token(bad)

    def test_rejects_expired(self) -> None:
        expired = jwt.encode(
            {
                "sub": str(uuid.uuid4()),
                "role": "viewer",
                "tier": "free",
                "typ": "access",
                "exp": int(time.time()) - 10,
            },
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
        with pytest.raises(TokenError):
            decode_access_token(expired)


# ---------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------
class TestRefreshTokens:
    def test_generate_returns_raw_hash_and_expiry(self) -> None:
        raw, h, exp = generate_refresh_token()
        assert len(raw) >= 40
        assert len(h) == 64  # sha256 hex
        assert exp > datetime.now(UTC)

    def test_hash_is_deterministic(self) -> None:
        raw, h, _ = generate_refresh_token()
        assert hash_refresh_token(raw) == h

    def test_raw_never_equals_hash(self) -> None:
        raw, h, _ = generate_refresh_token()
        assert raw != h

    def test_unique_each_call(self) -> None:
        a, _, _ = generate_refresh_token()
        b, _, _ = generate_refresh_token()
        assert a != b
