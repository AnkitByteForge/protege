"""Clerk JWT verification and ownership checks (roadmap P10 testing
requirements 4, 15; roadmap rule: "no trusting learner_id from the body
alone")."""

from __future__ import annotations

import uuid

from _auth_helpers import mint_token, mint_token_signed_by_wrong_key
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def test_missing_authorization_header_is_rejected() -> None:
    async def scenario() -> None:
        async with api_client() as (client, _router):
            response = await client.get(f"/v1/sessions/{uuid.uuid4()}")
            assert response.status_code == 401
            body = response.json()
            assert body["child_safe_message"]

    run_async(scenario())


def test_token_with_bad_signature_is_rejected() -> None:
    async def scenario() -> None:
        async with api_client() as (client, _router):
            token = mint_token_signed_by_wrong_key(sub="user_evil")
            response = await client.get(
                f"/v1/sessions/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401
            assert response.json()["child_safe_message"]

    run_async(scenario())


def test_expired_token_is_rejected() -> None:
    async def scenario() -> None:
        async with api_client() as (client, _router):
            token = mint_token(sub="user_expired", expires_in_s=-10)
            response = await client.get(
                f"/v1/sessions/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 401

    run_async(scenario())


def test_signed_in_actor_cannot_access_another_parents_learner() -> None:
    async def scenario() -> None:
        owner_sub = "user_owner"
        intruder_sub = "user_intruder"
        learner_id = await create_linked_learner(clerk_user_id=owner_sub)
        await create_linked_learner(clerk_user_id=intruder_sub)  # a real, unrelated account

        async with api_client() as (client, _router):
            intruder_token = mint_token(sub=intruder_sub, role="parent")
            response = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={
                    "Authorization": f"Bearer {intruder_token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 403
            assert response.json()["child_safe_message"]

    run_async(scenario())


def test_owning_parent_can_access_their_learner() -> None:
    async def scenario() -> None:
        sub = "user_owner_2"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        async with api_client() as (client, _router):
            token = mint_token(sub=sub, role="parent")
            response = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 201
            assert response.json()["learner_id"] == str(learner_id)

    run_async(scenario())


def test_fetching_a_nonexistent_session_is_not_found() -> None:
    async def scenario() -> None:
        sub = "user_owner_3"
        await create_linked_learner(clerk_user_id=sub)
        async with api_client() as (client, _router):
            token = mint_token(sub=sub, role="parent")
            response = await client.get(
                f"/v1/sessions/{uuid.uuid4()}", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 404
            assert response.json()["child_safe_message"]

    run_async(scenario())


def test_tutor_role_is_forbidden_from_creating_sessions() -> None:
    """Tutor/admin is a read-scoped role for learner state -- P10 does not
    grant a tutor write access to a learner's own session lifecycle."""

    async def scenario() -> None:
        learner_id = await create_linked_learner(clerk_user_id="user_parent_4")
        async with api_client() as (client, _router):
            tutor_token = mint_token(sub="user_tutor_1", role="tutor")
            response = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={
                    "Authorization": f"Bearer {tutor_token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            # A tutor has no linked `parents` row at all -> resolve_parent forbids.
            assert response.status_code == 403

    run_async(scenario())
