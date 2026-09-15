"""Structured learner state and the evidence ledger (ARCHITECTURE.md §22).

These are the authoritative quantities: mastery comes only from validated
responses, misconception beliefs only from Bayes over authored likelihoods.
Semantic memory (vectors) never appears here and never moves a probability
(§12; roadmap P22).

``MasteryOutcome`` is the §38 ``mastery_outcome`` aggregate — the session's
closing record. It is deliberately distinct from the persisted
``MasteryEstimate`` row: the outcome carries the before/after delta and the
claim for the proof artifact.
"""

from datetime import datetime

from pydantic import Field, model_validator

from .base import JSONValue, ProtegeBaseModel
from .enums import EvidenceKind, MisconceptionState
from .ids import (
    EpisodeId,
    EvidenceId,
    LearnerId,
    MisconceptionCode,
    OpaqueId,
    PositiveInt,
    Probability,
    ProbabilityWeight,
    SessionId,
    SkillCode,
)


class Evidence(ProtegeBaseModel):
    """Provenance atom (§22 ``evidence`` table; §17 provenance chain).

    Append-only: you cannot retroactively improve a child's history
    (§43 principle 15). Every parent-facing claim resolves to these rows.
    """

    evidence_id: EvidenceId = Field(alias="id")
    kind: EvidenceKind
    source_event_id: OpaqueId
    weight: ProbabilityWeight = 1.0
    payload: dict[str, JSONValue] = Field(default_factory=dict)
    created_at: datetime | None = None


class MasteryEstimate(ProtegeBaseModel):
    """Authoritative per-skill mastery state (§22 ``mastery_estimates`` DDL)."""

    learner_id: LearnerId
    skill_code: SkillCode
    p_known: Probability
    evidence_count: PositiveInt = 0
    unaided_correct: PositiveInt = 0
    transfer_verified: bool = False
    model_version: str
    computed_at: datetime | None = None


class MisconceptionBelief(ProtegeBaseModel):
    """Per-learner misconception belief (§22 ``misconception_beliefs``).

    A resolved misconception never re-raises without new evidence — the
    learning engine (P2) owns that rule; this contract carries the state.
    """

    learner_id: LearnerId
    misconception_code: MisconceptionCode
    p_holds: Probability
    state: MisconceptionState = MisconceptionState.UNRESOLVED
    resolved_at: datetime | None = None
    resolution_evidence_id: EvidenceId | None = None


class TeachingEpisode(ProtegeBaseModel):
    """One teach-back record (§22 ``teaching_episodes``)."""

    episode_id: EpisodeId = Field(alias="id")
    misconception_code: MisconceptionCode
    turns: PositiveInt
    resolved: bool
    resolution_turn: PositiveInt | None = None
    quality_score: Probability | None = None
    session_id: SessionId | None = None


class MasteryOutcome(ProtegeBaseModel):
    """The §38 ``mastery_outcome`` closing record for a session.

    The §38 document keys misconception posteriors flat
    (``"misconception_M003_after": 0.04``); a before-validator lifts any key
    matching that pattern into ``misconception_posteriors`` so the worked
    example validates verbatim while new code uses the structured field.
    """

    p_known_before: Probability
    p_known_after: Probability
    misconception_posteriors: dict[str, Probability] = Field(default_factory=dict)
    transfer_verified: bool
    claim: str
    evidence_ids: list[EvidenceId] = Field(min_length=1)
    caveats: list[str] = Field(default_factory=list)
    next_review: str | None = Field(
        default=None,
        description="ISO date (§38); scheduling semantics arrive with FSRS (P23).",
    )

    @model_validator(mode="before")
    @classmethod
    def _lift_flat_misconception_keys(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        lifted = {
            key: value
            for key, value in data.items()
            if isinstance(key, str) and key.startswith("misconception_") and key.endswith("_after")
        }
        if not lifted:
            return data
        rest = {key: value for key, value in data.items() if key not in lifted}
        posteriors = dict(rest.pop("misconception_posteriors", {}))
        for key, value in lifted.items():
            code = key.removeprefix("misconception_").removesuffix("_after")
            posteriors[code] = value
        rest["misconception_posteriors"] = posteriors
        return rest
