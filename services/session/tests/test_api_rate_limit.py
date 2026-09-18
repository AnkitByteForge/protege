"""Rate limits (roadmap P10 testing requirement 14; verbatim numbers "60
events/min/learner, 10 sessions/day" -- exercised here with small
test-configured limits rather than waiting on the real numbers)."""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, build_test_settings, create_linked_learner, new_idempotency_key

from protege.authoring.loader import load_content_pack
from protege.thin_thread.scenario import numeric_answer_text, resolve_items


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def test_session_creation_rate_limit_returns_429_with_child_safe_message() -> None:
    async def scenario() -> None:
        sub = "user_rl_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        settings = build_test_settings(rate_limit_sessions_per_day=1)

        async with api_client(settings=settings) as (client, _router):
            first = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert first.status_code == 201

            second = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert second.status_code == 429
            assert second.json()["child_safe_message"]

    run_async(scenario())


def test_event_rate_limit_returns_429_with_child_safe_message() -> None:
    async def scenario() -> None:
        content = load_content_pack()
        items = resolve_items(content)
        sub = "user_rl_2"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}
        # SESSION_STARTED already counts as one event -> the very first
        # events-endpoint call already sees count=1, so a limit of 1 rejects it.
        settings = build_test_settings(rate_limit_events_per_minute=1)

        async with api_client(settings=settings) as (client, _router):
            create_resp = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert create_resp.status_code == 201
            session_id = create_resp.json()["session_id"]

            response = await client.post(
                f"/v1/sessions/{session_id}/events",
                json={
                    "type": "answer_submitted",
                    "item_id": items.diagnostic.item_id,
                    "response_text": numeric_answer_text(items.diagnostic.correct_answer),
                },
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            assert response.status_code == 429
            assert response.json()["child_safe_message"]

    run_async(scenario())
