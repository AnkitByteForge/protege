"""Tests for the three-tier structured-output primitives (`structured.py`)."""

import json

import pytest

from protege.contracts import CoachHint
from protege.llm.base import Message
from protege.llm.structured import (
    StructuredParseError as ParseError,
)
from protege.llm.structured import (
    build_repair_messages,
    extract_json_object,
    parse_structured,
)


def test_extract_json_object_tolerates_prose_wrapper() -> None:
    raw = 'Sure! Here you go: {"a": 1} — thanks!'
    assert json.loads(extract_json_object(raw)) == {"a": 1}


def test_extract_json_object_raises_value_error_without_any_json() -> None:
    with pytest.raises(ValueError, match="no JSON object"):
        extract_json_object("no json here at all")


def test_parse_structured_success() -> None:
    raw = '{"intervention_id": "INT_M003_A", "text": "hi"}'
    value = parse_structured(raw, CoachHint)
    assert value.intervention_id == "INT_M003_A"
    assert value.text == "hi"


def test_parse_structured_wraps_validation_error() -> None:
    with pytest.raises(ParseError):
        parse_structured("{}", CoachHint)  # missing required fields


def test_parse_structured_wraps_json_decode_error() -> None:
    with pytest.raises(ParseError):
        parse_structured("not json at all", CoachHint)


def test_parse_structured_error_cause_is_preserved() -> None:
    try:
        parse_structured("{}", CoachHint)
    except ParseError as exc:
        assert exc.cause is not None
    else:
        pytest.fail("expected StructuredParseError")


def test_build_repair_messages_appends_assistant_then_user_turn() -> None:
    original = [Message("system", "sys"), Message("user", "hi")]
    repaired = build_repair_messages(original, "bad output", ValueError("boom"))
    assert repaired[0] == original[0]
    assert repaired[1] == original[1]
    assert repaired[2] == Message("assistant", "bad output")
    assert repaired[3].role == "user"
    assert "boom" in repaired[3].content


def test_build_repair_messages_does_not_mutate_the_original_list() -> None:
    original = [Message("user", "hi")]
    build_repair_messages(original, "bad", ValueError("x"))
    assert original == [Message("user", "hi")]
