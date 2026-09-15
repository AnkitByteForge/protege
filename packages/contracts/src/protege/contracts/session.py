"""Session-layer contracts: explanations, diagnoses, policy decisions, and
the domain event envelope (ARCHITECTURE.md §7.3, §11.3, §22, §24).

``Explanation`` is a discriminated union on ``modality`` — the four teach-back
input channels (§1.4). The §38 worked example predates the discriminator, so
the ``WorkedExample`` envelope carries its evidence as plain fields and
converts; see ``worked_example.py``.
"""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .base import JSONValue, ProtegeBaseModel, SchemaVersion
from .enums import (
    EventType,
    MisconceptionState,
    PolicyAction,
    UnderstandingSignal,
)
from .ids import (
    EventId,
    LearnerId,
    MisconceptionCode,
    OpaqueId,
    PositiveInt,
    Probability,
    SessionId,
    SkillCode,
    TraceId,
)


class ManipulativeAction(ProtegeBaseModel):
    """One manipulative interaction in a trace (§38: ``{t, action, target}``).

    The trace is a first-class diagnostic input, equal in standing to speech
    (roadmap P13): a child who aligns two bars has demonstrated understanding
    without a word.
    """

    t: float = Field(ge=0, description="Seconds since the item was presented.")
    action: str = Field(examples=["drag", "align", "snap"])
    target: str | None = None
    targets: list[str] | None = None


class ExplanationBase(ProtegeBaseModel):
    """Shared fields for every explanation modality."""

    explanation_id: OpaqueId | None = Field(default=None, alias="id")
    skill_code: SkillCode | None = None
    text: str | None = None


class VoiceExplanation(ExplanationBase):
    """Spoken explanation; ASR confidence gates diagnosis (§7.3 abstention)."""

    modality: Literal["voice"] = "voice"
    text: str
    asr_confidence: Probability


class TextExplanation(ExplanationBase):
    """Typed explanation."""

    modality: Literal["text"] = "text"
    text: str


class ManipulativeExplanation(ExplanationBase):
    """Non-verbal teach-back: the child shows it with the manipulative."""

    modality: Literal["manipulative"] = "manipulative"
    manipulative_trace: list[ManipulativeAction] = Field(min_length=1)


class CardExplanation(ExplanationBase):
    """Explanation chosen from the 3 authored cards (§19.2)."""

    modality: Literal["explanation_card"] = "explanation_card"
    card_ids: list[str] = Field(min_length=1)


Explanation = Annotated[
    VoiceExplanation | TextExplanation | ManipulativeExplanation | CardExplanation,
    Field(discriminator="modality"),
]
"""The four teach-back channels (ARCHITECTURE.md §1.4). Voice is an
enhancement, never a requirement — a mute child completes the loop."""


class DiagnosisLabel(ProtegeBaseModel):
    """One closed-set label from the Diagnostician (§7.3, §38).

    The wire key is ``misconception_id`` (§7.3); the value is the library
    code (``M003``).
    """

    misconception_code: MisconceptionCode = Field(alias="misconception_id")
    state: MisconceptionState = MisconceptionState.UNRESOLVED
    confidence: Probability
    evidence_span: str | None = None


class DiagnosisResult(ProtegeBaseModel):
    """Diagnostician output — closed set only, abstention over guessing (§7.3)."""

    labels: list[DiagnosisLabel] = Field(default_factory=list, max_length=8)
    understanding_signals: list[UnderstandingSignal] = Field(default_factory=list)
    asr_reliable: bool = True
    abstained: bool = False
    model_run_id: OpaqueId | None = None

    @model_validator(mode="after")
    def _abstention_has_no_labels(self) -> "DiagnosisResult":
        if self.abstained and self.labels:
            raise ValueError("an abstaining diagnosis must not carry labels (§7.3)")
        return self


class PolicyDecisionState(ProtegeBaseModel):
    """The 14-dim context vector at decision time (§11.2, §11.3)."""

    vector: list[float] = Field(min_length=14, max_length=14)
    schema_version: str = "state.v1"


class PolicyDecisionAction(ProtegeBaseModel):
    """The chosen action, its source, and the logged counterfactual (§11.3)."""

    type: PolicyAction
    params: dict[str, JSONValue] = Field(default_factory=dict)
    source: Literal["rules", "bandit"] = "rules"
    shield_overrode: bool = False
    counterfactual_bandit_choice: PolicyAction | None = None


class PolicyDecisionReward(ProtegeBaseModel):
    """Immediate reward plus deferred components (§11.3).

    Time-on-task has coefficient zero by construction (§11.2).
    """

    immediate: float | None = None
    deferred_pending: list[str] = Field(default_factory=list)


class PolicyDecision(ProtegeBaseModel):
    """One policy trajectory step — the RL training substrate (§11.3, §22).

    Logged for a future policy from day one while shipping today's rules.
    """

    trajectory_id: OpaqueId = Field(examples=["traj_..."])
    step: PositiveInt
    state: PolicyDecisionState
    action: PolicyDecisionAction
    observation: dict[str, JSONValue] = Field(default_factory=dict)
    reward: PolicyDecisionReward = Field(default_factory=PolicyDecisionReward)
    next_state_ref: str | None = None


class DomainEvent(ProtegeBaseModel):
    """Domain event envelope (§24). The event log is the RL substrate and the
    audit trail: append-only, ``schema_version`` on every envelope, consumers
    ignore unknown fields. Never mutate a payload shape in place.
    """

    event_id: EventId = Field(alias="id")
    event_type: EventType
    schema_version: SchemaVersion = "1.0"
    occurred_at: datetime
    learner_id: LearnerId | None = None
    session_id: SessionId | None = None
    trace_id: TraceId | None = None
    payload: dict[str, JSONValue] = Field(default_factory=dict)
