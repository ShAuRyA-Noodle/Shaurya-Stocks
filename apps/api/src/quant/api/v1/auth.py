"""Auth endpoints — register, login, refresh, logout, me.

Access tokens are short-lived JWTs in the `Authorization: Bearer` header.
Refresh tokens are opaque random strings set as httpOnly cookies and rotated
on every `/refresh`.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quant.config import settings
from quant.core.dependencies import get_current_user, get_db
from quant.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from quant.db.models import RefreshToken, User, UserRole, UserTier

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "quant_refresh"


# ---------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str | None
    role: UserRole
    tier: UserTier
    is_active: bool
    is_verified: bool

    @classmethod
    def from_orm_user(cls, u: User) -> UserOut:
        return cls(
            id=str(u.id),
            email=u.email,
            full_name=u.full_name,
            role=u.role,
            tier=u.tier,
            is_active=u.is_active,
            is_verified=u.is_verified,
        )


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=raw_token,
        max_age=settings.jwt_refresh_ttl_days * 86_400,
        httponly=True,
        secure=settings.is_prod,
        samesite="lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


async def _issue_tokens(
    db: AsyncSession,
    user: User,
    response: Response,
    *,
    request: Request,
) -> TokenOut:
    raw, token_hash, expires_at = generate_refresh_token()
    db.add(RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        ip_address=(request.client.host if request.client else None),
    ))
    await db.commit()

    access = create_access_token(user.id, role=user.role.value, tier=user.tier.value)
    _set_refresh_cookie(response, raw)
    return TokenOut(access_token=access, expires_in=settings.jwt_access_ttl_minutes * 60)


# ---------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------
@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterIn, db: AsyncSession = Depends(get_db)) -> UserOut:
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.viewer,
        tier=UserTier.free,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserOut.from_orm_user(user)


@router.post("/login", response_model=TokenOut)
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenOut:
    user = (await db.execute(select(User).where(User.email == payload.email))).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account disabled")
    return await _issue_tokens(db, user, response, request=request)


@router.post("/refresh", response_model=TokenOut)
async def refresh_access_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> TokenOut:
    if not refresh_cookie:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing refresh cookie")

    token_hash = hash_refresh_token(refresh_cookie)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    rt = (await db.execute(stmt)).scalar_one_or_none()

    now = datetime.now(UTC)
    if rt is None or rt.revoked_at is not None or rt.expires_at <= now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")

    # Rotate: revoke old, issue new
    rt.revoked_at = now
    user = (await db.execute(select(User).where(User.id == rt.user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        await db.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")

    return await _issue_tokens(db, user, response, request=request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_cookie: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
) -> Response:
    if refresh_cookie:
        token_hash = hash_refresh_token(refresh_cookie)
        rt = (await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )).scalar_one_or_none()
        if rt is not None and rt.revoked_at is None:
            rt.revoked_at = datetime.now(UTC)
            await db.commit()
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.from_orm_user(user)
