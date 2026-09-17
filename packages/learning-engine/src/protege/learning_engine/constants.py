"""Named model constants for the P2 deterministic learning engine.

Every numeric constant used by more than one function, or that appears in
a canonical document or a locked decision, is declared exactly once here
and imported by name elsewhere -- never duplicated as a magic number.

References:
- ``ELO_K_FACTOR``, ``ELO_SCALE``, ``MIN_ELO_RATING``, ``MAX_ELO_RATING``:
  locked in ``docs/DECISIONS.md`` D10 (standard logistic Elo, K=24); the
  rating bounds mirror ``protege.contracts.ids.EloRating`` (0-3000) as a
  plain numeric invariant, not a second source of truth for state (see
  ``mastery_engine.py``'s module docstring).
- ``DEFAULT_EVIDENCE_WEIGHT``, ``HINT_DISCOUNT_WEIGHT``,
  ``HINT_DISCOUNT_THRESHOLD``, ``VERIFICATION_EVIDENCE_WEIGHT``:
  ``PROTEGE_ARCHITECTURE.md`` §10.1 rules 2 and 4; also
  ``protege.contracts.ids.ProbabilityWeight``'s docstring (bounds
  0.0-3.0, matching ``VERIFICATION_EVIDENCE_WEIGHT`` exactly).
- ``MASTERY_P_KNOWN_THRESHOLD``, ``MASTERY_MIN_UNAIDED_CORRECT``,
  ``MASTERY_MIN_TRANSFER_ATTEMPTS``: ``PROTEGE_ARCHITECTURE.md`` §17
  provenance chain (``th_02``) and roadmap P2 ("P(L) >= 0.85 AND >= 3
  unaided correct AND >= 1 transfer attempted").
- ``MAX_READING_GRADE_LEVEL``: roadmap P3 testing ("Reading level <=
  Grade 3.5 on all child-facing text"), enforced here because P2's
  ``educational_validator`` is the shared validator P3 content depends on.
"""

from typing import Final

MODEL_VERSION: Final[str] = "learning-engine-v1"
"""Written by callers into ``MasteryEstimate.model_version`` so a mastery
number stays reproducible against the exact formulas that produced it."""

# --- Elo (docs/DECISIONS.md D10) -------------------------------------------

ELO_K_FACTOR: Final[int] = 24
"""Standard logistic Elo K-factor, locked in docs/DECISIONS.md D10."""

ELO_SCALE: Final[float] = 400.0
"""Logistic scale divisor: E = 1 / (1 + 10 ** ((R_item - R_learner) / ELO_SCALE))."""

MIN_ELO_RATING: Final[int] = 0
MAX_ELO_RATING: Final[int] = 3000

# --- Evidence weighting (ARCHITECTURE.md §10.1 rules 2, 4) ------------------

DEFAULT_EVIDENCE_WEIGHT: Final[float] = 1.0
HINT_DISCOUNT_WEIGHT: Final[float] = 0.4
"""An item solved at or above HINT_DISCOUNT_THRESHOLD hints contributes at
this discounted weight."""
HINT_DISCOUNT_THRESHOLD: Final[int] = 2
"""Hint count at or above which HINT_DISCOUNT_WEIGHT applies (architecture:
"solved after 2 hints")."""
VERIFICATION_EVIDENCE_WEIGHT: Final[float] = 3.0
"""Unaided/unseen verification (and transfer) items are weighted 3x
practice items."""

# --- Mastery threshold (ARCHITECTURE.md §17; roadmap P2) -------------------

MASTERY_P_KNOWN_THRESHOLD: Final[float] = 0.85
MASTERY_MIN_UNAIDED_CORRECT: Final[int] = 3
MASTERY_MIN_TRANSFER_ATTEMPTS: Final[int] = 1

# --- Educational validator (roadmap P3 testing; shared with P2) ------------

MAX_READING_GRADE_LEVEL: Final[float] = 3.5
