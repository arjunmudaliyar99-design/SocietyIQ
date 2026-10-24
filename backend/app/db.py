"""Async engine, sessions and tenant context (docs/04 §4, §6).

The app connects as app_backend, which has no BYPASSRLS. Each request runs in one
transaction; the user and society ids are set with set_config(..., true), the function form
of SET LOCAL, so they vanish when the transaction ends and cannot leak between requests on a
pooled connection.
"""

from collections.abc import AsyncIterator
from functools import lru_cache
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("Set DATABASE_URL (app_backend role) to use the database")
    # The Supabase pooler in transaction mode cannot use prepared-statement caching (docs/04 §4).
    return create_async_engine(url, connect_args={"statement_cache_size": 0}, pool_pre_ping=True)


@lru_cache
def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(), expire_on_commit=False)


async def set_user_context(session: AsyncSession, user_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_user_id', :v, true)"), {"v": str(user_id)}
    )


async def set_society_context(session: AsyncSession, society_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_society_id', :v, true)"), {"v": str(society_id)}
    )


async def transaction() -> AsyncIterator[AsyncSession]:
    """One transaction per request: commit on success, roll back on any error."""
    async with get_sessionmaker()() as session, session.begin():
        yield session
