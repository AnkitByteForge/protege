"""``/v1/learners/{id}/*`` and ``/v1/parents/{id}/deletion-request``
(roadmap P10)."""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key
from sqlalchemy import select

from protege.session_service.db.engine import session_scope
from protege.session_service.db.models import AuditEventRow
from protege.session_service.repositories.learners import LearnerRepository


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def test_learner_state_is_empty_but_well_formed_before_any_session() -> None:
    async def scenario() -> None:
        sub = "user_lp_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        async with api_client() as (client, _router):
            response = await client.get(
                f"/v1/learners/{learner_id}/state", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            body = response.json()
            assert body["learner_id"] == str(learner_id)
            assert body["skills"] == []
            assert body["misconceptions"] == []

    run_async(scenario())


def test_proof_returns_canonical_not_yet_available_representation() -> None:
    async def scenario() -> None:
        sub = "user_lp_2"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        async with api_client() as (client, _router):
            response = await client.get(
                f"/v1/learners/{learner_id}/proof", headers={"Authorization": f"Bearer {token}"}
            )
            assert response.status_code == 200
            body = response.json()
            assert body["status"] == "not_yet_available"
            assert body["learner_id"] == str(learner_id)

    run_async(scenario())


def test_tutor_brief_requires_tutor_or_admin_role() -> None:
    async def scenario() -> None:
        sub = "user_lp_3"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        parent_token = mint_token(sub=sub, role="parent")
        tutor_token = mint_token(sub="user_lp_tutor", role="tutor")

        async with api_client() as (client, _router):
            forbidden = await client.get(
                f"/v1/learners/{learner_id}/tutor-brief",
                headers={"Authorization": f"Bearer {parent_token}"},
            )
            assert forbidden.status_code == 403
            assert forbidden.json()["child_safe_message"]

            allowed = await client.get(
                f"/v1/learners/{learner_id}/tutor-brief",
                headers={"Authorization": f"Bearer {tutor_token}"},
            )
            assert allowed.status_code == 200
            assert allowed.json()["status"] == "not_yet_available"

    run_async(scenario())


def test_deletion_request_records_audit_event_and_does_not_delete() -> None:
    async def scenario() -> None:
        sub = "user_lp_4"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")

        async with session_scope() as session:
            parent = await LearnerRepository(session).get_parent_by_clerk_user_id(sub)
            parent_id = parent.id

        async with api_client() as (client, _router):
            response = await client.post(
                f"/v1/parents/{parent_id}/deletion-request",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 202
            body = response.json()
            assert body["status"] == "recorded"
            assert body["parent_id"] == str(parent_id)

        async with session_scope() as session:
            # The learner still exists -- no deletion executed.
            learner = await LearnerRepository(session).get(learner_id)
            assert learner is not None

            audit_rows = (
                (
                    await session.execute(
                        select(AuditEventRow).where(AuditEventRow.resource == f"parent:{parent_id}")
                    )
                )
                .scalars()
                .all()
            )
            assert len(audit_rows) == 1
            assert audit_rows[0].action == "deletion_requested"

    run_async(scenario())


def test_deletion_request_for_someone_elses_account_is_forbidden() -> None:
    async def scenario() -> None:
        await create_linked_learner(clerk_user_id="user_lp_5_owner")
        intruder_token = mint_token(sub="user_lp_5_intruder", role="parent")
        await create_linked_learner(clerk_user_id="user_lp_5_intruder")

        async with session_scope() as session:
            owner_parent = await LearnerRepository(session).get_parent_by_clerk_user_id(
                "user_lp_5_owner"
            )
            owner_parent_id = owner_parent.id

        async with api_client() as (client, _router):
            response = await client.post(
                f"/v1/parents/{owner_parent_id}/deletion-request",
                headers={
                    "Authorization": f"Bearer {intruder_token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 403

    run_async(scenario())
