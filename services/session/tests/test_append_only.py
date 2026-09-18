"""P9 exit gates 10-12: ``events``, ``evidence``, and ``safety_events`` are
append-only, enforced at the database boundary (``db/append_only.py``'s
trigger) -- not repository convention only. Each test attempts a raw
``UPDATE``/``DELETE`` directly against asyncpg, bypassing the repository
layer entirely, to prove the enforcement lives in the database itself.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import asyncpg
import pytest
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from sqlalchemy import text

from protege.session_service.db.engine import get_engine, session_scope
from protege.session_service.repositories.learners import LearnerRepository


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


async def _insert_event() -> str:
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO events (event_type, schema_version, occurred_at, payload) "
                "VALUES ('SESSION_STARTED', '1.0', :occurred_at, '{}'::jsonb) RETURNING id"
            ),
            {"occurred_at": datetime.now(UTC)},
        )
        return str(result.scalar_one())


async def _insert_learner_and_evidence(
    *, parent_email: str = "append-only-test@example.com"
) -> tuple[str, str]:
    engine = get_engine()
    async with engine.begin() as conn:
        parent_id = (
            await conn.execute(
                text(
                    "INSERT INTO parents (email, consent_version) "
                    "VALUES (:email, 'v1') RETURNING id"
                ),
                {"email": parent_email},
            )
        ).scalar_one()
        learner_id = (
            await conn.execute(
                text(
                    "INSERT INTO learners (parent_id, display_name, grade_band) "
                    "VALUES (:parent_id, 'Test', '3-4') RETURNING id"
                ),
                {"parent_id": parent_id},
            )
        ).scalar_one()
        event_id = (
            await conn.execute(
                text(
                    "INSERT INTO events (event_type, schema_version, occurred_at, payload) "
                    "VALUES ('ANSWER_SUBMITTED', '1.0', :occurred_at, '{}'::jsonb) RETURNING id"
                ),
                {"occurred_at": datetime.now(UTC)},
            )
        ).scalar_one()
        evidence_id = (
            await conn.execute(
                text(
                    "INSERT INTO evidence (learner_id, kind, source_event_id, weight, payload) "
                    "VALUES (:learner_id, 'response', :event_id, 1.0, '{}'::jsonb) RETURNING id"
                ),
                {"learner_id": learner_id, "event_id": event_id},
            )
        ).scalar_one()
        return str(learner_id), str(evidence_id)


async def _insert_safety_event(learner_id: str) -> str:
    engine = get_engine()
    async with engine.begin() as conn:
        result = await conn.execute(
            text(
                "INSERT INTO safety_events (learner_id, kind, severity, at) "
                "VALUES (:learner_id, 'test_kind', 'low', :at) RETURNING id"
            ),
            {"learner_id": learner_id, "at": datetime.now(UTC)},
        )
        return str(result.scalar_one())


async def _raw_connect() -> asyncpg.Connection:
    """A raw asyncpg connection to the same DB, bypassing SQLAlchemy
    entirely -- these tests prove the trigger blocks the write at the
    database boundary itself, not merely through the repository layer.

    ``Settings.database_url``'s ``?ssl=disable`` query parameter is
    SQLAlchemy-asyncpg-dialect-specific handling; asyncpg's own URL parser
    does not accept it the same way (``ssl=disable`` there raises
    ``CantChangeRuntimeParamError``), so the query string is dropped and
    ``ssl=False`` is passed as an explicit keyword instead -- matching
    the same "no TLS on the local Docker Compose stack" intent.
    """
    from protege.session_service.settings import get_settings

    dsn = (
        get_settings().database_url.replace("postgresql+asyncpg://", "postgresql://").split("?")[0]
    )
    return await asyncpg.connect(dsn, ssl=False)


def test_events_are_append_only() -> None:
    event_id = run_async(_insert_event())

    async def scenario() -> None:
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute("UPDATE events SET event_type = 'X' WHERE id = $1", event_id)
        finally:
            await conn.close()
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute("DELETE FROM events WHERE id = $1", event_id)
        finally:
            await conn.close()

    run_async(scenario())


def test_evidence_is_append_only() -> None:
    _learner_id, evidence_id = run_async(_insert_learner_and_evidence())

    async def scenario() -> None:
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute("UPDATE evidence SET weight = 2.0 WHERE id = $1", evidence_id)
        finally:
            await conn.close()
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute("DELETE FROM evidence WHERE id = $1", evidence_id)
        finally:
            await conn.close()

    run_async(scenario())


def test_safety_events_are_append_only() -> None:
    learner_id, _evidence_id = run_async(_insert_learner_and_evidence())
    safety_event_id = run_async(_insert_safety_event(learner_id))

    async def scenario() -> None:
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute(
                    "UPDATE safety_events SET severity = 'high' WHERE id = $1", safety_event_id
                )
        finally:
            await conn.close()
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute("DELETE FROM safety_events WHERE id = $1", safety_event_id)
        finally:
            await conn.close()

    run_async(scenario())


def test_append_only_escape_hatch_does_not_leak_across_transactions() -> None:
    """``LearnerRepository.delete`` sets ``protege.allow_cascade_write`` via
    ``SET LOCAL`` for exactly one transaction (see ``db/append_only.py``'s
    module docstring). This proves the guarantee, not just asserts it: run a
    real learner deletion (which legitimately bypasses the trigger for its
    own CASCADE/SET NULL writes), let that transaction commit, then -- on a
    brand new connection/transaction -- confirm ``evidence`` is still fully
    append-only-protected. If the escape hatch ever leaked past its own
    transaction, this second phase would silently succeed instead of raising.
    """
    learner_id, evidence_id = run_async(
        _insert_learner_and_evidence(parent_email="escape-hatch-leak-a@example.com")
    )

    async def delete_learner() -> None:
        async with session_scope() as session:
            await LearnerRepository(session).delete(uuid.UUID(learner_id))

    run_async(delete_learner())

    async def evidence_row_survived_as_orphaned_by_cascade() -> bool:
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT count(*) FROM evidence WHERE id = :id"), {"id": evidence_id}
            )
            return bool(result.scalar_one())

    # The deletion's CASCADE really did remove the evidence row (proves the
    # escape hatch worked for its one sanctioned purpose)...
    assert run_async(evidence_row_survived_as_orphaned_by_cascade()) is False

    # ...and now, on a fresh transaction with no learner deletion in
    # progress, append-only enforcement is still fully intact.
    remaining_learner_id, remaining_evidence_id = run_async(
        _insert_learner_and_evidence(parent_email="escape-hatch-leak-b@example.com")
    )
    del remaining_learner_id

    async def scenario() -> None:
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute(
                    "UPDATE evidence SET weight = 2.0 WHERE id = $1", remaining_evidence_id
                )
        finally:
            await conn.close()

    run_async(scenario())


def test_append_only_escape_hatch_does_not_survive_a_rollback() -> None:
    """Same guarantee as above, for the rollback path specifically (audit
    requirement: "confirm rollback restores normal append-only behavior").
    Forces the learner-deletion transaction to roll back after
    ``LearnerRepository.delete`` has already set the escape-hatch GUC and
    issued the cascading writes, then confirms both that the rollback
    genuinely undid the deletion and that append-only enforcement still
    holds afterward."""

    class _ForcedRollback(Exception):
        pass

    learner_id, evidence_id = run_async(_insert_learner_and_evidence())

    async def delete_then_force_rollback() -> None:
        with pytest.raises(_ForcedRollback):
            async with session_scope() as session:
                await LearnerRepository(session).delete(uuid.UUID(learner_id))
                raise _ForcedRollback

    run_async(delete_then_force_rollback())

    async def evidence_row_exists() -> bool:
        engine = get_engine()
        async with engine.begin() as conn:
            result = await conn.execute(
                text("SELECT count(*) FROM evidence WHERE id = :id"), {"id": evidence_id}
            )
            return bool(result.scalar_one())

    # Rolled back: the evidence row must still be there.
    assert run_async(evidence_row_exists()) is True

    async def scenario_after_rollback() -> None:
        conn = await _raw_connect()
        try:
            with pytest.raises(asyncpg.PostgresError, match="append-only"):
                await conn.execute("UPDATE evidence SET weight = 2.0 WHERE id = $1", evidence_id)
        finally:
            await conn.close()

    run_async(scenario_after_rollback())
