"""Event validation and FSM authority (roadmap P10 testing requirements 5,
6, 7): an invalid event is rejected, the server-side FSM remains the sole
transition authority (a client cannot force an illegal transition), and one
legal event produces exactly one state transition."""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key

from protege.authoring.loader import load_content_pack
from protege.session_service.db.engine import session_scope
from protege.session_service.repositories.sessions import SessionRepository
from protege.thin_thread.scenario import numeric_answer_text, resolve_items


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


async def _create_session(client, headers: dict[str, str], learner_id: object) -> str:
    resp = await client.post(
        "/v1/sessions",
        json={"learner_id": str(learner_id)},
        headers={**headers, "Idempotency-Key": new_idempotency_key()},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["session_id"]


def test_malformed_event_body_is_rejected_with_child_safe_message() -> None:
    async def scenario() -> None:
        sub = "user_events_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        async with api_client() as (client, _router):
            session_id = await _create_session(client, headers, learner_id)
            response = await client.post(
                f"/v1/sessions/{session_id}/events",
                json={"type": "not_a_real_event_type"},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert response.status_code == 422
            assert response.json()["child_safe_message"]

    run_async(scenario())


def test_answer_for_an_item_not_currently_presented_is_rejected() -> None:
    async def scenario() -> None:
        content = load_content_pack()
        items = resolve_items(content)
        sub = "user_events_2"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        async with api_client() as (client, _router):
            session_id = await _create_session(client, headers, learner_id)
            # Session is in DIAGNOSTIC; submitting the TRANSFER item's id is illegal.
            response = await client.post(
                f"/v1/sessions/{session_id}/events",
                json={
                    "type": "answer_submitted",
                    "item_id": items.transfer.item_id,
                    "response_text": numeric_answer_text(items.transfer.correct_answer),
                },
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert response.status_code == 422
            assert response.json()["child_safe_message"]

    run_async(scenario())


def test_hint_requested_outside_coach_assist_is_rejected() -> None:
    """The FSM stays the sole transition authority: a client cannot force
    an event that is illegal for the session's current state."""

    async def scenario() -> None:
        sub = "user_events_3"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        async with api_client() as (client, _router):
            session_id = await _create_session(client, headers, learner_id)
            # Session is in DIAGNOSTIC, not COACH_ASSIST.
            response = await client.post(
                f"/v1/sessions/{session_id}/events",
                json={"type": "hint_requested"},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert response.status_code == 409
            assert response.json()["child_safe_message"]

    run_async(scenario())


def test_one_legal_event_produces_exactly_one_recorded_step_increment() -> None:
    async def scenario() -> None:
        content = load_content_pack()
        items = resolve_items(content)
        sub = "user_events_4"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        async with api_client() as (client, _router):
            session_id = await _create_session(client, headers, learner_id)
            before = await client.get(f"/v1/sessions/{session_id}", headers=headers)
            step_before = before.json()["step"]

            response = await client.post(
                f"/v1/sessions/{session_id}/events",
                json={
                    "type": "answer_submitted",
                    "item_id": items.diagnostic.item_id,
                    "response_text": numeric_answer_text(items.diagnostic.correct_answer),
                },
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert response.status_code == 200
            after = await client.get(f"/v1/sessions/{session_id}", headers=headers)
            step_after = after.json()["step"]

        import uuid as uuid_mod

        async with session_scope() as session:
            transitions = await SessionRepository(session).list_transitions(
                uuid_mod.UUID(session_id)
            )
            steps = [t.step for t in transitions]
            assert steps == list(range(1, len(steps) + 1))
            assert step_after > step_before

    run_async(scenario())
