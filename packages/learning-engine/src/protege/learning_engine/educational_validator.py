"""Deterministic educational validation (``PROTEGE_ARCHITECTURE.md`` §8.4,
§16, §17; roadmap P2 ``educational_validator``: "answer-leak, reading
level, misconception consistency, schema").

No LLM calls anywhere in this module (task instruction). "Schema"
validity is deliberately not re-implemented here: ``packages/contracts``'
own Pydantic models (e.g. ``SproutTurn``'s 30-word check) are the schema
validators at the point generated content is parsed, and this package
does not depend on ``packages/contracts`` or Pydantic (docs/DECISIONS.md
D6; task instruction: "Do not couple to FastAPI/Pydantic unless a P2
requirement explicitly needs them"). Duplicating a schema check here
would also violate ``AGENTS.md``'s "never create a second source of
truth for state already represented elsewhere." This module owns the
three checks that are genuinely NOT schema-level: answer leakage, reading
level, and misconception-consistency (forbidden-phrase) checking.

``reading_level_ok`` is the function roadmap P3 content is explicitly
tested against ("every item passes the P2 validator... Reading level <=
Grade 3.5"), so it lives here rather than being duplicated in a future P3
tool.
"""

import re
from collections.abc import Iterable

from .answer_validator import parse_fraction_answer
from .constants import MAX_READING_GRADE_LEVEL

_FRACTION_TOKEN_RE = re.compile(r"\d+\s+\d+/\d+|\d+/\d+|\b\d+\b")
_WORD_RE = re.compile(r"[A-Za-z']+")
_SENTENCE_END_RE = re.compile(r"[.!?]+")
_VOWEL_GROUP_RE = re.compile(r"[aeiouy]+")


def answer_leaked(utterance: str, correct_answer: str) -> bool:
    """Zero-tolerance answer-leak check (§16, §17): deterministic
    substring match OR numeric equivalence -- never an LLM judge
    (§8.4: "deterministic: answer string absent").

    Two independent checks, either of which flags a leak:

    1. A case-insensitive literal substring match of ``correct_answer``
       within ``utterance``.
    2. Numeric equivalence: every fraction-shaped token in ``utterance``
       is parsed via :func:`~protege.learning_engine.answer_validator.\
parse_fraction_answer` and compared, exactly, to the parsed
       ``correct_answer`` -- this catches an equivalent-but-differently-
       written leak (e.g. correct answer "1/4", utterance contains "2/8").
    """
    normalized_utterance = utterance.lower()
    normalized_answer = correct_answer.strip().lower()
    if normalized_answer and normalized_answer in normalized_utterance:
        return True

    correct_value = parse_fraction_answer(correct_answer)
    if correct_value is None:
        return False
    for match in _FRACTION_TOKEN_RE.finditer(utterance):
        candidate = parse_fraction_answer(match.group(0))
        if candidate is not None and candidate == correct_value:
            return True
    return False


def contains_forbidden_phrase(utterance: str, forbidden_phrases: Iterable[str]) -> str | None:
    """Deterministic, case-insensitive substring check against a list of
    literal forbidden phrases/words (e.g. a ``Misconception.sprout_forbidden``
    entry that is literal vocabulary, such as ``"numerator"``/``"denominator"``).
    Returns the first matching forbidden phrase, or ``None``.

    This is a literal substring check only -- it cannot detect a
    semantic violation phrased as free text (e.g. an authored forbidden
    entry like "stating 1/4 > 1/8 before resolution"); that class of
    violation is covered either by :func:`answer_leaked` (when it is
    literally the answer) or requires an LLM judge (§8.4 fidelity score),
    which is out of P2's deterministic scope.
    """
    normalized = utterance.lower()
    for phrase in forbidden_phrases:
        if phrase.lower() in normalized:
            return phrase
    return None


def count_syllables(word: str) -> int:
    """Vowel-group heuristic syllable count.

    No dependency added (task instruction forbids new third-party
    dependencies) -- this is the standard lightweight heuristic used when
    a syllable-counting library is unavailable: count vowel-sound groups,
    then drop one for a silent trailing "e" on longer words. It is an
    approximation, as all such heuristics are; documented as such rather
    than presented as exact.
    """
    normalized = word.lower().strip(".,!?;:\"'")
    if not normalized:
        return 0
    groups = _VOWEL_GROUP_RE.findall(normalized)
    count = len(groups)
    if normalized.endswith("e") and not normalized.endswith("le") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_kincaid_grade(text: str) -> float:
    """Flesch-Kincaid Grade Level:

        FKGL = 0.39*(words/sentences) + 11.8*(syllables/words) - 15.59

    Approximate (heuristic syllable counting via :func:`count_syllables`;
    no ``textstat``-style dependency added). Returns ``0.0`` for
    empty/whitespace-only text, or text with no sentence-ending
    punctuation (treated as a single sentence).
    """
    words = _WORD_RE.findall(text)
    if not words:
        return 0.0
    sentence_count = max(len(_SENTENCE_END_RE.findall(text)), 1)
    syllable_count = sum(count_syllables(w) for w in words)
    word_count = len(words)
    return 0.39 * (word_count / sentence_count) + 11.8 * (syllable_count / word_count) - 15.59


def reading_level_ok(text: str, *, max_grade: float = MAX_READING_GRADE_LEVEL) -> bool:
    """``True`` iff :func:`flesch_kincaid_grade` is at or below
    ``max_grade`` (roadmap default: Grade 3.5)."""
    return flesch_kincaid_grade(text) <= max_grade
