"""The P3 <-> P2 validation boundary.

Reading-level validation is P2's responsibility (roadmap P2: the
``educational_validator`` in ``packages/learning-engine``, checking
Flesch-Kincaid grade level per ARCHITECTURE.md §8.4/§16). P3 must not
duplicate that implementation, and P3 must be able to run its own content
gate before P2 merges (docs/DECISIONS.md D6/D9 spirit: packages stay
independently importable; roadmap: "P3 can proceed without P2 being
merged").

This module is the *only* place P3 names that boundary. It defines the
narrow interface P3 needs, a null adapter that P3's own CI runs against
today, and documents exactly what wiring the real gate requires once
``packages/learning-engine`` ships ``educational_validator`` on a merged
``main``. Nothing here imports ``protege.learning_engine`` — that import is
added at the call site once P2 lands, not speculatively here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class ReadingLevelPort(Protocol):
    """What P3 expects from P2's ``educational_validator`` for content review.

    Expected shape, once wired to the real implementation
    (``protege.learning_engine.educational_validator``):

    - ``check(text, max_grade)`` returns ``True`` when ``text`` scores at or
      below ``max_grade`` on the same reading-level formula P2 uses
      elsewhere in the pipeline (ARCHITECTURE.md §8.4: Flesch-Kincaid <= 3.5
      for Sprout output; P3 content — stems, sprout utterances, intervention
      scripts — should be held to the same bar).
    - It never raises on ordinary text; a formula failure should be a
      logged abstention (``None``), not an exception, so one malformed
      sentence cannot fail an entire content-pack validation run.
    """

    def check(self, text: str, max_grade: float) -> bool | None: ...


@dataclass(frozen=True)
class NullReadingLevelPort:
    """The P3-side default: reading level is NOT evaluated.

    Used until ``packages/learning-engine`` merges its P2
    ``educational_validator`` and a call site wires the real port in. Every
    check abstains (returns ``None``) rather than fabricating a pass or a
    fail — the content manifest reports this explicitly as
    ``"not_evaluated (pending P2 merge)"`` so nobody mistakes silence for a
    passing grade-level check.
    """

    def check(self, text: str, max_grade: float) -> bool | None:
        return None


READING_LEVEL_STATUS_PENDING = "not_evaluated (pending P2 merge)"
"""Manifest status string used whenever the reading-level port abstains."""
