"""
SQLAlchemy 2.0 async engine, session factory, and declarative base.

Usage in routers:
    from quant.db import get_session
    async def route(session: AsyncSession = Depends(get_session)):
        ...

Usage in workers/scripts (sync):
    from quant.db import SyncSessionLocal
    with SyncSessionLocal() as s:
        ...
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy import create_engine

from quant.config import settings

# ---------------------------------------------------------------
# Naming convention — makes Alembic autogenerate predictable
# ---------------------------------------------------------------
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base with consistent naming + per-schema organization."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    # Useful default __repr__ for debugging
    def __repr__(self) -> str:
        pk = getattr(self, "id", None)
        return f"<{self.__class__.__name__} id={pk!r}>"


# ---------------------------------------------------------------
# Engines
# ---------------------------------------------------------------
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug and settings.app_log_level == "DEBUG",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)

sync_engine = create_engine(
    settings.database_url_sync,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engines() -> None:
    """Called on app shutdown."""
    await async_engine.dispose()
    sync_engine.dispose()
