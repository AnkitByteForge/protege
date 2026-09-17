"""Tests for `FakeProvider` — the deterministic testing interface P5/P6/P7
will build on."""

import pytest

from protege.contracts import CoachHint, DiagnosisResult, ReportDraft, SproutTurn
from protege.llm.errors import ProviderRateLimited
from protege.llm.providers.fake import FakeOutcome, FakeProvider


@pytest.mark.parametrize("model_cls", [SproutTurn, DiagnosisResult, CoachHint, ReportDraft])
def test_every_role_schema_has_a_valid_canned_response(model_cls: type) -> None:
    provider = FakeProvider()
    schema = model_cls.model_json_schema()
    result = provider.complete(
        [], model_id="x", max_tokens=1, temperature=0.0, timeout_s=1.0, json_schema=schema
    )
    model_cls.model_validate_json(result.text)  # must not raise


def test_default_responses_are_byte_identical_across_calls() -> None:
    provider = FakeProvider()
    schema = CoachHint.model_json_schema()
    first = provider.complete(
        [], model_id="x", max_tokens=1, temperature=0.9, timeout_s=1.0, json_schema=schema
    )
    second = provider.complete(
        [], model_id="x", max_tokens=1, temperature=0.9, timeout_s=1.0, json_schema=schema
    )
    assert first.text == second.text


def test_unknown_schema_title_falls_back_to_empty_object() -> None:
    provider = FakeProvider()
    result = provider.complete(
        [],
        model_id="x",
        max_tokens=1,
        temperature=0.0,
        timeout_s=1.0,
        json_schema={"title": "Unknown"},
    )
    assert result.text == "{}"


def test_custom_responses_override_defaults() -> None:
    provider = FakeProvider(responses={"CoachHint": '{"intervention_id": "X", "text": "custom"}'})
    schema = CoachHint.model_json_schema()
    result = provider.complete(
        [], model_id="x", max_tokens=1, temperature=0.0, timeout_s=1.0, json_schema=schema
    )
    assert CoachHint.model_validate_json(result.text).text == "custom"


def test_script_is_consumed_in_order_then_falls_back_to_canned() -> None:
    provider = FakeProvider(script=[FakeOutcome.rate_limited(), FakeOutcome.ok('{"a": 1}')])
    with pytest.raises(ProviderRateLimited):
        provider.complete([], model_id="x", max_tokens=1, temperature=0.0, timeout_s=1.0)
    second = provider.complete([], model_id="x", max_tokens=1, temperature=0.0, timeout_s=1.0)
    assert second.text == '{"a": 1}'
    # script exhausted -> falls back to the canned-response behaviour
    third = provider.complete(
        [],
        model_id="x",
        max_tokens=1,
        temperature=0.0,
        timeout_s=1.0,
        json_schema=CoachHint.model_json_schema(),
    )
    CoachHint.model_validate_json(third.text)


def test_calls_are_recorded_in_order() -> None:
    provider = FakeProvider()
    provider.complete(
        [],
        model_id="m1",
        max_tokens=1,
        temperature=0.0,
        timeout_s=1.0,
        json_schema=CoachHint.model_json_schema(),
    )
    provider.complete([], model_id="m2", max_tokens=1, temperature=0.0, timeout_s=1.0)
    assert provider.calls == [("m1", "CoachHint"), ("m2", None)]


def test_malformed_and_schema_invalid_outcomes_return_bad_but_non_raising_text() -> None:
    provider = FakeProvider(script=[FakeOutcome.malformed(), FakeOutcome.schema_invalid()])
    malformed = provider.complete([], model_id="x", max_tokens=1, temperature=0.0, timeout_s=1.0)
    assert "{" not in malformed.text
    invalid = provider.complete([], model_id="x", max_tokens=1, temperature=0.0, timeout_s=1.0)
    assert invalid.text == "{}"
