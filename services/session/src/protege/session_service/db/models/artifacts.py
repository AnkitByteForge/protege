"""§22 ``proof_artifacts``, ``tutor_briefings`` -- parent/tutor-facing outputs.
Schema only; P9 does not generate these (P20/P21)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class ProofArtifact(Base):
    """§22 ``proof_artifacts``."""

    __tablename__ = "proof_artifacts"

    id: Mapped[uuid.UUID] = uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    claims: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    evidence_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PGUUID(as_uuid=True)), nullable=False, default=list
    )
    pdf_s3_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = created_at_column()


class TutorBriefingRow(Base):
    """§22 ``tutor_briefings``."""

    __tablename__ = "tutor_briefings"

    id: Mapped[uuid.UUID] = uuid_pk()
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = created_at_column()
    viewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
