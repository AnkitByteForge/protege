"""Async engine/session factory (roadmap P9: "SQLAlchemy 2 + asyncpg").

Single settings source (``Settings.database_url``), matching
``migrations/env.py``'s own connection setup. Repositories and the jobs
worker take an ``AsyncSession`` they did not create -- this module only
supplies how to make one.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from ..settings import Settings, get_settings

_engines: dict[str, AsyncEngine] = {}
"""Keyed by ``database_url`` (a plain string, unlike ``Settings`` itself,
which is not guaranteed hashable) so repeated calls for the same database
reuse one connection pool, while tests constructing a ``Settings`` pointed
at a different URL each get their own engine."""


def get_engine(settings: Settings | None = None) -> AsyncEngine:
    resolved = settings if settings is not None else get_settings()
    engine = _engines.get(resolved.database_url)
    if engine is None:
        engine = create_async_engine(resolved.database_url, pool_pre_ping=True)
        _engines[resolved.database_url] = engine
    return engine


def get_sessionmaker(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(get_engine(settings), expire_on_commit=False)


async def dispose_all_engines() -> None:
    """Dispose every cached engine's connection pool and clear the cache.

    Must be awaited on the same event loop the engine(s) were created on --
    asyncpg connections are loop-bound. The real application calls this
    once, from its shutdown lifespan. The test suite (``tests/_db_helpers.py``)
    calls it at the end of every ``asyncio.run()``-driven test, since each
    test otherwise starts and tears down its own event loop while this
    module's cache would naively try to reuse a now-dead loop's pool.
    """
    for engine in list(_engines.values()):
        await engine.dispose()
    _engines.clear()


@asynccontextmanager
async def session_scope(settings: Settings | None = None) -> AsyncIterator[AsyncSession]:
    """One transaction: commits on clean exit, rolls back on exception."""
    maker = get_sessionmaker(settings)
    async with maker() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise
