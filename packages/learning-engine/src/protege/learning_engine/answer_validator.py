"""Exact answer validation (``PROTEGE_ARCHITECTURE.md`` §5, §17; task
instruction: "exact Fraction arithmetic for math validation").

Uses only the standard-library :mod:`fractions` module for exact rational
arithmetic -- no SymPy, no new third-party dependency (task instruction:
"Do NOT add any third-party dependencies beyond what is already
present"). :class:`fractions.Fraction` gives bit-exact rational
comparison, which is what §17's "math_error_rate target 0.000" requires;
SymPy's symbolic-algebra machinery is not needed to compare two rational
numbers, and the "Numerical / edge case safety" section of the task that
produced this module names ``Fraction`` explicitly.

This module never performs fuzzy or LLM interpretation of an answer (task
instruction: "Do not perform fuzzy LLM interpretation here") -- an
unparseable raw answer is reported as an explicit outcome, never guessed
at, and a near-miss (e.g. a typo'd denominator) is exact-compared and
reported INCORRECT, never accepted within a tolerance.
"""

import re
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

_SIMPLE_FRACTION_RE = re.compile(r"^-?\d+/\d+$")


class AnswerOutcome(Enum):
    """The four validator outcomes the task instruction distinguishes:
    "mathematically equivalent valid answers", "incorrect/near-miss
    answers", "representation requirements" (mismatch), and unparseable
    input."""

    CORRECT = "correct"
    INCORRECT = "incorrect"
    UNPARSEABLE = "unparseable"
    REPRESENTATION_MISMATCH = "representation_mismatch"


@dataclass(frozen=True)
class AnswerValidationResult:
    """Immutable validation result. ``submitted_value``/``correct_value``
    are the exact parsed :class:`~fractions.Fraction` values, or ``None``
    when parsing did not happen (unparseable input, or a representation
    mismatch that short-circuits before any numeric comparison)."""

    outcome: AnswerOutcome
    submitted_value: Fraction | None
    correct_value: Fraction | None

    @property
    def is_correct(self) -> bool:
        return self.outcome is AnswerOutcome.CORRECT


def _parse_simple_fraction(text: str) -> Fraction | None:
    """Parse ``"a/b"`` (possibly negative) into an exact Fraction, or
    ``None`` if ``text`` is not that shape or has a zero denominator."""
    if not _SIMPLE_FRACTION_RE.match(text):
        return None
    numerator_str, _, denominator_str = text.partition("/")
    denominator = int(denominator_str)
    if denominator == 0:
        return None
    return Fraction(int(numerator_str), denominator)


def parse_fraction_answer(raw: str) -> Fraction | None:
    """Parse a child-facing fraction answer string into an exact
    :class:`~fractions.Fraction`.

    Accepted grammars (K-5 fraction domain, §38 worked example forms):

    - whole numbers: ``"4"``, ``"-2"``
    - simple fractions, any (unsimplified) form: ``"1/4"``, ``"2/8"``
    - mixed numbers: ``"1 1/2"`` (a non-negative whole part plus a simple
      fraction; PROTÉGÉ's K-5 fraction domain has no documented need for
      negative mixed numbers, so ``"-1 1/2"`` is deliberately not
      supported -- it returns ``None`` rather than guessing a sign
      convention nothing authors)

    Returns ``None`` (never raises) for anything that does not parse --
    an unparseable answer is a validator *outcome*
    (:attr:`AnswerOutcome.UNPARSEABLE`), not a Python exception, because a
    malformed child answer is expected input, not a programming error.
    Whitespace is stripped; internal formatting (e.g. multiple spaces) is
    not tolerated, matching the "near-miss" testing requirement that the
    validator not be fuzzy.
    """
    text = raw.strip()
    if not text:
        return None

    if " " in text:
        whole_part, _, frac_part = text.partition(" ")
        if not re.match(r"^\d+$", whole_part):
            return None
        fractional = _parse_simple_fraction(frac_part)
        if fractional is None:
            return None
        return int(whole_part) + fractional

    simple = _parse_simple_fraction(text)
    if simple is not None:
        return simple

    if _is_signed_int(text):
        return Fraction(int(text))

    return None


def _is_signed_int(text: str) -> bool:
    return bool(re.match(r"^-?\d+$", text))


def validate_answer(
    raw_answer: str,
    correct_answer: str,
    *,
    expected_representation: str | None = None,
    submitted_representation: str | None = None,
) -> AnswerValidationResult:
    """Exact, representation-aware answer validation.

    If both ``expected_representation`` and ``submitted_representation``
    are given and differ, the result is
    :attr:`AnswerOutcome.REPRESENTATION_MISMATCH` and no numeric
    comparison is attempted -- this fails closed rather than guessing
    which representation the child meant. Both representation arguments
    accept plain strings so callers can pass
    ``protege.contracts.RepresentationType`` members directly (it is a
    ``StrEnum`` and compares equal to its string value) without this
    package importing ``packages/contracts`` (docs/DECISIONS.md D6: no
    Pydantic coupling).

    Numeric equivalence is exact: ``"2/8"`` and ``"1/4"`` are both
    CORRECT against a correct answer of ``"1/4"``; ``"1/5"`` against the
    same correct answer is INCORRECT, exactly and always -- there is no
    numeric tolerance, so a near-miss typo is never silently accepted.

    Raises ``ValueError`` if ``correct_answer`` itself does not parse --
    that indicates misconfigured authored content, not a child input to
    report an outcome for.
    """
    if (
        expected_representation is not None
        and submitted_representation is not None
        and expected_representation != submitted_representation
    ):
        return AnswerValidationResult(
            outcome=AnswerOutcome.REPRESENTATION_MISMATCH,
            submitted_value=None,
            correct_value=None,
        )

    correct_value = parse_fraction_answer(correct_answer)
    if correct_value is None:
        raise ValueError(
            f"correct_answer {correct_answer!r} is not a parseable fraction -- "
            "authored content is misconfigured"
        )

    submitted_value = parse_fraction_answer(raw_answer)
    if submitted_value is None:
        return AnswerValidationResult(
            outcome=AnswerOutcome.UNPARSEABLE,
            submitted_value=None,
            correct_value=correct_value,
        )

    outcome = AnswerOutcome.CORRECT if submitted_value == correct_value else AnswerOutcome.INCORRECT
    return AnswerValidationResult(
        outcome=outcome, submitted_value=submitted_value, correct_value=correct_value
    )
