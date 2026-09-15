"""Constraint tests: probability bounds, closed vocabularies, the §7.3
30-word Sprout cap, the §17 evidence-per-sentence rule, the §11.3 14-dim
state vector, and §24 additive-only payloads.

Rejections are asserted through ``model_validate`` (not ``model_copy``),
which is the path untrusted input actually takes."""

import pytest
from builders import (
    build_diagnosis_result,
    build_domain_event,
    build_evidence,
    build_mastery_estimate,
    build_policy_decision,
    build_sprout_script,
    build_sprout_turn,
    build_verification_record,
)
from pydantic import ValidationError

from protege.contracts import (
    DiagnosisResult,
    DomainEvent,
    Evidence,
    MasteryEstimate,
    PolicyDecision,
    ReportSentence,
    SproutScript,
    SproutTurn,
    VerificationRecord,
)

TOO_LONG = "word " * 30 + "end"


def test_probability_bounds_reject_out_of_range() -> None:
    bad_mastery = build_mastery_estimate().model_dump()
    bad_mastery["p_known"] = 1.5
    with pytest.raises(ValidationError):
        MasteryEstimate.model_validate(bad_mastery)

    bad_evidence = build_evidence().model_dump()
    bad_evidence["weight"] = 3.5
    with pytest.raises(ValidationError):
        Evidence.model_validate(bad_evidence)


def test_probability_weight_accepts_documented_verification_value() -> None:
    assert build_evidence().weight == 3.0


def test_sprout_turn_rejects_31_words() -> None:
    turn = build_sprout_turn().model_dump()
    turn["utterance"] = TOO_LONG
    with pytest.raises(ValidationError, match="30 words"):
        SproutTurn.model_validate(turn)


def test_sprout_script_rejects_31_words() -> None:
    script = build_sprout_script().model_dump()
    script["utterance"] = TOO_LONG
    with pytest.raises(ValidationError, match="30 words"):
        SproutScript.model_validate(script)


def test_report_sentence_requires_evidence_ids() -> None:
    with pytest.raises(ValidationError):
        ReportSentence(text="Ava mastered fractions.", evidence_ids=[])


def test_policy_decision_requires_14_dim_state_vector() -> None:
    bad = build_policy_decision().model_dump()
    bad["state"]["vector"] = [0.5] * 13
    with pytest.raises(ValidationError):
        PolicyDecision.model_validate(bad)


def test_abstaining_diagnosis_cannot_carry_labels() -> None:
    abstained = build_diagnosis_result().model_dump()
    abstained["abstained"] = True
    with pytest.raises(ValidationError, match="abstain"):
        DiagnosisResult.model_validate(abstained)


def test_unknown_event_payload_keys_are_ignored() -> None:
    """§24: consumers ignore unknown fields — additive-only within a major."""
    event = build_domain_event()
    payload = {**event.payload, "some_future_field": {"nested": [1, 2]}}
    parsed = DomainEvent.model_validate({**event.model_dump(), "payload": payload})
    assert parsed.payload["some_future_field"] == {"nested": [1, 2]}


def test_mastery_estimate_rejects_negative_counts() -> None:
    bad = build_mastery_estimate().model_dump()
    bad["unaided_correct"] = -1
    with pytest.raises(ValidationError):
        MasteryEstimate.model_validate(bad)


def test_sprout_turn_uses_closed_emotion_vocabulary() -> None:
    with pytest.raises(ValidationError):
        SproutTurn.model_validate(
            {
                "utterance": "hello",
                "exhibits": "M003",
                "emotion": "smug",
                "confidence_shown": "high",
            }
        )


def test_verification_record_rejects_result_count_mismatch() -> None:
    """§38 verification: ``results`` must align 1:1 with ``unaided_items``.

    A record claiming 3 unaided items but only 2 results is malformed input
    and must be rejected, not silently truncated or zero-padded — untrusted
    input takes the ``model_validate`` path, not ``model_copy``."""
    bad = build_verification_record().model_dump()
    bad["results"] = bad["results"][:-1]
    assert len(bad["results"]) != len(bad["unaided_items"])
    with pytest.raises(ValidationError, match="must align"):
        VerificationRecord.model_validate(bad)
