"""Tests for protege.learning_engine.educational_validator.

Covers answer-leak (deterministic substring + numeric-equivalence, zero
tolerance), forbidden-phrase (misconception consistency) checking, and
reading-level (Flesch-Kincaid) scoring.
"""

import pytest

from protege.learning_engine.educational_validator import (
    answer_leaked,
    contains_forbidden_phrase,
    count_syllables,
    flesch_kincaid_grade,
    reading_level_ok,
)

# --- answer_leaked ---------------------------------------------------------


def test_answer_leaked_literal_substring() -> None:
    assert answer_leaked("The answer is 1/4, easy!", "1/4") is True


def test_answer_leaked_case_insensitive() -> None:
    assert answer_leaked("THE ANSWER IS 1/4", "1/4") is True


def test_answer_leaked_numeric_equivalence_unsimplified_form() -> None:
    # Correct answer "1/4" leaked via an equivalent but differently
    # written form, "2/8" -- must still be caught (zero tolerance).
    assert answer_leaked("I bet it's 2/8 of the pizza", "1/4") is True


def test_answer_leaked_no_leak_for_wrong_statement() -> None:
    # Sprout stating its (wrong) misconception-driven belief must not be
    # flagged as leaking the correct answer.
    assert answer_leaked("I think 1/8 is bigger! Eight is way more than four.", "1/4") is False


def test_answer_leaked_no_leak_for_unrelated_text() -> None:
    assert answer_leaked("Let's look at the pizza together.", "1/4") is False


def test_answer_leaked_deterministic_replay() -> None:
    args = ("So 1/8 is bigger, right? Eight is more than four.", "1/4")
    assert answer_leaked(*args) == answer_leaked(*args)


@pytest.mark.parametrize(
    ("utterance", "correct_answer", "expected"),
    [
        ("It's definitely 1/4.", "1/4", True),
        ("It's definitely 1/8.", "1/4", False),
        ("", "1/4", False),
    ],
)
def test_answer_leaked_boundary_cases(utterance: str, correct_answer: str, expected: bool) -> None:
    assert answer_leaked(utterance, correct_answer) is expected


# --- contains_forbidden_phrase ---------------------------------------------


def test_contains_forbidden_phrase_detects_literal_vocabulary() -> None:
    result = contains_forbidden_phrase(
        "The denominator tells you how many pieces.", ["numerator", "denominator"]
    )
    assert result == "denominator"


def test_contains_forbidden_phrase_none_when_clean() -> None:
    result = contains_forbidden_phrase(
        "The bottom number tells you how many pieces.", ["numerator", "denominator"]
    )
    assert result is None


def test_contains_forbidden_phrase_case_insensitive() -> None:
    assert contains_forbidden_phrase("NUMERATOR!", ["numerator"]) == "numerator"


def test_contains_forbidden_phrase_empty_forbidden_list() -> None:
    assert contains_forbidden_phrase("anything at all", []) is None


def test_contains_forbidden_phrase_returns_first_match() -> None:
    result = contains_forbidden_phrase(
        "numerator and denominator both appear", ["numerator", "denominator"]
    )
    assert result == "numerator"


# --- reading level ----------------------------------------------------------


def test_count_syllables_basic_words() -> None:
    assert count_syllables("cat") == 1
    assert count_syllables("apple") >= 1
    assert count_syllables("") == 0


def test_count_syllables_never_returns_zero_for_nonempty_word() -> None:
    for word in ["a", "the", "strength", "queue"]:
        assert count_syllables(word) >= 1


def test_flesch_kincaid_grade_empty_text_is_zero() -> None:
    assert flesch_kincaid_grade("") == 0.0
    assert flesch_kincaid_grade("   ") == 0.0


def test_flesch_kincaid_grade_simple_sentence_is_low_grade() -> None:
    grade = flesch_kincaid_grade("The cat sat on the mat.")
    assert grade < 5.0


def test_flesch_kincaid_grade_complex_sentence_is_higher_grade() -> None:
    simple = flesch_kincaid_grade("The cat sat.")
    complex_ = flesch_kincaid_grade(
        "The extraordinarily sophisticated communication methodology "
        "necessitated comprehensive interdisciplinary collaboration."
    )
    assert complex_ > simple


def test_reading_level_ok_uses_default_grade_3_5_threshold() -> None:
    assert reading_level_ok("The cat sat on the mat.") is True


def test_reading_level_ok_rejects_complex_text() -> None:
    complex_text = (
        "The extraordinarily sophisticated communication methodology "
        "necessitated comprehensive interdisciplinary collaboration."
    )
    assert reading_level_ok(complex_text) is False


def test_reading_level_ok_custom_threshold() -> None:
    text = "The bottom number tells how many equal pieces."
    grade = flesch_kincaid_grade(text)
    assert reading_level_ok(text, max_grade=grade + 0.01) is True
    assert reading_level_ok(text, max_grade=grade - 0.01) is False
