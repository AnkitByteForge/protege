"""``/v1/learners/{id}/*`` (roadmap P10)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import Actor, ActorRole, get_current_actor
from ..authz import get_owned_learner, require_tutor_or_admin
from ..deps import get_db
from ..repositories.evidence import EvidenceRepository
from ..repositories.learning_state import LearningStateRepository
from ..repositories.proof import ProofRepository
from ..schemas import (
    EvidenceTreeNodeOut,
    LearnerStateOut,
    MisconceptionBeliefOut,
    NotYetAvailableOut,
    ProofCardOut,
    ProofClaimOut,
    ProofSentenceOut,
    SkillMasteryOut,
)

router = APIRouter(tags=["learners"])


@router.get("/v1/learners/{learner_id}/state", response_model=LearnerStateOut)
async def get_learner_state_route(
    learner_id: uuid.UUID,
    actor: Actor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db),
) -> LearnerStateOut:
    """Parent/tutor-scoped mastery view (architecture §23), read straight
    off P9's authoritative ``mastery_estimates``/``misconception_beliefs``
    -- no client-side reconstruction, no re-derivation here."""
    if actor.role == ActorRole.TUTOR:
        require_tutor_or_admin(actor)  # confirms role only; no grant ledger exists yet
    else:
        # PARENT: checked against ownership. ADMIN: get_owned_learner bypasses
        # the ownership check internally but still 404s a nonexistent learner.
        await get_owned_learner(session, actor, learner_id)

    repo = LearningStateRepository(session)
    skills = [
        SkillMasteryOut(
            skill_code=item.skill_code,
            p_known=float(item.row.p_known),
            evidence_count=item.row.evidence_count,
            unaided_correct=item.row.unaided_correct,
            transfer_verified=item.row.transfer_verified,
            computed_at=item.row.computed_at,
        )
        for item in await repo.list_mastery_for_learner(learner_id)
    ]
    misconceptions = [
        MisconceptionBeliefOut(
            misconception_code=item.misconception_code,
            p_holds=float(item.row.p_holds),
            state=item.row.state,
            resolved_at=item.row.resolved_at,
        )
        for item in await repo.list_misconception_beliefs_for_learner(learner_id)
    ]
    return LearnerStateOut(learner_id=learner_id, skills=skills, misconceptions=misconceptions)


@router.get("/v1/learners/{learner_id}/proof", response_model=ProofCardOut | NotYetAvailableOut)
async def get_learner_proof_route(
    learner_id: uuid.UUID,
    actor: Actor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """The parent proof card (roadmap P20): the most recent
    ``ProofArtifact`` for this learner, with every claim's evidence tree
    resolved fresh (never a stored second copy -- see
    ``repositories/proof.py``). Same authz shape as ``/state`` above:
    tutor/admin bypass ownership (no time-boxed grant ledger exists yet,
    same disclosed P10 gap ``authz.require_tutor_or_admin`` already
    documents); a parent may only reach their own linked learner.

    Falls back to the same canonical ``NotYetAvailableOut`` roadmap P10
    already established -- before any session completes, or if the async
    P20 job has not yet run, there is still nothing to fabricate."""
    if actor.role not in (ActorRole.TUTOR, ActorRole.ADMIN):
        await get_owned_learner(session, actor, learner_id)

    artifact = await ProofRepository(session).get_latest_for_learner(learner_id)
    if artifact is None:
        body = NotYetAvailableOut(
            learner_id=learner_id,
            message="Nothing to show yet -- this appears after a completed session.",
        ).model_dump(mode="json")
        return JSONResponse(status_code=200, content=body)

    evidence_repo = EvidenceRepository(session)
    claims_out: list[ProofClaimOut] = []
    tonight_action: str | None = None
    duration_minutes: int | None = None

    for raw_record in artifact.claims:
        record: dict[str, Any] = raw_record if isinstance(raw_record, dict) else {}
        claim_dict: dict[str, Any] = dict(record.get("claim", {}))
        evidence_ids = [str(eid) for eid in claim_dict.get("evidence_ids", [])]
        nodes = await evidence_repo.resolve_claim(evidence_ids, learner_row_id=learner_id)
        claims_out.append(
            ProofClaimOut(
                claim_id=str(claim_dict.get("id", "")),
                text=str(claim_dict.get("text", "")),
                threshold_id=claim_dict.get("threshold_id"),
                caveats=[str(c) for c in claim_dict.get("caveats", [])],
                transfer_verified=bool(record.get("transfer_verified", False)),
                sentences=[
                    ProofSentenceOut(
                        text=str(s.get("text", "")),
                        evidence_ids=[str(e) for e in s.get("evidence_ids", [])],
                    )
                    for s in record.get("sentences", [])
                ],
                evidence=[
                    EvidenceTreeNodeOut(
                        evidence_id=node.evidence.external_ref or "",
                        kind=node.evidence.kind,
                        weight=float(node.evidence.weight),
                        payload=dict(node.evidence.payload),
                        occurred_at=node.evidence.created_at,
                        event_type=node.source_event.event_type if node.source_event else None,
                        session_id=node.evidence.session_id,
                        turn_id=node.evidence.turn_id,
                    )
                    for node in nodes
                ],
            )
        )
        record_tonight_action = record.get("tonight_action")
        if isinstance(record_tonight_action, str):
            tonight_action = record_tonight_action
        record_duration = record.get("duration_minutes")
        if isinstance(record_duration, int):
            duration_minutes = record_duration

    card = ProofCardOut(
        learner_id=learner_id,
        session_id=artifact.session_id,
        generated_at=artifact.created_at,
        duration_minutes=duration_minutes,
        claims=claims_out,
        tonight_action=tonight_action,
    )
    return JSONResponse(status_code=200, content=card.model_dump(mode="json"))


@router.get("/v1/learners/{learner_id}/tutor-brief", response_model=NotYetAvailableOut)
async def get_learner_tutor_brief_route(
    learner_id: uuid.UUID,
    actor: Actor = Depends(get_current_actor),
    session: AsyncSession = Depends(get_db),
) -> NotYetAvailableOut:
    """Tutor Briefs are generated by P21, which has not shipped. Gated to
    tutor/admin roles (architecture §23: "Requires time-boxed tutor
    grant") -- P10 does not implement the grant ledger itself; see
    ``authz.require_tutor_or_admin``'s docstring."""
    require_tutor_or_admin(actor)
    return NotYetAvailableOut(
        learner_id=learner_id,
        message="Tutor briefs are generated by a later phase (P21) and are not available yet.",
    )
