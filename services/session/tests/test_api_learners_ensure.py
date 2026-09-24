"""``POST /v1/learners/ensure`` (roadmap product-entry milestone).

Covers: first-call creation, idempotency by ``clerk_user_id`` (repeat calls
and a parent already linked by some other path both reuse, never
duplicate), the missing-``email``-claim failure, unauthenticated rejection,
and that a caller can never reach another user's learner. See
``routes/learners.py``'s ``ensure_learner_route`` and
``repositories/learners.py``'s ``get_or_create_parent_for_clerk_user``/
``get_or_create_default_learner``.
"""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key
from sqlalchemy import func, select

from protege.session_service.db.engine import session_scope
from protege.session_service.db.models import Learner, Parent
from protege.session_service.repositories.learners import LearnerRepository


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def test_first_ensure_call_creates_parent_and_learner() -> None:
    async def scenario() -> None:
        sub = "user_ensure_1"
        token = mint_token(sub=sub, role="parent", email="ensure1@example.com")

        async with api_client() as (client, _router):
            response = await client.post(
                "/v1/learners/ensure",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["display_name"]
            learner_id = body["learner_id"]

        async with session_scope() as session:
            parent = await LearnerRepository(session).get_parent_by_clerk_user_id(sub)
            assert parent is not None
            assert parent.email == "ensure1@example.com"

            learner = await session.get(Learner, learner_id)
            assert learner is not None
            assert str(learner.parent_id) == str(parent.id)

    run_async(scenario())


def test_repeat_ensure_call_is_idempotent_no_duplicates() -> None:
    async def scenario() -> None:
        sub = "user_ensure_2"
        token = mint_token(sub=sub, role="parent", email="ensure2@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client() as (client, _router):
            first = await client.post(
                "/v1/learners/ensure",
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            second = await client.post(
                "/v1/learners/ensure",
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert first.status_code == second.status_code == 200
            assert first.json() == second.json()

        async with session_scope() as session:
            parent_count = (
                await session.execute(
                    select(func.count()).select_from(Parent).where(Parent.clerk_user_id == sub)
                )
            ).scalar_one()
            assert parent_count == 1

            parent = await LearnerRepository(session).get_parent_by_clerk_user_id(sub)
            assert parent is not None
            learner_count = (
                await session.execute(
                    select(func.count()).select_from(Learner).where(Learner.parent_id == parent.id)
                )
            ).scalar_one()
            assert learner_count == 1

    run_async(scenario())


def test_ensure_reuses_a_parent_already_linked_by_another_path() -> None:
    """A parent linked via the existing test/demo ``create_linked_learner``
    helper (mirroring, e.g., a row seeded by ``scripts/e2e_server.py``) must
    be reused, not duplicated, and its existing learner returned as-is."""

    async def scenario() -> None:
        sub = "user_ensure_3"
        learner_id = await create_linked_learner(clerk_user_id=sub, email="preexisting@example.com")
        token = mint_token(sub=sub, role="parent", email="preexisting@example.com")

        async with api_client() as (client, _router):
            response = await client.post(
                "/v1/learners/ensure",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 200, response.text
            assert response.json()["learner_id"] == str(learner_id)

        async with session_scope() as session:
            parent_count = (
                await session.execute(
                    select(func.count()).select_from(Parent).where(Parent.clerk_user_id == sub)
                )
            ).scalar_one()
            assert parent_count == 1

    run_async(scenario())


def test_ensure_without_email_claim_fails_safely_for_a_new_parent() -> None:
    async def scenario() -> None:
        sub = "user_ensure_4"
        token = mint_token(sub=sub, role="parent")  # no email claim

        async with api_client() as (client, _router):
            response = await client.post(
                "/v1/learners/ensure",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 400, response.text
            body = response.json()
            assert body["type"] == "protege:email-claim-missing"
            assert body["child_safe_message"]

        async with session_scope() as session:
            parent = await LearnerRepository(session).get_parent_by_clerk_user_id(sub)
            assert parent is None

    run_async(scenario())


def test_ensure_requires_authentication() -> None:
    async def scenario() -> None:
        async with api_client() as (client, _router):
            response = await client.post(
                "/v1/learners/ensure", headers={"Idempotency-Key": new_idempotency_key()}
            )
            assert response.status_code == 401

    run_async(scenario())


def test_ensure_never_returns_another_users_learner() -> None:
    async def scenario() -> None:
        token_a = mint_token(sub="user_ensure_5a", role="parent", email="a5@example.com")
        token_b = mint_token(sub="user_ensure_5b", role="parent", email="b5@example.com")

        async with api_client() as (client, _router):
            resp_a = await client.post(
                "/v1/learners/ensure",
                headers={
                    "Authorization": f"Bearer {token_a}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            resp_b = await client.post(
                "/v1/learners/ensure",
                headers={
                    "Authorization": f"Bearer {token_b}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert resp_a.status_code == resp_b.status_code == 200
            assert resp_a.json()["learner_id"] != resp_b.json()["learner_id"]

    run_async(scenario())


def test_ensured_learner_can_start_a_real_session() -> None:
    """The end of the product-entry chain: the id ``/v1/learners/ensure``
    returns is a real, ownable learner that the existing, unmodified
    ``POST /v1/sessions`` accepts -- proving the new endpoint composes with
    the session-creation flow rather than replacing or duplicating it."""

    async def scenario() -> None:
        sub = "user_ensure_6"
        token = mint_token(sub=sub, role="parent", email="ensure6@example.com")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client() as (client, _router):
            ensure_resp = await client.post(
                "/v1/learners/ensure",
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert ensure_resp.status_code == 200, ensure_resp.text
            learner_id = ensure_resp.json()["learner_id"]

            session_resp = await client.post(
                "/v1/sessions",
                json={"learner_id": learner_id},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert session_resp.status_code == 201, session_resp.text
            assert session_resp.json()["learner_id"] == learner_id

    run_async(scenario())
