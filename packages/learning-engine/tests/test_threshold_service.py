"""Tests for protege.learning_engine.threshold_service.

Explicit positive and negative tests for every threshold condition (task
instruction), plus purity checks (no I/O import anywhere in the module)
and boundary values at exactly 0.85 / 3 / 1.
"""

import pytest

from protege.learning_engine.threshold_service import (
    ThresholdInputs,
    evaluate_mastery_threshold,
)


def test_all_conditions_met_verifies_mastery() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.90, unaided_correct_count=3, transfer_attempted_count=1)
    )
    assert decision.mastery_verified is True
    assert decision.p_known_met is True
    assert decision.unaided_correct_met is True
    assert decision.transfer_attempted_met is True


def test_p_known_below_threshold_fails() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.84, unaided_correct_count=3, transfer_attempted_count=1)
    )
    assert decision.p_known_met is False
    assert decision.mastery_verified is False


def test_p_known_exactly_at_threshold_passes() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.85, unaided_correct_count=3, transfer_attempted_count=1)
    )
    assert decision.p_known_met is True
    assert decision.mastery_verified is True


def test_unaided_correct_below_minimum_fails() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.90, unaided_correct_count=2, transfer_attempted_count=1)
    )
    assert decision.unaided_correct_met is False
    assert decision.mastery_verified is False


def test_unaided_correct_exactly_at_minimum_passes() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.90, unaided_correct_count=3, transfer_attempted_count=1)
    )
    assert decision.unaided_correct_met is True


def test_transfer_not_attempted_fails() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.90, unaided_correct_count=5, transfer_attempted_count=0)
    )
    assert decision.transfer_attempted_met is False
    assert decision.mastery_verified is False


def test_transfer_attempted_once_passes() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.90, unaided_correct_count=5, transfer_attempted_count=1)
    )
    assert decision.transfer_attempted_met is True


def test_high_p_known_alone_is_not_sufficient() -> None:
    # A very high p_known with no verification evidence must not verify
    # mastery -- all three conditions are independently required.
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.999, unaided_correct_count=0, transfer_attempted_count=0)
    )
    assert decision.mastery_verified is False


def test_extra_unaided_correct_and_transfer_still_requires_p_known() -> None:
    decision = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.5, unaided_correct_count=10, transfer_attempted_count=5)
    )
    assert decision.mastery_verified is False
    assert decision.p_known_met is False


def test_p_known_out_of_range_raises() -> None:
    with pytest.raises(ValueError, match="p_known"):
        evaluate_mastery_threshold(
            ThresholdInputs(p_known=1.1, unaided_correct_count=3, transfer_attempted_count=1)
        )
    with pytest.raises(ValueError, match="p_known"):
        evaluate_mastery_threshold(
            ThresholdInputs(p_known=-0.1, unaided_correct_count=3, transfer_attempted_count=1)
        )


def test_negative_counts_raise() -> None:
    with pytest.raises(ValueError, match="unaided_correct_count"):
        evaluate_mastery_threshold(
            ThresholdInputs(p_known=0.9, unaided_correct_count=-1, transfer_attempted_count=1)
        )
    with pytest.raises(ValueError, match="transfer_attempted_count"):
        evaluate_mastery_threshold(
            ThresholdInputs(p_known=0.9, unaided_correct_count=3, transfer_attempted_count=-1)
        )


def test_zero_and_one_boundary_probabilities_are_valid() -> None:
    lower = evaluate_mastery_threshold(
        ThresholdInputs(p_known=0.0, unaided_correct_count=0, transfer_attempted_count=0)
    )
    assert lower.mastery_verified is False
    upper = evaluate_mastery_threshold(
        ThresholdInputs(p_known=1.0, unaided_correct_count=3, transfer_attempted_count=1)
    )
    assert upper.mastery_verified is True


def test_deterministic_replay() -> None:
    inputs = ThresholdInputs(p_known=0.90, unaided_correct_count=3, transfer_attempted_count=1)
    assert evaluate_mastery_threshold(inputs) == evaluate_mastery_threshold(inputs)


def test_threshold_service_module_is_pure_no_io_imports() -> None:
    import protege.learning_engine.threshold_service as module

    source = module.__file__
    assert source is not None
    with open(source, encoding="utf-8") as f:
        contents = f.read()
    for forbidden in ("import os", "import sys", "open(", "requests", "httpx", "sqlalchemy"):
        message = f"threshold_service.py must stay pure; found {forbidden!r}"
        assert forbidden not in contents, message
