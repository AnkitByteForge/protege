"""RFC 9457 problem+json shape and ``child_safe_message`` (roadmap P10
testing requirement 13). Auth/authz/idempotency/rate-limit tests elsewhere
already exercise most status codes end to end; this file checks the
response *shape* itself, and that nothing internal leaks."""

from __future__ import annotations

import uuid

from _auth_helpers import mint_token
from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables
from _p10_helpers import api_client, create_linked_learner


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def test_problem_response_has_rfc9457_shape_and_content_type() -> None:
    async def scenario() -> None:
        async with api_client() as (client, _router):
            response = await client.get(f"/v1/sessions/{uuid.uuid4()}")
            assert response.status_code == 401
            assert response.headers["content-type"].startswith("application/problem+json")
            body = response.json()
            for field in ("type", "title", "status", "detail", "instance", "child_safe_message"):
                assert field in body, f"missing RFC 9457 field: {field}"
            assert body["status"] == 401
            # Never a stack trace, a Python exception repr, or SQL.
            joined = " ".join(str(v) for v in body.values())
            assert "Traceback" not in joined
            assert "Exception" not in joined

    run_async(scenario())


def test_validation_error_never_leaks_internal_detail() -> None:
    async def scenario() -> None:
        sub = "user_err_1"
        learner_id = await create_linked_learner(clerk_user_id=sub)
        token = mint_token(sub=sub, role="parent")
        async with api_client() as (client, _router):
            response = await client.post(
                "/v1/sessions",
                json={"learner_id": "not-a-uuid"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": str(uuid.uuid4()),
                },
            )
            assert response.status_code == 422
            body = response.json()
            assert body["child_safe_message"]
            assert "Traceback" not in str(body)
            _ = learner_id

    run_async(scenario())
