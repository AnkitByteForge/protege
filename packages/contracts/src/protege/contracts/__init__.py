"""PROTÉGÉ shared contracts.

P1 defines the domain vocabulary here exactly once — Skill, Misconception,
LearningItem, Evidence, MasteryEstimate, Diagnosis, DomainEvent, … — so the
Python service, the generated TypeScript types, the content packages, and the
eval harness cannot drift (roadmap P1).

Versioning: additive-only within a major. Consumers ignore unknown fields
(``extra="ignore"``). ``content/schema/*.json`` is generated from these
models (``make types`` / ``python -m protege.contracts.export``); the
schema-snapshot test fails loudly on any change, forcing a conscious bump.
"""

from .artifacts import ProofClaim, TutorBriefing
from .base import JSONValue, ProtegeBaseModel, SchemaVersion
from .content import (
    Concept,
    Distractor,
    Intervention,
    ItemVersion,
    LearningItem,
    Misconception,
    MissingComplementLikelihoodError,
    Prerequisite,
    Skill,
    SproutScript,
    TransferItem,
)
from .enums import (
    ConfidenceLabel,
    EventType,
    EvidenceKind,
    ExplanationModality,
    InterventionType,
    ItemRole,
    MisconceptionState,
    PedagogicalRole,
    PolicyAction,
    RepresentationType,
    RewardKind,
    SafetySeverity,
    SessionEndReason,
    SessionState,
    SproutConfidenceShown,
    SproutPresentationEmotion,
    SproutScriptEmotion,
    TurnSpeaker,
    UnderstandingSignal,
)
from .ids import (
    ClaimId,
    ContentVersion,
    EloRating,
    EpisodeId,
    EventId,
    EvidenceId,
    ExplanationId,
    GradeBand,
    InterventionId,
    ItemId,
    LearnerId,
    MisconceptionCode,
    OpaqueId,
    PositiveInt,
    Probability,
    ProbabilityWeight,
    SessionId,
    SkillCode,
    SproutScriptId,
    TraceId,
)
from .learning_state import (
    Evidence,
    MasteryEstimate,
    MasteryOutcome,
    MisconceptionBelief,
    TeachingEpisode,
)
from .roles import CoachHint, ReportDraft, ReportSentence, SproutTurn
from .session import (
    CardExplanation,
    DiagnosisLabel,
    DiagnosisResult,
    DomainEvent,
    Explanation,
    ManipulativeAction,
    ManipulativeExplanation,
    PolicyDecision,
    PolicyDecisionAction,
    PolicyDecisionReward,
    PolicyDecisionState,
    TextExplanation,
    VoiceExplanation,
)
from .worked_example import (
    LearnerEvidence,
    TransferObservation,
    VerificationRecord,
    WorkedExample,
)

__version__ = "0.2.0"

# Grouped by domain (content / learner state / session / role outputs /
# artifacts / worked example / enums / scalars), mirroring the module
# docstring's own vocabulary ordering — not alphabetical by design.
__all__ = [  # noqa: RUF022
    "JSONValue",
    "ProtegeBaseModel",
    "SchemaVersion",
    # Content domain
    "Skill",
    "Concept",
    "Prerequisite",
    "Misconception",
    "MissingComplementLikelihoodError",
    "Distractor",
    "LearningItem",
    "ItemVersion",
    "Intervention",
    "SproutScript",
    "TransferItem",
    # Learner state
    "Evidence",
    "MasteryEstimate",
    "MisconceptionBelief",
    "TeachingEpisode",
    "MasteryOutcome",
    # Session layer
    "Explanation",
    "VoiceExplanation",
    "TextExplanation",
    "ManipulativeExplanation",
    "CardExplanation",
    "ManipulativeAction",
    "DiagnosisLabel",
    "DiagnosisResult",
    "PolicyDecision",
    "PolicyDecisionState",
    "PolicyDecisionAction",
    "PolicyDecisionReward",
    "DomainEvent",
    # Role outputs
    "SproutTurn",
    "CoachHint",
    "ReportSentence",
    "ReportDraft",
    # Artifacts
    "ProofClaim",
    "TutorBriefing",
    # Worked example
    "LearnerEvidence",
    "TransferObservation",
    "VerificationRecord",
    "WorkedExample",
    # Enums
    "ConfidenceLabel",
    "EvidenceKind",
    "EventType",
    "ExplanationModality",
    "InterventionType",
    "ItemRole",
    "MisconceptionState",
    "PedagogicalRole",
    "PolicyAction",
    "RepresentationType",
    "RewardKind",
    "SafetySeverity",
    "SessionEndReason",
    "SessionState",
    "SproutConfidenceShown",
    "SproutPresentationEmotion",
    "SproutScriptEmotion",
    "TurnSpeaker",
    "UnderstandingSignal",
    # Scalars and ids
    "ClaimId",
    "ContentVersion",
    "EloRating",
    "EpisodeId",
    "EventId",
    "EvidenceId",
    "ExplanationId",
    "GradeBand",
    "InterventionId",
    "ItemId",
    "LearnerId",
    "MisconceptionCode",
    "OpaqueId",
    "PositiveInt",
    "Probability",
    "ProbabilityWeight",
    "SessionId",
    "SkillCode",
    "SproutScriptId",
    "TraceId",
]
