"""Alembic runs as the database owner (MIGRATIONS_DATABASE_URL), never as app_backend.

See docs/04 §4.
"""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.config import get_settings


def _url() -> str:
    url = context.config.attributes.get("url") or get_settings().migrations_database_url
    if not url:
        raise RuntimeError("Set MIGRATIONS_DATABASE_URL to run migrations")
    return url


def _run(connection) -> None:  # noqa: ANN001
    context.configure(connection=connection, target_metadata=None)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(_url(), connect_args={"statement_cache_size": 0})
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline migrations are not supported")
asyncio.run(_run_async())
