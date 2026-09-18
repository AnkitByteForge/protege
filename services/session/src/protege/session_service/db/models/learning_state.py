"""§22 ``mastery_estimates``, ``misconception_beliefs``, ``teaching_episodes``
-- the authoritative persisted learner state (roadmap P9: "``mastery_estimates``
and ``misconception_beliefs`` become authoritative persisted state").

``MisconceptionBeliefRow.resolution_evidence_id`` is a real foreign key to
``evidence.id``, but ``evidence`` itself references this table
(``misconception_belief_id``) -- a genuine mutual reference. The P9 migration
creates this table's FK to ``evidence`` as a deferred ``ALTER TABLE`` after
``evidence`` exists (see the migration module docstring) rather than dropping
the constraint to "repository convention only".
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class MasteryEstimateRow(Base):
    """§22 ``mastery_estimates``: authoritative per-skill mastery state."""

    __tablename__ = "mastery_estimates"

    id: Mapped[uuid.UUID] = uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id"), nullable=False, index=True
    )
    p_known: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    evidence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unaided_correct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    transfer_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        UniqueConstraint("learner_id", "skill_id", name="uq_mastery_estimates_learner_skill"),
        CheckConstraint("p_known BETWEEN 0 AND 1", name="p_known_between_0_and_1"),
    )


class MisconceptionBeliefRow(Base):
    """§22 ``misconception_beliefs``: per-learner Bernoulli bug state."""

    __tablename__ = "misconception_beliefs"

    id: Mapped[uuid.UUID] = uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    misconception_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("misconceptions.id"), nullable=False, index=True
    )
    p_holds: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="unresolved")
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # FK to evidence.id added by the migration after `evidence` is created
    # (mutual reference -- see module docstring).
    resolution_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "learner_id", "misconception_id", name="uq_misconception_beliefs_learner_misc"
        ),
        CheckConstraint("p_holds BETWEEN 0 AND 1", name="p_holds_between_0_and_1"),
    )


class TeachingEpisodeRow(Base):
    """§22 ``teaching_episodes``: teach-back record."""

    __tablename__ = "teaching_episodes"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    misconception_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("misconceptions.id"), nullable=False, index=True
    )
    turns: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolution_turn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
