"""``GET /v1/sessions/{id}/stream`` (roadmap P10 testing requirements 10,
11): authoritative events, stable order, reconnect-safe via
``Last-Event-ID``."""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


async def _parse_sse(stream) -> list[tuple[int, str]]:
    events: list[tuple[int, str]] = []
    current_id: int | None = None
    current_event: str | None = None
    async for line in stream.aiter_lines():
        if line.startswith("id: "):
            current_id = int(line.removeprefix("id: "))
        elif line.startswith("event: "):
            current_event = line.removeprefix("event: ")
        elif line == "" and current_id is not None and current_event is not None:
            events.append((current_id, current_event))
            if current_event == "session_ended":
                break
            current_id, current_event = None, None
    return events


def test_sse_stream_emits_authoritative_events_in_stable_order() -> None:
    async def scenario() -> None:
        sub = "user_sse_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client() as (client, _router):
            create_resp = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            session_id = create_resp.json()["session_id"]

            async with client.stream(
                "GET", f"/v1/sessions/{session_id}/stream", headers=headers
            ) as stream:
                assert stream.status_code == 200
                assert stream.headers["content-type"].startswith("text/event-stream")
                events = await _parse_sse(stream)

            ids = [event_id for event_id, _name in events]
            assert ids == sorted(ids)
            assert ids == list(range(1, len(ids) + 1))
            # ARRIVAL->SPROUT_TEASE->DIAGNOSTIC: two transitions at creation.
            assert len(ids) >= 2

    run_async(scenario())


def test_sse_reconnect_with_last_event_id_does_not_replay_earlier_events() -> None:
    async def scenario() -> None:
        sub = "user_sse_2"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        headers = {"Authorization": f"Bearer {token}"}

        async with api_client() as (client, _router):
            create_resp = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={**headers, "Idempotency-Key": new_idempotency_key()},
            )
            session_id = create_resp.json()["session_id"]
            total_steps = create_resp.json()["step"]
            assert total_steps >= 2

            resume_headers = {**headers, "Last-Event-ID": "1"}
            async with client.stream(
                "GET", f"/v1/sessions/{session_id}/stream", headers=resume_headers
            ) as stream:
                events = await _parse_sse(stream)

            ids = [event_id for event_id, _name in events if _name != "session_ended"]
            assert all(event_id > 1 for event_id in ids)

    run_async(scenario())
