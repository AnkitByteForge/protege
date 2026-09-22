"""Wire response/request shapes for the P10 REST API.

Thin wrappers over ``engine/runtime.py``'s dataclasses and the P9 ORM rows --
never a place business logic lives (roadmap rule 5: "Do not move learning
logic into FastAPI route handlers"). Contract objects already designed for
the wire (``SproutTurn``, ``DiagnosisResult``) are embedded directly rather
than re-declared.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from protege.contracts import DiagnosisResult, SproutTurn

from .engine.runtime import EventOutcome, SessionView


class ItemPromptOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str
    stem: str


class SessionOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: uuid.UUID
    learner_id: uuid.UUID
    state: str
    started_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    step: int
    next_item: ItemPromptOut | None = None

    @classmethod
    def from_view(cls, view: SessionView, *, next_item: ItemPromptOut | None = None) -> SessionOut:
        return cls(
            session_id=view.session_id,
            learner_id=view.learner_id,
            state=view.state,
            started_at=view.started_at,
            ended_at=view.ended_at,
            end_reason=view.end_reason,
            step=view.step,
            next_item=next_item,
        )


class SessionEventOut(SessionOut):
    sprout_turn: SproutTurn | None = None
    diagnosis: DiagnosisResult | None = None
    hint_text: str | None = None
    misconception_resolved: bool = False
    mastery_verified: bool | None = None

    @classmethod
    def from_outcome(cls, outcome: EventOutcome) -> SessionEventOut:
        next_item = (
            ItemPromptOut(item_id=outcome.next_item.item_id, stem=outcome.next_item.stem)
            if outcome.next_item is not None
            else None
        )
        return cls(
            session_id=outcome.session.session_id,
            learner_id=outcome.session.learner_id,
            state=outcome.session.state,
            started_at=outcome.session.started_at,
            ended_at=outcome.session.ended_at,
            end_reason=outcome.session.end_reason,
            step=outcome.session.step,
            next_item=next_item,
            sprout_turn=outcome.sprout_turn,
            diagnosis=outcome.diagnosis,
            hint_text=outcome.hint_text,
            misconception_resolved=outcome.misconception_resolved,
            mastery_verified=outcome.mastery_verified,
        )


class SessionCreateIn(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_id: uuid.UUID


class SkillMasteryOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_code: str
    p_known: float
    evidence_count: int
    unaided_correct: int
    transfer_verified: bool
    computed_at: datetime


class MisconceptionBeliefOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    misconception_code: str
    p_holds: float
    state: str
    resolved_at: datetime | None


class LearnerStateOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    learner_id: uuid.UUID
    skills: list[SkillMasteryOut]
    misconceptions: list[MisconceptionBeliefOut]


class EvidenceTreeNodeOut(BaseModel):
    """One resolved node in a claim's clickable evidence tree (roadmap P20;
    ARCHITECTURE.md §17 provenance chain: "evidence -> source event ->
    originating session/turn"). Built fresh on every read from
    ``EvidenceRepository.resolve_claim`` -- never stored a second time."""

    model_config = ConfigDict(frozen=True)

    evidence_id: str
    kind: str
    weight: float
    payload: dict[str, object]
    occurred_at: datetime | None
    event_type: str | None
    session_id: uuid.UUID | None
    turn_id: uuid.UUID | None


class ProofSentenceOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    text: str
    evidence_ids: list[str]


class ProofClaimOut(BaseModel):
    """One ``ProofClaim`` plus its resolved evidence tree (roadmap P20:
    "every claim expands to its evidence tree"). ``transfer_verified`` is
    surfaced as its own field, deliberately never folded into ``text`` --
    roadmap P20: "transfer_verified shown separately"."""

    model_config = ConfigDict(frozen=True)

    claim_id: str
    text: str
    threshold_id: str | None
    sentences: list[ProofSentenceOut]
    caveats: list[str]
    transfer_verified: bool
    evidence: list[EvidenceTreeNodeOut]


class ProofCardOut(BaseModel):
    """The parent proof card (roadmap P20). No score, no percentage, no
    letter grade appears anywhere in this shape -- only claims, evidence,
    mandatory caveats, and one concrete action."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ready"] = "ready"
    learner_id: uuid.UUID
    session_id: uuid.UUID | None
    generated_at: datetime
    duration_minutes: int | None
    claims: list[ProofClaimOut]
    tonight_action: str | None


class NotYetAvailableOut(BaseModel):
    """Roadmap P10: "If those artifacts do not yet have writers ... return
    the canonical not-yet-available representation instead of fabricating
    data." Used for ``/proof`` and ``/tutor-brief`` until P20/P21 exist."""

    model_config = ConfigDict(frozen=True)

    status: Literal["not_yet_available"] = "not_yet_available"
    learner_id: uuid.UUID
    message: str = Field(
        default="This isn't ready yet -- proof artifacts are generated by a later phase."
    )


class DeletionRequestOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: uuid.UUID
    parent_id: uuid.UUID
    status: Literal["recorded"] = "recorded"
