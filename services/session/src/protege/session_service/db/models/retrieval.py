"""§22 ``retrieval_schedule`` -- spacing (FSRS arrives in P23; schema only)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class RetrievalScheduleRow(Base):
    """§22 ``retrieval_schedule``."""

    __tablename__ = "retrieval_schedule"

    id: Mapped[uuid.UUID] = uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id"), nullable=False
    )
    due_at: Mapped[datetime] = mapped_column(nullable=False)
    interval_days: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stability: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    difficulty: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
