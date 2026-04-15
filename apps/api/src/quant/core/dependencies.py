"""FastAPI dependencies: DB session, current_user, role gates."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from quant.core.security import TokenError, decode_access_token
from quant.db import get_session
from quant.db.models import User, UserRole, UserTier

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=True)


async def get_db(session: AsyncSession = Depends(get_session)) -> AsyncSession:
    """Alias — exported so routers read `Depends(get_db)` consistently."""
    return session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
    except TokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing sub claim")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad sub claim") from e

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user not found or inactive")
    return user


def require_role(*roles: UserRole) -> Callable[..., Awaitable[User]]:
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return user

    return _checker


def require_tier(*tiers: UserTier) -> Callable[..., Awaitable[User]]:
    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.tier not in tiers:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "tier upgrade required")
        return user

    return _checker


get_current_admin = require_role(UserRole.admin)
get_current_trader = require_role(UserRole.trader, UserRole.admin)
