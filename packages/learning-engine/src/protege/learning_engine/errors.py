"""Domain-specific exceptions for the P2 deterministic learning engine.

P2 never hides a numerical problem behind a silent clamp, a NaN, or an
invented default; every degenerate input that would otherwise produce an
undefined or meaningless result raises one of these instead (task
instruction: "Do not hide numerical problems with arbitrary clamping").
"""


class LearningEngineError(Exception):
    """Base class for every P2 domain error."""


class DegenerateBKTParametersError(LearningEngineError):
    """Raised when BKT parameters make the observation-posterior
    denominator zero (a mathematically undefined update), e.g.
    ``p_know=0`` with ``guess=0`` on a correct observation, or
    ``slip=0`` with ``guess=1`` on an incorrect one."""


class UndefinedDistractorLikelihoodError(LearningEngineError):
    """Raised when an observed distractor has neither an explicit
    authored entry nor an authored ``"other"`` fallback in a
    misconception's ``distractor_likelihood`` table -- P(d | M_k)
    (docs/DECISIONS.md D10: the authored table is authoritative; P2
    never invents a value in its place). Also raised when the whole
    ``distractor_likelihood`` table is absent for a tracked misconception."""


class UndefinedComplementLikelihoodError(LearningEngineError):
    """Raised when an observed distractor has neither an explicit
    authored entry nor an authored ``"other"`` fallback in a
    misconception's *complement* likelihood table -- P(d | not M_k)
    (docs/DECISIONS.md D13: the independent-Bernoulli update requires
    this table and P2 never invents a value in its place, never treats
    it as zero, and never substitutes ``distractor_likelihood``'s own
    ``"other"`` bucket for it). Also raised when the whole complement
    table is absent for a tracked misconception -- "missing complement
    data must fail closed" (D13)."""


class MisconceptionNormalizationError(LearningEngineError):
    """Raised when a misconception's independent Bayes update
    (docs/DECISIONS.md D13) has a zero denominator -- i.e.
    ``P(d|M_k)*P(M_k) + P(d|not M_k)*(1-P(M_k))`` evaluates to zero --
    so no posterior is mathematically defined for that misconception."""


class InvalidEloRatingError(LearningEngineError):
    """Raised when an Elo rating falls outside the documented EloRating
    domain (``protege.contracts.ids.EloRating``: 0-3000)."""
