"""Session aggregate: ``sessions``, ``session_states``, ``turns``.

``append_transition`` takes a ``protege.session.machine.TransitionRecord``
directly -- that dataclass's own docstring: "kept deliberately as plain
scalars ... so a later P9 mapping to that table is a straight field copy."
This repository performs exactly that copy and nothing else; the Python FSM
(``packages/session-fsm``) remains the sole transition authority (roadmap
rule 2) -- no guard, no transition table, no state-machine logic lives here.

``rehydrate`` reconstructs a :class:`RehydratedSession` from the persisted
journal: the current state (the last ``to_state``, or the session's own
``state`` column if no transitions were recorded) and the ordered
``state_sequence`` a golden-trace-style comparison expects
(``Journal.state_sequence``'s own shape: ``(start, *every to_state)``).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import SessionState

from ..db.models import SessionRow, SessionStateRow, TurnRow


@dataclass(frozen=True)
class RehydratedSession:
    session_id: uuid.UUID
    learner_id: uuid.UUID
    current_state: SessionState
    state_sequence: tuple[SessionState, ...]
    started_at: datetime
    ended_at: datetime | None
    end_reason: str | None


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self, *, learner_id: uuid.UUID, initial_state: SessionState = SessionState.ARRIVAL
    ) -> SessionRow:
        row = SessionRow(learner_id=learner_id, state=str(initial_state))
        self._session.add(row)
        await self._session.flush()
        return row

    async def append_transition(
        self,
        *,
        session_id: uuid.UUID,
        from_state: SessionState,
        to_state: SessionState,
        event: str,
        occurred_at: datetime,
        step: int,
    ) -> SessionStateRow:
        """Persist one FSM step. ``step`` is the 1-indexed ordinal within
        this session's journal -- the caller (the P8 bridge, or a future
        P10 service) supplies it so ordering survives even if transitions
        are persisted out of strict insertion order (e.g. a retried write)."""
        row = SessionStateRow(
            session_id=session_id,
            from_state=str(from_state),
            to_state=str(to_state),
            trigger=event,
            step=step,
            at=occurred_at,
        )
        self._session.add(row)
        session_row = await self._session.get(SessionRow, session_id)
        if session_row is not None:
            session_row.state = str(to_state)
        await self._session.flush()
        return row

    async def append_turn(
        self,
        *,
        session_id: uuid.UUID,
        idx: int,
        speaker: str,
        modality: str,
        content: str,
        asr_confidence: float | None = None,
        latency_ms: int | None = None,
    ) -> TurnRow:
        row = TurnRow(
            session_id=session_id,
            idx=idx,
            speaker=speaker,
            modality=modality,
            content=content,
            asr_confidence=asr_confidence,
            latency_ms=latency_ms,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def end_session(
        self, *, session_id: uuid.UUID, ended_at: datetime, end_reason: str
    ) -> None:
        session_row = await self._session.get(SessionRow, session_id)
        if session_row is not None:
            session_row.ended_at = ended_at
            session_row.end_reason = end_reason
        await self._session.flush()

    async def get(self, session_id: uuid.UUID) -> SessionRow | None:
        return await self._session.get(SessionRow, session_id)

    async def list_transitions(self, session_id: uuid.UUID) -> list[SessionStateRow]:
        result = await self._session.execute(
            select(SessionStateRow)
            .where(SessionStateRow.session_id == session_id)
            .order_by(SessionStateRow.step)
        )
        return list(result.scalars().all())

    async def rehydrate(self, session_id: uuid.UUID) -> RehydratedSession:
        session_row = await self._session.get(SessionRow, session_id)
        if session_row is None:
            raise LookupError(f"no session {session_id}")
        transitions = await self.list_transitions(session_id)
        if transitions:
            sequence = (
                SessionState(transitions[0].from_state),
                *(SessionState(t.to_state) for t in transitions),
            )
            current = sequence[-1]
        else:
            sequence = (SessionState(session_row.state),)
            current = SessionState(session_row.state)
        return RehydratedSession(
            session_id=session_row.id,
            learner_id=session_row.learner_id,
            current_state=current,
            state_sequence=sequence,
            started_at=session_row.started_at,
            ended_at=session_row.ended_at,
            end_reason=session_row.end_reason,
        )
