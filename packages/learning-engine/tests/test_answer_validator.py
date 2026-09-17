"""Tests for protege.learning_engine.answer_validator.

Covers: equivalent fractions, unsimplified forms, mixed-number
equivalents, invalid fractions, near-misses, representation mismatch, and
boundary/error cases (task instruction: "Create extensive tests").
"""

from fractions import Fraction

import pytest

from protege.learning_engine.answer_validator import (
    AnswerOutcome,
    parse_fraction_answer,
    validate_answer,
)

# --- parse_fraction_answer ---------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1/4", Fraction(1, 4)),
        ("2/8", Fraction(1, 4)),  # unsimplified form, same exact value
        ("4/8", Fraction(1, 2)),
        ("4", Fraction(4)),
        ("0", Fraction(0)),
        ("-3", Fraction(-3)),
        ("-1/4", Fraction(-1, 4)),
        ("1 1/2", Fraction(3, 2)),  # mixed number
        ("0 1/2", Fraction(1, 2)),
        ("3 0/4", Fraction(3)),
    ],
)
def test_parse_fraction_answer_valid_forms(raw: str, expected: Fraction) -> None:
    assert parse_fraction_answer(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "1/0",  # zero denominator
        "abc",
        "1/",
        "/4",
        "1//4",
        "one half",
        "1.5",  # decimals not in the accepted grammar
        "-1 1/2",  # negative mixed numbers deliberately unsupported
        "1 2 3",
    ],
)
def test_parse_fraction_answer_unparseable(raw: str) -> None:
    assert parse_fraction_answer(raw) is None


def test_parse_fraction_answer_never_raises_on_garbage() -> None:
    # A malformed child answer is expected input, not a programming error.
    for garbage in ["🍕", "1/4/8", "--1", "1/-4", "1/4x"]:
        assert parse_fraction_answer(garbage) is None


# --- validate_answer -----------------------------------------------------


def test_validate_answer_exact_match_is_correct() -> None:
    result = validate_answer("1/4", "1/4")
    assert result.outcome is AnswerOutcome.CORRECT
    assert result.is_correct


def test_validate_answer_equivalent_unsimplified_form_is_correct() -> None:
    result = validate_answer("2/8", "1/4")
    assert result.outcome is AnswerOutcome.CORRECT
    assert result.submitted_value == Fraction(1, 4)


def test_validate_answer_mixed_number_equivalent_is_correct() -> None:
    result = validate_answer("1 1/2", "3/2")
    assert result.is_correct


@pytest.mark.parametrize(
    ("raw", "correct"),
    [
        ("1/8", "1/4"),  # the classic M003 near-miss distractor
        ("1/5", "1/4"),  # off-by-one denominator typo
        ("1/3", "1/4"),
        ("2/4", "1/4"),  # equivalent to 1/2, not 1/4 -- must not be accepted
    ],
)
def test_validate_answer_near_miss_is_incorrect_never_fuzzy(raw: str, correct: str) -> None:
    result = validate_answer(raw, correct)
    assert result.outcome is AnswerOutcome.INCORRECT
    assert not result.is_correct


def test_validate_answer_unparseable_submission() -> None:
    result = validate_answer("banana", "1/4")
    assert result.outcome is AnswerOutcome.UNPARSEABLE
    assert result.submitted_value is None
    assert result.correct_value == Fraction(1, 4)


def test_validate_answer_invalid_correct_answer_raises() -> None:
    # Misconfigured authored content -- a real programming/content error,
    # not a child-input outcome.
    with pytest.raises(ValueError, match="not a parseable fraction"):
        validate_answer("1/4", "not-a-fraction")


def test_validate_answer_representation_match_is_evaluated_normally() -> None:
    result = validate_answer(
        "1/4",
        "1/4",
        expected_representation="area_model",
        submitted_representation="area_model",
    )
    assert result.is_correct


def test_validate_answer_representation_mismatch_short_circuits() -> None:
    result = validate_answer(
        "1/4",
        "1/4",
        expected_representation="number_line",
        submitted_representation="area_model",
    )
    assert result.outcome is AnswerOutcome.REPRESENTATION_MISMATCH
    assert result.submitted_value is None
    assert result.correct_value is None


def test_validate_answer_representation_none_is_not_a_mismatch() -> None:
    # Only an *explicit* differing pair triggers a mismatch; omitting
    # either side means "representation not tracked for this call."
    result = validate_answer("1/4", "1/4", expected_representation="number_line")
    assert result.is_correct


def test_validate_answer_enum_string_interop_without_import() -> None:
    # protege.contracts.RepresentationType members are StrEnum values that
    # compare equal to their plain string -- callers can pass either
    # without this package importing packages/contracts.
    assert validate_answer(
        "1/4", "1/4", expected_representation="area_model", submitted_representation="area_model"
    ).is_correct
