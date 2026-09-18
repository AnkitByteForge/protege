"""Shared DB-test helpers for the P9 persistence test suite.

No ``pytest-asyncio``/``anyio`` plugin dependency is added: every DB test is
a plain sync function that drives one coroutine via ``run_async`` (stdlib
``asyncio.run``), matching this repo's existing convention of not carrying
test-only framework weight beyond what a package already needs
(AGENTS.md: "Do not introduce a new framework ... without explaining why").

Named ``_db_helpers`` (leading underscore, not ``conftest``), following
``packages/thin-thread/tests/_helpers.py``'s own precedent for the same
reason documented there: no test directory in this monorepo uses
``__init__.py`` packages, so a second literal ``conftest.py`` name would
collide across directories under pytest's flat module cache.
"""

from __future__ import annotations

import asyncio
import socket
from collections.abc import Coroutine
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from alembic import command
from alembic.config import Config

from protege.session_service.db.engine import dispose_all_engines, get_engine
from protege.session_service.db.models import Base
from protege.session_service.settings import get_settings

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _REPO_ROOT / "services" / "session" / "alembic.ini"


def run_async[T](coro: Coroutine[object, object, T]) -> T:
    """``asyncio.run`` a coroutine, then dispose the cached SQLAlchemy
    engine(s) on that same loop before it closes.

    Each call here starts and tears down its own event loop (there is no
    ``pytest-asyncio``/``anyio`` session-wide loop -- see module docstring),
    but ``db.engine.get_engine`` caches one ``AsyncEngine`` per database URL
    for the lifetime of the *process* (the right behaviour for the real,
    single-event-loop application). Without disposing here, a second test's
    ``asyncio.run`` would try to reuse a connection pool bound to the first
    test's now-closed loop and fail with ``RuntimeError: Event loop is
    closed`` -- an asyncpg/loop-lifetime mismatch, not a P9 code defect.
    """

    async def _wrapped() -> T:
        try:
            return await coro
        finally:
            await dispose_all_engines()

    return asyncio.run(_wrapped())


def _postgres_reachable(database_url: str) -> bool:
    parts = urlsplit(database_url.replace("postgresql+asyncpg://", "postgresql://"))
    host = parts.hostname or "localhost"
    port = parts.port or 5432
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


def require_postgres() -> None:
    """Skip the calling test if Postgres is not reachable at
    ``Settings.database_url`` -- keeps ``make test``/bare ``pytest`` usable
    on a machine without ``make db-up`` run, while still exercising the
    real P9 schema whenever Postgres is available (this repo's Docker
    Compose default, and CI's Postgres service container)."""
    settings = get_settings()
    if not _postgres_reachable(settings.database_url):
        pytest.skip("Postgres not reachable at DATABASE_URL -- run `make db-up` first")


_schema_ensured = False


def ensure_p9_schema() -> None:
    """Apply P9 migrations once per test process. Idempotent: Alembic's own
    ``upgrade head`` is a no-op once already at head."""
    global _schema_ensured
    require_postgres()
    if _schema_ensured:
        return
    cfg = Config(str(_ALEMBIC_INI))
    command.upgrade(cfg, "head")
    _schema_ensured = True


async def truncate_all_p9_tables() -> None:
    """Reset every P9 table between tests. A single ``TRUNCATE ... CASCADE``
    (not per-row ``DELETE``) so it bypasses the append-only triggers
    entirely (Postgres does not fire ``FOR EACH ROW`` triggers on
    ``TRUNCATE``) and handles every foreign-key dependency in one
    statement regardless of table order."""
    table_names = ", ".join(name for name in Base.metadata.tables if name != "alembic_version")
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.exec_driver_sql(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
