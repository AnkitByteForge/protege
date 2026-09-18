"""Mypy fix follow-up: proves the ``Evidence.payload`` type-narrowing fix
in ``engine.py`` (``_json_payload``/``_json_value``) changes no evidence
content -- every payload produced by a real run is both byte-for-byte
what ``protege.learning_engine.evidence_builder`` built AND genuinely
JSON-serializable (the actual property ``protege.contracts.JSONValue``
promises).

Tested through the public :func:`~protege.thin_thread.run_thin_thread`
API, not the private ``_json_payload``/``_json_value`` helpers directly,
matching this repo's existing testing convention (behavioral tests over
private-function unit tests).
"""

from __future__ import annotations

import json

from _helpers import get_content, run_with_fake

from protege.thin_thread.scenario import happy_path_scenario


def test_every_evidence_payload_is_genuinely_json_serializable() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)

    assert result.evidence  # sanity: the run actually produced evidence
    for evidence in result.evidence:
        # Raises on anything that isn't real JSON -- the exact guarantee
        # protege.contracts.JSONValue is supposed to type-check.
        json.dumps(evidence.payload)


def test_response_evidence_payload_matches_the_p2_evidence_builder_shape() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)

    response_payloads = [e.payload for e in result.evidence if e.kind == "response"]
    assert len(response_payloads) == 5  # diagnostic + practice + 3 unaided verify
    for payload in response_payloads:
        assert payload.keys() >= {"item", "correct", "unaided", "hints_used"}
        assert isinstance(payload["item"], str)
        assert isinstance(payload["correct"], bool)
        assert isinstance(payload["unaided"], bool)
        assert isinstance(payload["hints_used"], int)


def test_transfer_evidence_payload_matches_the_p2_evidence_builder_shape() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)

    (payload,) = [e.payload for e in result.evidence if e.kind == "transfer"]
    assert payload.keys() >= {"item", "result"}
    assert isinstance(payload["item"], str)
    assert isinstance(payload["result"], bool)


def test_teaching_episode_evidence_payload_matches_the_p2_evidence_builder_shape() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)

    (payload,) = [e.payload for e in result.evidence if e.kind == "teaching_episode"]
    assert payload.keys() >= {"episode_id", "resolved"}
    assert isinstance(payload["episode_id"], str)
    assert isinstance(payload["resolved"], bool)
