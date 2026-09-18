"""Tests for protege.policy.context: the 14-dim state vector."""

from __future__ import annotations

import pytest
from _context_factory import make_context

from protege.contracts import ConfidenceLabel, PolicyDecisionState
from protege.policy.context import (
    STATE_VECTOR_DIMENSION_NAMES,
    build_state_vector,
    encode_grade_band,
    mean_confidence,
)


def test_state_vector_has_exactly_14_dimensions() -> None:
    assert len(STATE_VECTOR_DIMENSION_NAMES) == 14
    vector = build_state_vector(make_context())
    assert isinstance(vector, PolicyDecisionState)
    assert len(vector.vector) == 14


def test_state_vector_dimension_order_matches_architecture_doc_example() -> None:
    # PROTEGE_ARCHITECTURE.md §11.3 / packages/contracts/tests/builders.py
    # build_policy_decision_state: [p_known, max_belief, n_active_mc,
    # hint_rate, latency_z, streak_correct, streak_incorrect,
    # session_minutes, items_this_skill, confidence_mean, calibration_error,
    # prior_teachback_success, time_since_last_review, grade_band].
    context = make_context(
        p_known=0.62,
        max_misconception_belief=0.71,
        n_active_misconceptions=1,
        hints_requested_this_skill=1,
        items_this_skill=4,  # hint_rate = 1/4 = 0.25
        mean_latency_z=-0.4,
        streak_correct=2,
        streak_incorrect=0,
        session_minutes=8.2,
        confidence_mean=0.7,
        calibration_error=0.18,
        prior_teachback_success=1.0,
        time_since_last_review_days=3.0,
        grade_band="3-4",
    )
    vector = build_state_vector(context).vector
    assert vector == [0.62, 0.71, 1.0, 0.25, -0.4, 2.0, 0.0, 8.2, 4.0, 0.7, 0.18, 1.0, 3.0, 3.0]


def test_state_vector_is_deterministic() -> None:
    context = make_context(p_known=0.4, grade_band="K-2")
    assert build_state_vector(context) == build_state_vector(context)


@pytest.mark.parametrize(
    ("grade_band", "expected"),
    [
        ("K-2", 0.0),
        ("0-1", 0.0),
        ("3-4", 3.0),
        ("4-5", 4.0),
        ("9-12", 9.0),
    ],
)
def test_encode_grade_band(grade_band: str, expected: float) -> None:
    assert encode_grade_band(grade_band) == expected


@pytest.mark.parametrize("bad", ["3", "3_4", "", "K", "3-4-5", "grade3"])
def test_encode_grade_band_rejects_malformed_input(bad: str) -> None:
    with pytest.raises(ValueError, match="grade_band"):
        encode_grade_band(bad)


def test_context_rejects_malformed_grade_band_at_construction() -> None:
    with pytest.raises(ValueError, match="grade_band"):
        make_context(grade_band="not-a-band-3")


@pytest.mark.parametrize(
    ("labels", "expected"),
    [
        ([], 0.5),
        ([ConfidenceLabel.SURE], 1.0),
        ([ConfidenceLabel.GUESSING], 0.0),
        ([ConfidenceLabel.THINK_SO], 0.5),
        ([ConfidenceLabel.SURE, ConfidenceLabel.GUESSING], 0.5),
        ([ConfidenceLabel.SURE, ConfidenceLabel.SURE, ConfidenceLabel.GUESSING], 2.0 / 3.0),
    ],
)
def test_mean_confidence(labels: list[ConfidenceLabel], expected: float) -> None:
    assert mean_confidence(labels) == pytest.approx(expected)


@pytest.mark.parametrize(
    "field_name",
    [
        "p_known",
        "max_misconception_belief",
        "confidence_mean",
        "calibration_error",
        "prior_teachback_success",
    ],
)
def test_probability_fields_reject_out_of_range(field_name: str) -> None:
    with pytest.raises(ValueError):
        make_context(**{field_name: 1.5})
    with pytest.raises(ValueError):
        make_context(**{field_name: -0.1})


@pytest.mark.parametrize(
    "field_name",
    [
        "n_active_misconceptions",
        "hints_requested_this_skill",
        "streak_correct",
        "streak_incorrect",
        "items_this_skill",
        "loop_count",
    ],
)
def test_nonnegative_int_fields_reject_negatives(field_name: str) -> None:
    with pytest.raises(ValueError):
        make_context(**{field_name: -1})


@pytest.mark.parametrize(
    "field_name", ["session_minutes", "time_since_last_review_days", "struggle_seconds"]
)
def test_nonnegative_float_fields_reject_negatives(field_name: str) -> None:
    with pytest.raises(ValueError):
        make_context(**{field_name: -0.01})


def test_mean_latency_z_may_be_negative() -> None:
    # Unlike the other float fields, mean_latency_z is a z-score and is
    # legitimately negative in the common case (faster than baseline).
    context = make_context(mean_latency_z=-2.5)
    assert context.mean_latency_z == -2.5


def test_mean_latency_z_rejects_non_finite() -> None:
    with pytest.raises(ValueError, match="mean_latency_z"):
        make_context(mean_latency_z=float("nan"))
    with pytest.raises(ValueError, match="mean_latency_z"):
        make_context(mean_latency_z=float("inf"))


def test_hints_without_items_attempted_raises() -> None:
    with pytest.raises(ValueError, match="hints_requested_this_skill"):
        make_context(hints_requested_this_skill=1, items_this_skill=0)


def test_hint_rate_zero_when_no_items_attempted() -> None:
    context = make_context(hints_requested_this_skill=0, items_this_skill=0)
    assert context.hint_rate == 0.0


def test_hint_rate_is_hints_over_items() -> None:
    context = make_context(hints_requested_this_skill=3, items_this_skill=6)
    assert context.hint_rate == 0.5
