"""PROTÉGÉ bounded LLM roles (roadmap P5-P6, P17, P20-P21).

Roles in this package propose bounded outputs only. They never have authority
over mastery, verification, reward, or session transitions.
"""

from .beliefs import apply_diagnosis_to_beliefs
from .calibration import CalibrationParams, calibrate_confidence, fit_calibration
from .diagnostician import DiagnosticContext, diagnose
from .errors import (
    DiagnosticianError,
    DistractorNotInClosedSetError,
    NoCandidatePoolError,
    NoClosedSetProvidedError,
    PromptTemplateError,
    RoleError,
    UnknownMisconceptionError,
)
from .eval import (
    AttemptOutcome,
    EvalReport,
    HeldOutCalibrationReport,
    NvidiaEvalReport,
    PerClassMetrics,
    evaluate_rule_based_only,
    evaluate_with_router,
    evaluate_with_router_calibrated_held_out,
    per_class_metrics,
    run_nvidia_diagnostician_evaluation,
)
from .evidence_span import describe_explanation, extract_evidence_span
from .golden_set import DATASET_STATUS, GoldenExample, load_golden_set, split_golden_set
from .rule_based import rule_based_diagnosis
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
    "DATASET_STATUS",
    "AttemptOutcome",
    "CalibrationParams",
    "DiagnosticContext",
    "DiagnosticianError",
    "DistractorNotInClosedSetError",
    "EvalReport",
    "GoldenExample",
    "HeldOutCalibrationReport",
    "NoCandidatePoolError",
    "NoClosedSetProvidedError",
    "NvidiaEvalReport",
    "PerClassMetrics",
    "PromptTemplateError",
    "RoleError",
    "SproutAttemptRecord",
    "SproutConstraints",
    "SproutDialogueTurn",
    "SproutGenerationResult",
    "SproutGenerator",
    "SproutState",
    "SproutValidationResult",
    "SproutValidationStage",
    "UnknownMisconceptionError",
    "apply_diagnosis_to_beliefs",
    "calibrate_confidence",
    "compile_constraints",
    "describe_explanation",
    "diagnose",
    "emit_authored_fallback",
    "evaluate_rule_based_only",
    "evaluate_with_router",
    "evaluate_with_router_calibrated_held_out",
    "extract_evidence_span",
    "fit_calibration",
    "load_golden_set",
    "per_class_metrics",
    "presentation_emotion_for",
    "rule_based_diagnosis",
    "run_nvidia_diagnostician_evaluation",
    "score_fidelity",
    "select_candidate_pool",
    "split_golden_set",
    "validate_generated_turn",
]
