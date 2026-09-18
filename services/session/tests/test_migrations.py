"""P9 exit gates 1-3: Alembic upgrade/downgrade/upgrade against real
PostgreSQL 17 + pgvector, plus presence checks for the pgvector extension
and the ``embedding_records`` HNSW index (exit gate 16).

Runs last within its own module and restores ``head`` in a ``finally`` so
every other test module (which assumes the P9 schema already exists) is
unaffected regardless of test collection order.
"""

from __future__ import annotations

from pathlib import Path

from _db_helpers import ensure_p9_schema, require_postgres, run_async
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from protege.session_service.db.engine import get_engine

_REPO_ROOT = Path(__file__).resolve().parents[3]
_ALEMBIC_INI = _REPO_ROOT / "services" / "session" / "alembic.ini"


def _table_names() -> set[str]:
    async def _query() -> set[str]:
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            return {row[0] for row in result}

    return run_async(_query())


def test_upgrade_downgrade_upgrade_round_trip_is_deterministic() -> None:
    require_postgres()
    cfg = Config(str(_ALEMBIC_INI))

    try:
        command.upgrade(cfg, "head")
        tables_after_first_upgrade = _table_names()
        assert "evidence" in tables_after_first_upgrade
        assert "embedding_records" in tables_after_first_upgrade
        assert "jobs" in tables_after_first_upgrade

        command.downgrade(cfg, "0001_baseline")
        tables_after_downgrade = _table_names()
        assert "evidence" not in tables_after_downgrade
        assert "embedding_records" not in tables_after_downgrade

        command.upgrade(cfg, "head")
        tables_after_second_upgrade = _table_names()
        assert tables_after_second_upgrade == tables_after_first_upgrade
    finally:
        command.upgrade(cfg, "head")  # always leave the DB at head for other tests


def test_pgvector_extension_is_enabled() -> None:
    ensure_p9_schema()

    async def _query() -> set[str]:
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT extname FROM pg_extension"))
            return {row[0] for row in result}

    assert "vector" in run_async(_query())


def test_embedding_records_hnsw_index_exists() -> None:
    ensure_p9_schema()

    async def _query() -> list[str]:
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                text(
                    "SELECT indexdef FROM pg_indexes "
                    "WHERE tablename = 'embedding_records' AND indexname LIKE '%hnsw%'"
                )
            )
            return [row[0] for row in result]

    indexdefs = run_async(_query())
    assert len(indexdefs) == 1
    assert "USING hnsw" in indexdefs[0]
    assert "vector_cosine_ops" in indexdefs[0]
