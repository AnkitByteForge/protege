"""``Idempotency-Key`` semantics (roadmap P10 testing requirements 8, 9).

Covers: duplicate key + identical body -> exactly one state change; a
different key is independent; the guarantee survives a fresh
``session_scope()`` (simulating a process restart, since nothing but row ids
is held in memory between requests -- see ``repositories/idempotency.py``).
"""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key
from sqlalchemy import func, select

from protege.session_service.db.engine import session_scope
from protege.session_service.db.models import SessionRow


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def test_duplicate_idempotency_key_creates_exactly_one_session() -> None:
    async def scenario() -> None:
        sub = "user_idem_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        key = new_idempotency_key()

        async with api_client() as (client, _router):
            first = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": key},
            )
            second = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": key},
            )
            assert first.status_code == second.status_code == 201
            assert first.json() == second.json()

        async with session_scope() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(SessionRow)
                    .where(SessionRow.learner_id == learner_id)
                )
            ).scalar_one()
            assert count == 1

    run_async(scenario())


def test_different_idempotency_keys_are_independent() -> None:
    async def scenario() -> None:
        sub = "user_idem_2"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client() as (client, _router):
            first = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            second = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert first.status_code == second.status_code == 201
            assert first.json()["session_id"] != second.json()["session_id"]

        async with session_scope() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(SessionRow)
                    .where(SessionRow.learner_id == learner_id)
                )
            ).scalar_one()
            assert count == 2

    run_async(scenario())


def test_reusing_a_key_with_a_different_body_is_rejected() -> None:
    async def scenario() -> None:
        sub = "user_idem_3"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        other_learner_id = await create_linked_learner(clerk_user_id="user_idem_3_other")
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        key = new_idempotency_key()

        async with api_client() as (client, _router):
            first = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": key},
            )
            assert first.status_code == 201

            second = await client.post(
                "/v1/sessions",
                json={"learner_id": str(other_learner_id)},
                headers={**headers, "Idempotency-Key": key},
            )
            assert second.status_code == 409
            assert second.json()["child_safe_message"]

    run_async(scenario())


def test_idempotency_survives_a_fresh_session_scope() -> None:
    """The ledger lives in Postgres, not process memory -- a fresh
    ``session_scope()`` (this repo's stand-in for "a different process")
    still recognises the key and serves the cached result."""

    async def scenario() -> None:
        sub = "user_idem_4"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        key = new_idempotency_key()

        async with api_client() as (client_a, _router_a):
            first = await client_a.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": key},
            )
            assert first.status_code == 201

        async with api_client() as (client_b, _router_b):
            second = await client_b.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": key},
            )
            assert second.status_code == 201
            assert second.json() == first.json()

        async with session_scope() as session:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(SessionRow)
                    .where(SessionRow.learner_id == learner_id)
                )
            ).scalar_one()
            assert count == 1

    run_async(scenario())


def test_post_without_idempotency_key_is_rejected() -> None:
    async def scenario() -> None:
        sub = "user_idem_5"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        async with api_client() as (client, _router):
            response = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code in (400, 422)

    run_async(scenario())
