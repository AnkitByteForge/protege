"""PROTÉGÉ deterministic learning engine (roadmap P2).

Pure functions only: answer validation (exact rational arithmetic), BKT +
misconception Bayes mastery estimation, Elo item difficulty, the
educational validator, and the mastery threshold service. No I/O, no
framework coupling, no Pydantic/packages/contracts dependency
(docs/DECISIONS.md D6) -- importable by the session service, the
evaluation harness (P24), and tests alike.

See docs/DECISIONS.md D10 for the locked Elo and Bayesian
zero-likelihood formulas, and D11 for implementation-level interpretive
choices this package makes that go beyond D10 and remain open for review.
"""

from .answer_validator import (
    AnswerOutcome,
    AnswerValidationResult,
    parse_fraction_answer,
    validate_answer,
)
from .constants import (
    DEFAULT_EVIDENCE_WEIGHT,
    ELO_K_FACTOR,
    ELO_SCALE,
    HINT_DISCOUNT_THRESHOLD,
    HINT_DISCOUNT_WEIGHT,
    MASTERY_MIN_TRANSFER_ATTEMPTS,
    MASTERY_MIN_UNAIDED_CORRECT,
    MASTERY_P_KNOWN_THRESHOLD,
    MAX_ELO_RATING,
    MAX_READING_GRADE_LEVEL,
    MIN_ELO_RATING,
    MODEL_VERSION,
    VERIFICATION_EVIDENCE_WEIGHT,
)
from .educational_validator import (
    answer_leaked,
    contains_forbidden_phrase,
    count_syllables,
    flesch_kincaid_grade,
    reading_level_ok,
)
from .errors import (
    DegenerateBKTParametersError,
    InvalidEloRatingError,
    LearningEngineError,
    MisconceptionNormalizationError,
    UndefinedComplementLikelihoodError,
    UndefinedDistractorLikelihoodError,
)
from .evidence_builder import (
    BuiltEvidence,
    ResponseObservation,
    TeachingEpisodeObservation,
    TransferObservationInput,
    build_response_evidence,
    build_teaching_episode_evidence,
    build_transfer_evidence,
    evidence_weight,
)
from .mastery_engine import (
    OTHER_DISTRACTOR_KEY,
    BKTParameters,
    bkt_posterior,
    bkt_update,
    elo_expected_score,
    mastery_effective,
    misconception_belief_update,
    update_item_elo,
)
from .threshold_service import ThresholdDecision, ThresholdInputs, evaluate_mastery_threshold

__version__ = "0.1.0"

__all__ = [  # noqa: RUF022
    # Answer validation
    "AnswerOutcome",
    "AnswerValidationResult",
    "parse_fraction_answer",
    "validate_answer",
    # Mastery engine: BKT
    "BKTParameters",
    "bkt_posterior",
    "bkt_update",
    # Mastery engine: Elo
    "elo_expected_score",
    "update_item_elo",
    # Mastery engine: misconception Bayes + derived mastery
    "OTHER_DISTRACTOR_KEY",
    "misconception_belief_update",
    "mastery_effective",
    # Educational validator
    "answer_leaked",
    "contains_forbidden_phrase",
    "count_syllables",
    "flesch_kincaid_grade",
    "reading_level_ok",
    # Threshold service
    "ThresholdInputs",
    "ThresholdDecision",
    "evaluate_mastery_threshold",
    # Evidence builder
    "ResponseObservation",
    "TeachingEpisodeObservation",
    "TransferObservationInput",
    "BuiltEvidence",
    "evidence_weight",
    "build_response_evidence",
    "build_teaching_episode_evidence",
    "build_transfer_evidence",
    # Constants
    "MODEL_VERSION",
    "ELO_K_FACTOR",
    "ELO_SCALE",
    "MIN_ELO_RATING",
    "MAX_ELO_RATING",
    "DEFAULT_EVIDENCE_WEIGHT",
    "HINT_DISCOUNT_WEIGHT",
    "HINT_DISCOUNT_THRESHOLD",
    "VERIFICATION_EVIDENCE_WEIGHT",
    "MASTERY_P_KNOWN_THRESHOLD",
    "MASTERY_MIN_UNAIDED_CORRECT",
    "MASTERY_MIN_TRANSFER_ATTEMPTS",
    "MAX_READING_GRADE_LEVEL",
    # Errors
    "LearningEngineError",
    "DegenerateBKTParametersError",
    "UndefinedDistractorLikelihoodError",
    "UndefinedComplementLikelihoodError",
    "MisconceptionNormalizationError",
    "InvalidEloRatingError",
]
