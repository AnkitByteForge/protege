"""The P9 <-> P8 integration point (roadmap: "minimal P8 integration points
required for persistence").

``persist_thin_thread_result`` takes a real
``protege.thin_thread.engine.ThinThreadResult`` (the exact object
``run_thin_thread`` returns -- P8's own end-to-end, no-DB demo run) and
writes it into the P9 schema: a session row, its transition journal, one
``events`` row per evidence item plus session bookends, the evidence ledger
itself, the authoritative mastery estimate and misconception belief, the
teaching episode, and (if supplied) the router's buffered ``model_runs``.

**Two disclosed fidelity limits**, both because P8's own return type does
not carry the information a fuller integration would need (P8 is
explicitly "no DB" -- ``packages/thin-thread`` is not touched by this
change; see the final P9 report for the full note):

1. ``ThinThreadResult.state_sequence`` is a plain tuple of states (the
   ``Journal.state_sequence`` shape), not ``Journal.records`` -- so the
   *event* name that caused each transition is not recoverable here, and
   every persisted ``session_states.trigger`` reads ``"advance"``. A real
   P10 service wired directly to a live ``SessionOrchestrator`` (which
   *is* the roadmap's actual runtime target) has ``orchestrator.journal``
   and gets the exact event name per transition for free by calling
   ``SessionRepository.append_transition`` once per
   ``TransitionRecord`` instead of this bridge's synthesized loop.
2. Each evidence item's originating domain event is *synthesized* here
   (P8 mints an opaque ``evt_NNN`` id via its own in-memory
   ``IdAllocator`` but never constructs a real ``DomainEvent``), with an
   approximate ``event_type`` inferred from ``EvidenceKind`` and a
   monotonic synthetic ``occurred_at`` (P8 does not timestamp evidence).
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import DomainEvent, EventType, Evidence, EvidenceKind, MasteryEstimate
from protege.llm.telemetry import ModelRunRecord
from protege.thin_thread.engine import ThinThreadResult

from ..repositories.events import EventRepository
from ..repositories.evidence import EvidenceRepository
from ..repositories.learning_state import LearningStateRepository
from ..repositories.model_runs import ModelRunRepository
from ..repositories.sessions import SessionRepository


def _event_type_for_evidence(item: Evidence) -> EventType:
    """Infer the synthesized event's type from one evidence item.

    ``TRANSFER`` is payload-dependent, not a blanket "passed": P8's own
    ``build_transfer_evidence`` (``packages/learning-engine``) always
    attaches evidence for a transfer attempt regardless of outcome, with the
    actual result in ``payload["result"]``. A prior revision of this bridge
    mapped every ``TRANSFER``-kind item straight to ``TRANSFER_PASSED``,
    which fabricated a passing event for a transfer the child actually
    failed -- exactly the kind of falsely-precise event semantics P8 itself
    never produced. ``RESPONSE`` maps to ``ANSWER_SUBMITTED`` regardless of
    correctness, which is accurate: the catalog's ``ANSWER_SUBMITTED`` event
    means only "an answer was submitted," not that it was correct.
    """
    if item.kind == EvidenceKind.RESPONSE:
        return EventType.ANSWER_SUBMITTED
    if item.kind == EvidenceKind.TEACHING_EPISODE:
        return EventType.TEACH_BACK_COMPLETED
    if item.kind == EvidenceKind.TRANSFER:
        passed = bool(item.payload.get("result", False))
        return EventType.TRANSFER_PASSED if passed else EventType.TRANSFER_FAILED
    raise ValueError(f"no event-type mapping for evidence kind {item.kind!r}")


@dataclass(frozen=True)
class PersistedThinThreadRun:
    """Row ids a caller (a test, or a future rehydration check) needs."""

    session_id: uuid.UUID
    learner_id: uuid.UUID
    skill_id: uuid.UUID
    mastery_estimate_id: uuid.UUID | None
    misconception_belief_id: uuid.UUID | None
    evidence_row_ids: dict[str, uuid.UUID]


def _session_end_reason(result: ThinThreadResult) -> str | None:
    final = str(result.final_state)
    if final == "COMPLETE":
        if result.threshold_decision is not None and result.threshold_decision.mastery_verified:
            return "mastery_verified"
        return "progress_made"
    if final == "ABANDONED":
        return "abandoned"
    if final == "ESCALATE_TO_HUMAN":
        return "escalated"
    return None  # session did not reach a terminal state in this run


async def persist_thin_thread_result(
    session: AsyncSession,
    *,
    learner_id: uuid.UUID,
    skill_id: uuid.UUID,
    skill_code: str,
    misconception_id: uuid.UUID,
    result: ThinThreadResult,
    model_runs: Sequence[ModelRunRecord] = (),
) -> PersistedThinThreadRun:
    session_repo = SessionRepository(session)
    event_repo = EventRepository(session)
    evidence_repo = EvidenceRepository(session)
    learning_state_repo = LearningStateRepository(session)
    model_run_repo = ModelRunRepository(session)

    session_row = await session_repo.create_session(
        learner_id=learner_id, initial_state=result.state_sequence[0]
    )

    for step, (from_state, to_state) in enumerate(
        zip(result.state_sequence, result.state_sequence[1:], strict=False), start=1
    ):
        await session_repo.append_transition(
            session_id=session_row.id,
            from_state=from_state,
            to_state=to_state,
            event="advance",  # see module docstring limitation (1)
            occurred_at=datetime.now(UTC),
            step=step,
        )

    end_reason = _session_end_reason(result)
    if end_reason is not None:
        await session_repo.end_session(
            session_id=session_row.id, ended_at=datetime.now(UTC), end_reason=end_reason
        )

    base_time = datetime.now(UTC)
    await event_repo.append(
        DomainEvent(
            id=f"evt_session_started_{session_row.id}",
            event_type=EventType.SESSION_STARTED,
            occurred_at=base_time,
            learner_id=str(learner_id),
            session_id=str(session_row.id),
        ),
        learner_row_id=learner_id,
        session_row_id=session_row.id,
    )  # bookend only; nothing references it back

    # Mastery estimate is upserted BEFORE the evidence loop below, even
    # though the architecture's §22 evidence -> mastery_estimates
    # relationship reads as "evidence supports an estimate" -- the estimate
    # is already fully computed by ``run_thin_thread`` (it does not depend
    # on evidence rows existing in the database), and doing it first lets
    # each RESPONSE/TRANSFER evidence row set the real
    # ``evidence.mastery_estimate_id`` FK on insert, instead of leaving that
    # documented relationship null.
    mastery_estimate_id: uuid.UUID | None = None
    if result.mastery_outcome is not None:
        unaided_correct = sum(
            1
            for item in result.evidence
            if item.kind == EvidenceKind.RESPONSE and float(item.weight) == 3.0
        )
        estimate = MasteryEstimate(
            learner_id=str(learner_id),
            skill_code=skill_code,
            p_known=result.mastery_outcome.p_known_after,
            evidence_count=len(result.evidence),
            unaided_correct=unaided_correct,
            transfer_verified=result.mastery_outcome.transfer_verified,
            model_version="thin-thread-p8-bridge",
        )
        mastery_row = await learning_state_repo.upsert_mastery(
            learner_id=learner_id, skill_id=skill_id, estimate=estimate
        )
        mastery_estimate_id = mastery_row.id

    evidence_row_ids: dict[str, uuid.UUID] = {}
    for index, item in enumerate(result.evidence, start=1):
        event_type = _event_type_for_evidence(item)
        event_row = await event_repo.append(
            DomainEvent(
                id=f"evt_for_{item.evidence_id}",
                event_type=event_type,
                occurred_at=base_time + timedelta(milliseconds=index),
                learner_id=str(learner_id),
                session_id=str(session_row.id),
                payload={"evidence_id": item.evidence_id, "kind": str(item.kind)},
            ),
            learner_row_id=learner_id,
            session_row_id=session_row.id,
        )
        evidence_row = await evidence_repo.append(
            item,
            learner_row_id=learner_id,
            source_event_row_id=event_row.id,
            session_row_id=session_row.id,
            mastery_estimate_row_id=(
                mastery_estimate_id
                if item.kind in (EvidenceKind.RESPONSE, EvidenceKind.TRANSFER)
                else None
            ),
        )
        evidence_row_ids[item.evidence_id] = evidence_row.id

    misconception_belief_id: uuid.UUID | None = None
    if result.misconception_belief is not None:
        belief_contract = result.misconception_belief
        resolution_row_id = (
            evidence_row_ids.get(belief_contract.resolution_evidence_id)
            if belief_contract.resolution_evidence_id is not None
            else None
        )
        belief_row = await learning_state_repo.upsert_misconception_belief(
            learner_id=learner_id,
            misconception_id=misconception_id,
            belief=belief_contract,
            resolution_evidence_row_id=resolution_row_id,
        )
        misconception_belief_id = belief_row.id
        await learning_state_repo.append_teaching_episode(
            session_id=session_row.id,
            misconception_id=misconception_id,
            turns=result.context.teach_back_turns,
            resolved=result.context.misconception_resolved,
            resolution_turn=(
                result.context.teach_back_turns if result.context.misconception_resolved else None
            ),
        )

    if model_runs:
        await model_run_repo.record_many(model_runs, session_row_id=session_row.id)

    return PersistedThinThreadRun(
        session_id=session_row.id,
        learner_id=learner_id,
        skill_id=skill_id,
        mastery_estimate_id=mastery_estimate_id,
        misconception_belief_id=misconception_belief_id,
        evidence_row_ids=evidence_row_ids,
    )
