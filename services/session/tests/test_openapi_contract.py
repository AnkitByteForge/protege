"""OpenAPI generation consistency (roadmap P10 testing requirement 16):
the app builds a valid OpenAPI document, every P10 endpoint is documented,
and the export used for ``apps/web``'s typed client is deterministic."""

from __future__ import annotations

import json

from protege.session_service.app import create_app
from protege.session_service.openapi_export import export_openapi
from protege.session_service.settings import Settings


def _build_schema() -> dict:
    app = create_app(Settings(_env_file=None, log_level="WARNING", otel_console_export=False))
    return app.openapi()


EXPECTED_PATHS = {
    ("/v1/sessions", "post"),
    ("/v1/sessions/{session_id}", "get"),
    ("/v1/sessions/{session_id}/events", "post"),
    ("/v1/sessions/{session_id}/stream", "get"),
    ("/v1/sessions/{session_id}/complete", "post"),
    ("/v1/learners/{learner_id}/state", "get"),
    ("/v1/learners/{learner_id}/proof", "get"),
    ("/v1/learners/{learner_id}/tutor-brief", "get"),
    ("/v1/parents/{parent_id}/deletion-request", "post"),
}


def test_every_p10_endpoint_is_documented() -> None:
    schema = _build_schema()
    found = {
        (path, method)
        for path, methods in schema["paths"].items()
        for method in methods
        if path != "/healthz"
    }
    assert found >= EXPECTED_PATHS


def test_session_event_request_is_a_discriminated_union_in_the_schema() -> None:
    schema = _build_schema()
    events_body = schema["paths"]["/v1/sessions/{session_id}/events"]["post"]["requestBody"]
    content_schema = events_body["content"]["application/json"]["schema"]
    # Resolve one level of $ref if present.
    if "$ref" in content_schema:
        name = content_schema["$ref"].rsplit("/", 1)[-1]
        content_schema = schema["components"]["schemas"][name]
    assert "oneOf" in content_schema or "discriminator" in content_schema


def test_openapi_export_is_deterministic(tmp_path) -> None:
    out_a = export_openapi(tmp_path / "a.json")
    out_b = export_openapi(tmp_path / "b.json")
    assert out_a.read_text(encoding="utf-8") == out_b.read_text(encoding="utf-8")
    # Byte-parseable and non-trivial.
    parsed = json.loads(out_a.read_text(encoding="utf-8"))
    assert "paths" in parsed and len(parsed["paths"]) >= len(EXPECTED_PATHS)
