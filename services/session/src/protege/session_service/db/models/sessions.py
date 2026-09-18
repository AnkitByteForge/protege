"""§22 ``sessions``, ``session_states``, ``turns`` -- the FSM's persisted
journal (roadmap P7: "Journal in memory this phase; persisted in P9";
``protege.session.machine.TransitionRecord``'s docstring: "kept deliberately
as plain scalars ... so a later P9 mapping to that table is a straight field
copy"). The Python FSM (``packages/session-fsm``) remains the sole transition
authority -- this module only stores what already happened.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class SessionRow(Base):
    """§22 ``sessions``: session root."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = created_at_column()
    ended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    end_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)


class SessionStateRow(Base):
    """§22 ``session_states``: the transition log -- one row per FSM step,
    a straight copy of ``protege.session.machine.TransitionRecord``."""

    __tablename__ = "session_states"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    from_state: Mapped[str] = mapped_column(String(32), nullable=False)
    to_state: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("session_id", "step", name="uq_session_states_session_step"),
    )


class TurnRow(Base):
    """§22 ``turns``: every exchange."""

    __tablename__ = "turns"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[str] = mapped_column(String(16), nullable=False)
    modality: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    asr_confidence: Mapped[float | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (UniqueConstraint("session_id", "idx", name="uq_turns_session_idx"),)
