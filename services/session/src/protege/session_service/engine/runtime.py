"""The P10 orchestration engine: one HTTP request in, one authoritative
state transition (or none) out.

Design (see ``engine/__init__.py`` for the summary):

1. **Rehydrate.** A live ``SessionOrchestrator`` is reconstructed for every
   request from ``sessions.context_snapshot`` (``engine/context_codec.py``)
   -- the FSM's own transition table stays the sole authority
   (``packages/session-fsm``); this module never re-derives or guesses a
   transition, it only replays the orchestrator's own methods, exactly as
   ``protege.thin_thread.engine`` drives one in-process.
2. **Dispatch.** The incoming ``SessionEventRequest`` (the four polymorphic
   client event types) is only legal in specific FSM states; illegal
   combinations raise :class:`~..errors.IllegalSessionTransitionError` or
   :class:`~..errors.UnprocessableEventError` before anything is persisted.
3. **Synchronous app-logic cascade.** States the roadmap marks as
   synchronous/instantaneous (``SPROUT_SETUP``, ``MASTERY_DECISION``,
   ``REWARD``, ``SUMMARY``, ``RETRIEVAL_SCHEDULE`` -- see
   ``packages/session-fsm/src/protege/session/constants.py``'s per-state
   timeout table, all 5 s or less) are advanced through automatically
   within the same request, exactly as
   ``protege.thin_thread.engine.run_thin_thread`` advances them
   synchronously in one Python call -- this is what makes the P10 exit
   criterion ("Thin Thread replays entirely over HTTP with identical
   outcomes") true rather than merely similar.
4. **Persist.** Every transition the orchestrator's journal accumulated
   this request is flushed to ``session_states`` (the durable transition
   journal, unchanged from P9) in one pass at the end
   (:func:`_flush_journal`); evidence/mastery/misconception-belief writes
   go through the same P9 repositories P8's bridge already uses; nothing
   here is a second event store, a second ORM, or a second transition
   table.
5. **Checkpoint.** The orchestrator's final ``SessionContext`` is written
   back to ``context_snapshot`` so the next request (possibly a different
   process, after a restart) resumes from exactly where this one left off.

**One disclosed fidelity limit**, in the same spirit as
``persistence/thin_thread_bridge.py``'s own disclosed limits: ``evidence``
is append-only and each item is persisted as soon as it is submitted (so a
session's evidence survives even if the child never finishes), but the
authoritative ``mastery_estimates`` row does not exist until the transfer
item resolves the mastery decision -- so only the transfer item's own
``evidence.mastery_estimate_id`` can be set at insert time; the earlier
diagnostic/practice/verify evidence rows for the same session are left
unlinked (``NULL``). Backfilling them would require mutating already-
persisted evidence, which the append-only trigger correctly forbids.
``EvidenceRepository.resolve_claim`` (used by the proof/tutor-brief routes)
does not depend on this link -- it resolves a claim's evidence purely by
each item's own ``external_ref``, so the claim's evidence tree is complete
regardless.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import (
    AnswerSubmittedEvent,
    DiagnosisResult,
    DomainEvent,
    EventType,
    Evidence,
    EvidenceKind,
    Explanation,
    ExplanationGivenEvent,
    HintRequestedEvent,
    ManipulativeMovedEvent,
    MasteryEstimate,
    MisconceptionBelief,
    MisconceptionState,
    SessionEventRequest,
    SproutTurn,
)
from protege.contracts import (
    SessionState as S,
)
from protege.learning_engine import (
    ResponseObservation,
    TeachingEpisodeObservation,
    TransferObservationInput,
    bkt_update,
    build_response_evidence,
    build_teaching_episode_evidence,
    build_transfer_evidence,
    validate_answer,
)
from protege.llm.router import ModelRouter
from protege.roles.beliefs import apply_diagnosis_to_beliefs
from protege.roles.sprout import SproutGenerator
from protege.session.machine import Event, SessionContext
from protege.session.orchestrator import SessionOrchestrator
from protege.thin_thread.ids import IdAllocator
from protege.thin_thread.scenario import INITIAL_P_KNOWN, numeric_answer_text

from ..db.models import EvidenceRow, SessionRow, TurnRow
from ..errors import IllegalSessionTransitionError, UnprocessableEventError
from ..repositories.content import ContentRepository
from ..repositories.events import EventRepository
from ..repositories.evidence import EvidenceRepository
from ..repositories.learning_state import LearningStateRepository
from ..repositories.sessions import SessionRepository
from .content import (
    SESSION_BKT_PARAMS,
    get_content_pack,
    get_misconception,
    get_skill,
    get_thin_thread_items,
)
from .context_codec import context_from_dict, context_to_dict
from .ports import DiagnosticianPortAdapter, SproutPortAdapter

_ANSWERABLE_STATES = (S.DIAGNOSTIC, S.PRACTICE, S.INDEPENDENT_VERIFY, S.TRANSFER)


@dataclass(frozen=True)
class SessionView:
    session_id: uuid.UUID
    learner_id: uuid.UUID
    state: str
    started_at: datetime
    ended_at: datetime | None
    end_reason: str | None
    step: int


@dataclass(frozen=True)
class ItemPrompt:
    item_id: str
    stem: str


@dataclass(frozen=True)
class EventOutcome:
    session: SessionView
    next_item: ItemPrompt | None
    sprout_turn: SproutTurn | None
    diagnosis: DiagnosisResult | None
    hint_text: str | None
    misconception_resolved: bool
    mastery_verified: bool | None


def _json_value(value: object) -> object:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    raise TypeError(f"payload value {value!r} ({type(value).__name__}) is not JSON-compatible")


def _json_payload(payload: Mapping[str, object]) -> dict[str, object]:
    return {key: _json_value(value) for key, value in payload.items()}


async def _session_view(session: AsyncSession, session_row: SessionRow) -> SessionView:
    transitions = await SessionRepository(session).list_transitions(session_row.id)
    return SessionView(
        session_id=session_row.id,
        learner_id=session_row.learner_id,
        state=session_row.state,
        started_at=session_row.started_at,
        ended_at=session_row.ended_at,
        end_reason=session_row.end_reason,
        step=len(transitions),
    )


def next_item_prompt(context: SessionContext) -> ItemPrompt | None:
    items = get_thin_thread_items()
    if context.current == S.DIAGNOSTIC:
        item = items.diagnostic
    elif context.current == S.PRACTICE:
        item = items.practice
    elif context.current == S.INDEPENDENT_VERIFY:
        if context.verify_items_attempted >= len(items.verify):
            return None
        item = items.verify[context.verify_items_attempted]
    elif context.current == S.TRANSFER:
        item = items.transfer
    else:
        return None
    return ItemPrompt(item_id=item.item_id, stem=item.stem)


def _build_router_ports(
    router: ModelRouter, ids: IdAllocator
) -> tuple[SproutPortAdapter, DiagnosticianPortAdapter]:
    items = get_thin_thread_items()
    content = get_content_pack()
    generator = SproutGenerator(router, content=content)
    sprout = SproutPortAdapter(
        generator,
        item_stem=items.diagnostic.stem,
        correct_answer=items.diagnostic.correct_answer,
        ids=ids,
    )
    diagnostician = DiagnosticianPortAdapter(router, ids)
    return sprout, diagnostician


async def _flush_journal(
    session_repo: SessionRepository,
    session_row: SessionRow,
    orchestrator: SessionOrchestrator,
    existing_step_count: int,
) -> int:
    """Persist every transition ``orchestrator``'s journal accumulated this
    request. The orchestrator is reconstructed fresh per request (see
    module docstring point 1), so its journal *always* starts empty and
    holds only this request's own transitions -- ``existing_step_count``
    is not a slice index into it, only the running DB ``step`` counter
    (across every prior request for this session) each new record
    continues from."""
    step = existing_step_count
    for record in orchestrator.journal.records:
        step += 1
        await session_repo.append_transition(
            session_id=session_row.id,
            from_state=record.from_state,
            to_state=record.to_state,
            event=str(record.event),
            occurred_at=record.occurred_at,
            step=step,
        )
    return step


async def create_session(
    session: AsyncSession, *, learner_id: uuid.UUID, router: ModelRouter
) -> EventOutcome:
    """Create a session and drive it through the synchronous ARRIVAL ->
    SPROUT_TEASE -> DIAGNOSTIC preamble (roadmap: ARRIVAL is a synchronous
    profile load; SPROUT_TEASE's own 10 s timeout is documented "skip; no
    learning cost" -- neither state waits on the child)."""
    ids = IdAllocator()
    sprout, diagnostician = _build_router_ports(router, ids)
    context = SessionContext(p_known=INITIAL_P_KNOWN)
    orchestrator = SessionOrchestrator(sprout=sprout, diagnostician=diagnostician, context=context)

    session_repo = SessionRepository(session)
    event_repo = EventRepository(session)

    session_row = await session_repo.create_session(learner_id=learner_id, initial_state=S.ARRIVAL)

    orchestrator.advance(Event.PROFILE_LOADED)
    orchestrator.advance(Event.TEASE_ELAPSED)
    await _flush_journal(session_repo, session_row, orchestrator, 0)

    await event_repo.append(
        DomainEvent(
            id=f"evt_{uuid.uuid4().hex}",
            event_type=EventType.SESSION_STARTED,
            occurred_at=datetime.now(UTC),
            learner_id=str(learner_id),
            session_id=str(session_row.id),
        ),
        learner_row_id=learner_id,
        session_row_id=session_row.id,
    )

    await session_repo.save_context_snapshot(
        session_id=session_row.id, snapshot=context_to_dict(orchestrator.context)
    )

    view = await _session_view(session, session_row)
    return EventOutcome(
        session=view,
        next_item=next_item_prompt(orchestrator.context),
        sprout_turn=None,
        diagnosis=None,
        hint_text=None,
        misconception_resolved=False,
        mastery_verified=None,
    )


async def get_session_view(session: AsyncSession, session_row: SessionRow) -> SessionView:
    return await _session_view(session, session_row)


async def apply_event(
    session: AsyncSession,
    *,
    session_row: SessionRow,
    event: SessionEventRequest,
    router: ModelRouter,
) -> EventOutcome:
    if session_row.context_snapshot is None:
        raise IllegalSessionTransitionError("session has no recorded state yet")
    context = context_from_dict(session_row.context_snapshot)

    ids = IdAllocator()
    sprout, diagnostician = _build_router_ports(router, ids)
    orchestrator = SessionOrchestrator(sprout=sprout, diagnostician=diagnostician, context=context)

    session_repo = SessionRepository(session)
    event_repo = EventRepository(session)
    evidence_repo = EvidenceRepository(session)
    learning_state_repo = LearningStateRepository(session)
    content_repo = ContentRepository(session)

    existing_transitions = len(await session_repo.list_transitions(session_row.id))
    learner_id = session_row.learner_id
    items = get_thin_thread_items()
    misconception = get_misconception()
    skill = get_skill()

    sprout_turn: SproutTurn | None = None
    diagnosis: DiagnosisResult | None = None
    hint_text: str | None = None
    mastery_verified: bool | None = None

    async def _record_event(
        event_type: EventType, payload: dict[str, object] | None = None
    ) -> uuid.UUID:
        row = await event_repo.append(
            DomainEvent(
                id=f"evt_{uuid.uuid4().hex}",
                event_type=event_type,
                occurred_at=datetime.now(UTC),
                learner_id=str(learner_id),
                session_id=str(session_row.id),
                payload=_json_payload(payload or {}),
            ),
            learner_row_id=learner_id,
            session_row_id=session_row.id,
        )
        return row.id

    async def _record_evidence(
        evidence: Evidence,
        event_type: EventType,
        *,
        mastery_estimate_row_id: uuid.UUID | None = None,
    ) -> uuid.UUID:
        event_row_id = await _record_event(event_type, {"evidence_id": evidence.evidence_id})
        row = await evidence_repo.append(
            evidence,
            learner_row_id=learner_id,
            source_event_row_id=event_row_id,
            session_row_id=session_row.id,
            mastery_estimate_row_id=mastery_estimate_row_id,
        )
        return row.id

    if isinstance(event, AnswerSubmittedEvent):
        if context.current not in _ANSWERABLE_STATES:
            raise IllegalSessionTransitionError(
                f"no item is awaiting an answer in state {context.current}"
            )
        prompt = next_item_prompt(context)
        if prompt is None or prompt.item_id != event.item_id:
            raise UnprocessableEventError("item_id does not match the currently presented item")

        if context.current == S.DIAGNOSTIC:
            item = items.diagnostic
        elif context.current == S.PRACTICE:
            item = items.practice
        elif context.current == S.INDEPENDENT_VERIFY:
            item = items.verify[context.verify_items_attempted]
        else:
            item = items.transfer

        correct_text = numeric_answer_text(item.correct_answer)
        result = validate_answer(event.response_text, correct_text)
        correct = result.is_correct
        before_p_known = context.p_known
        context.p_known = bkt_update(before_p_known, correct=correct, params=SESSION_BKT_PARAMS)

        if context.current == S.TRANSFER:
            observation = TransferObservationInput(
                item_id=item.item_id,
                source_event_id=f"pending_{uuid.uuid4().hex}",
                representation=str(item.representation),
                result=correct,
            )
            built = build_transfer_evidence(observation)
            evidence = Evidence(
                id=f"e_{uuid.uuid4().hex}",
                kind=EvidenceKind.TRANSFER,
                source_event_id=built.source_event_id,
                weight=built.weight,
                payload=_json_payload(built.payload),
            )
            new_state = orchestrator.advance(Event.TRANSFER_ATTEMPTED)
            decision, new_state = orchestrator.compute_mastery_decision(
                p_known_before=INITIAL_P_KNOWN
            )
            mastery_verified = decision.mastery_verified

            mastery_estimate_row_id: uuid.UUID | None = None
            if decision.mastery_verified:
                skill_row = await content_repo.get_or_create_skill(skill)
                existing_evidence_count = (
                    await session.execute(
                        select(func.count())
                        .select_from(EvidenceRow)
                        .where(EvidenceRow.session_id == session_row.id)
                    )
                ).scalar_one()
                estimate = MasteryEstimate(
                    learner_id=str(learner_id),
                    skill_code=skill.code,
                    p_known=context.p_known,
                    evidence_count=existing_evidence_count + 1,
                    unaided_correct=context.verify_correct_count,
                    transfer_verified=correct,
                    model_version="p10-live-session",
                )
                mastery_row = await learning_state_repo.upsert_mastery(
                    learner_id=learner_id, skill_id=skill_row.id, estimate=estimate
                )
                mastery_estimate_row_id = mastery_row.id

            event_type = EventType.TRANSFER_PASSED if correct else EventType.TRANSFER_FAILED
            await _record_evidence(
                evidence, event_type, mastery_estimate_row_id=mastery_estimate_row_id
            )
            if decision.mastery_verified:
                await _record_event(EventType.MASTERY_VERIFIED, {"p_known": context.p_known})

            if orchestrator.context.current == S.REWARD:
                orchestrator.advance(Event.REWARD_PROCESSED)
                await _record_event(EventType.REWARD_GRANTED)
            orchestrator.advance(Event.ARTIFACTS_PERSISTED)
            orchestrator.advance(Event.SCHEDULE_COMPUTED)
        else:
            unaided = context.current == S.INDEPENDENT_VERIFY
            observation = ResponseObservation(
                item_id=item.item_id,
                source_event_id=f"pending_{uuid.uuid4().hex}",
                correct=correct,
                unaided=unaided,
            )
            built = build_response_evidence(observation)
            evidence = Evidence(
                id=f"e_{uuid.uuid4().hex}",
                kind=EvidenceKind.RESPONSE,
                source_event_id=built.source_event_id,
                weight=built.weight,
                payload=_json_payload(built.payload),
            )
            await _record_evidence(evidence, EventType.ANSWER_SUBMITTED)

            if context.current == S.DIAGNOSTIC:
                new_state = orchestrator.advance(Event.PRIORS_SET)
                if new_state == S.DISCOVERY:
                    # No discovery/guided-learning content authored for the
                    # thin-thread content pack -- the real, registered
                    # TIMEOUT exits (packages/session-fsm golden traces
                    # #17/#18) skip both, exactly as
                    # protege.thin_thread.engine does.
                    orchestrator.advance(Event.TIMEOUT)  # -> GUIDED_LEARNING
                    orchestrator.advance(Event.TIMEOUT)  # -> PRACTICE
            elif context.current == S.PRACTICE:
                exit_state = orchestrator.score_practice_item(correct=correct)
                if exit_state is None:
                    # Only one PRACTICE item is authored in the thin-thread
                    # content pack; the real "timeout: move on with partial
                    # evidence" path (also exercised by P8) advances anyway.
                    orchestrator.advance(Event.TIMEOUT)
            else:  # INDEPENDENT_VERIFY
                orchestrator.score_verify_item(correct=correct)

    elif isinstance(event, ExplanationGivenEvent):
        explanation: Explanation = event.explanation
        text_preview = explanation.text or explanation.modality
        await session_repo.append_turn(
            session_id=session_row.id,
            idx=await _next_turn_idx(session, session_row.id),
            speaker="child",
            modality=explanation.modality,
            content=text_preview,
        )

        if context.current == S.EXPLANATION:
            await _record_event(EventType.EXPLANATION_CREATED)
            new_state = orchestrator.advance(Event.EXPLANATION_CAPTURED)
            if new_state in (S.SPROUT_SETUP, S.SPROUT_SETUP_HARD):
                # Deterministic policy: the thin-thread content pack
                # authors exactly one misconception, so selecting it is not
                # a choice -- matches protege.thin_thread.engine's own
                # SPROUT_SETUP handling.
                orchestrator.advance(Event.MISCONCEPTION_SELECTED)
        elif context.current == S.TEACH_BACK:
            await _record_event(EventType.EXPLANATION_CREATED)
            skill_row = await content_repo.get_or_create_skill(skill)
            misconception_row = await content_repo.get_or_create_misconception(
                misconception, skill_id=skill_row.id
            )
            belief_row = await learning_state_repo.get_misconception_belief(
                learner_id, misconception_row.id
            )
            prior = belief_row.p_holds if belief_row is not None else misconception.prevalence_prior

            sprout_turn, diagnosis, new_state = orchestrator.run_teach_back_turn(
                misconception_code=misconception.code,
                explanation=explanation,
                misconception_set=[misconception],
            )
            sprout.record_child_turn(text_preview)

            updated_belief = apply_diagnosis_to_beliefs(
                diagnosis, misconception_set=[misconception], priors={misconception.code: prior}
            )
            new_p_holds = updated_belief[misconception.code]

            if context.misconception_resolved:
                await _record_event(EventType.MISCONCEPTION_RESOLVED)

            if new_state == S.REFLECTION:
                teaching_built = build_teaching_episode_evidence(
                    TeachingEpisodeObservation(
                        episode_id=f"te_{uuid.uuid4().hex}",
                        source_event_id=f"pending_{uuid.uuid4().hex}",
                        resolved=context.misconception_resolved,
                        resolution_turn=(
                            context.teach_back_turns if context.misconception_resolved else None
                        ),
                    )
                )
                teaching_evidence = Evidence(
                    id=f"e_{uuid.uuid4().hex}",
                    kind=EvidenceKind.TEACHING_EPISODE,
                    source_event_id=teaching_built.source_event_id,
                    weight=teaching_built.weight,
                    payload=_json_payload(teaching_built.payload),
                )
                teaching_evidence_row_id = await _record_evidence(
                    teaching_evidence, EventType.TEACH_BACK_COMPLETED
                )
                await learning_state_repo.upsert_misconception_belief(
                    learner_id=learner_id,
                    misconception_id=misconception_row.id,
                    belief=MisconceptionBelief(
                        learner_id=str(learner_id),
                        misconception_code=misconception.code,
                        p_holds=new_p_holds,
                        state=(
                            MisconceptionState.RESOLVED
                            if context.misconception_resolved
                            else MisconceptionState.UNRESOLVED
                        ),
                        resolution_evidence_id=(
                            teaching_evidence.evidence_id
                            if context.misconception_resolved
                            else None
                        ),
                    ),
                    resolution_evidence_row_id=(
                        teaching_evidence_row_id if context.misconception_resolved else None
                    ),
                )
                await learning_state_repo.append_teaching_episode(
                    session_id=session_row.id,
                    misconception_id=misconception_row.id,
                    turns=context.teach_back_turns,
                    resolved=context.misconception_resolved,
                    resolution_turn=(
                        context.teach_back_turns if context.misconception_resolved else None
                    ),
                )
            else:
                await learning_state_repo.upsert_misconception_belief(
                    learner_id=learner_id,
                    misconception_id=misconception_row.id,
                    belief=MisconceptionBelief(
                        learner_id=str(learner_id),
                        misconception_code=misconception.code,
                        p_holds=new_p_holds,
                        state=MisconceptionState.UNRESOLVED,
                    ),
                )
        elif context.current == S.REFLECTION:
            orchestrator.advance(Event.REFLECTION_CAPTURED)
        else:
            raise IllegalSessionTransitionError(
                f"no explanation is expected in state {context.current}"
            )

    elif isinstance(event, HintRequestedEvent):
        if context.current != S.COACH_ASSIST:
            raise IllegalSessionTransitionError("no hint is available in this state")
        content = get_content_pack()
        candidate = next(
            (i for i in content.interventions if i.misconception_code == misconception.code), None
        )
        hint_text = candidate.script if candidate is not None else None
        await _record_event(EventType.INTERVENTION_SELECTED, {"hint": hint_text or ""})
        await session_repo.append_turn(
            session_id=session_row.id,
            idx=await _next_turn_idx(session, session_row.id),
            speaker="system",
            modality="text",
            content=hint_text or "",
        )
        orchestrator.advance(Event.HINT_DELIVERED)

    elif isinstance(event, ManipulativeMovedEvent):
        if context.current in (S.COMPLETE, S.ABANDONED):
            raise IllegalSessionTransitionError("session has already ended")
        await session_repo.append_turn(
            session_id=session_row.id,
            idx=await _next_turn_idx(session, session_row.id),
            speaker="child",
            modality="manipulative",
            content=json.dumps(
                _json_payload({"trace": [action.model_dump(mode="json") for action in event.trace]})
            ),
        )
        # Recorded as evidence-grade interaction trace only (roadmap P13);
        # never itself an FSM transition trigger.

    else:  # pragma: no cover - exhaustive over SessionEventRequest's union
        raise UnprocessableEventError("unrecognised event type")

    await _flush_journal(session_repo, session_row, orchestrator, existing_transitions)
    await session_repo.save_context_snapshot(
        session_id=session_row.id, snapshot=context_to_dict(orchestrator.context)
    )

    view = await _session_view(session, session_row)
    return EventOutcome(
        session=view,
        next_item=next_item_prompt(orchestrator.context),
        sprout_turn=sprout_turn,
        diagnosis=diagnosis,
        hint_text=hint_text,
        misconception_resolved=orchestrator.context.misconception_resolved,
        mastery_verified=mastery_verified,
    )


async def _next_turn_idx(session: AsyncSession, session_id: uuid.UUID) -> int:
    count = (
        await session.execute(
            select(func.count()).select_from(TurnRow).where(TurnRow.session_id == session_id)
        )
    ).scalar_one()
    return int(count)


async def complete_session(session: AsyncSession, *, session_row: SessionRow) -> SessionView:
    """Finalize a session (roadmap P10: "complete only when the
    authoritative server state permits it"; architecture §23: "Emits
    SESSION_COMPLETED"). Idempotent: calling this again once the session is
    already ended returns the existing canonical state without emitting a
    second ``SESSION_COMPLETED`` event (on top of the ``Idempotency-Key``
    guard every ``POST`` already gets)."""
    if session_row.state != str(S.COMPLETE):
        raise IllegalSessionTransitionError(
            f"session cannot be completed from state {session_row.state}"
        )
    session_repo = SessionRepository(session)
    if session_row.ended_at is None:
        await session_repo.end_session(
            session_id=session_row.id, ended_at=datetime.now(UTC), end_reason="mastery_verified"
        )
        await EventRepository(session).append(
            DomainEvent(
                id=f"evt_{uuid.uuid4().hex}",
                event_type=EventType.SESSION_COMPLETED,
                occurred_at=datetime.now(UTC),
                learner_id=str(session_row.learner_id),
                session_id=str(session_row.id),
            ),
            learner_row_id=session_row.learner_id,
            session_row_id=session_row.id,
        )
        session_row = await session_repo.get(session_row.id) or session_row
    return await _session_view(session, session_row)
