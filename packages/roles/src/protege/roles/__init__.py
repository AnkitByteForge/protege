"""PROTÉGÉ bounded LLM roles (ARCHITECTURE.md §7; roadmap P5+).

Only the Sprout Generator (roadmap P5) exists in this package today. Each
role in this family proposes only -- it never has authority over mastery,
verification, reward, or session transitions (AGENTS.md non-negotiable
principles).
"""

from .sprout import (
    SproutAttemptRecord,
    SproutConstraints,
    SproutDialogueTurn,
    SproutGenerationResult,
    SproutGenerator,
    SproutState,
    SproutValidationResult,
    SproutValidationStage,
    compile_constraints,
    emit_authored_fallback,
    presentation_emotion_for,
    score_fidelity,
    select_candidate_pool,
    validate_generated_turn,
)

__all__ = [
    "SproutAttemptRecord",
    "SproutConstraints",
    "SproutDialogueTurn",
    "SproutGenerationResult",
    "SproutGenerator",
    "SproutState",
    "SproutValidationResult",
    "SproutValidationStage",
    "compile_constraints",
    "emit_authored_fallback",
    "presentation_emotion_for",
    "score_fidelity",
    "select_candidate_pool",
    "validate_generated_turn",
]
