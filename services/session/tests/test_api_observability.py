"""``traceparent`` propagation (roadmap P10 testing requirement 13: "one
trace per request ... propagated to the client via `traceparent`") -- and
that the *same* trace id is the one persisted on that request's domain
events, so a request can be correlated to what it wrote in Postgres."""

from __future__ import annotations

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner, new_idempotency_key
from sqlalchemy import select

from protege.session_service.db.engine import session_scope
from protege.session_service.db.models import EventRow


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def _trace_id_from_traceparent(header: str) -> str:
    # W3C format: "00-<32 hex trace id>-<16 hex span id>-<2 hex flags>"
    return header.split("-")[1]


def test_response_carries_a_traceparent_header() -> None:
    async def scenario() -> None:
        async with api_client() as (client, _router):
            response = await client.get("/healthz")
            assert response.status_code == 200
            assert "traceparent" in response.headers
            header = response.headers["traceparent"]
            parts = header.split("-")
            assert len(parts) == 4
            assert len(parts[1]) == 32  # trace id
            assert len(parts[2]) == 16  # span id

    run_async(scenario())


def test_persisted_domain_events_carry_the_same_trace_id_as_the_response() -> None:
    async def scenario() -> None:
        sub = "user_trace_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        async with api_client() as (client, _router):
            response = await client.post(
                "/v1/sessions",
                json={"learner_id": str(learner_id)},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": new_idempotency_key(),
                },
            )
            assert response.status_code == 201
            session_id = response.json()["session_id"]
            trace_id = _trace_id_from_traceparent(response.headers["traceparent"])

        async with session_scope() as session:
            import uuid as uuid_mod

            rows = (
                (
                    await session.execute(
                        select(EventRow).where(EventRow.session_id == uuid_mod.UUID(session_id))
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) >= 1
            assert all(row.trace_id == trace_id for row in rows)

    run_async(scenario())
