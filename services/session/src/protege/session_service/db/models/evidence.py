"""§22 ``evidence`` -- provenance atoms (append-only; §17 provenance chain).

Extends the architecture's abridged DDL (``mastery_estimate_id``,
``source_event_id``, ``weight``, ``payload``) with the fields the P9 roadmap
contract explicitly requires beyond that abridgement: "relevant
learner/session/turn association" and a real ``misconception_belief_id`` link
(a ``TEACHING_EPISODE``-kind row backs a misconception belief, not a mastery
estimate). ``source_event_id`` is a real foreign key to ``events.id`` --
resolving a claim to "source event -> originating session/turn" (the roadmap's
exact claim-resolution path) is a plain join, not a string-matching lookup.

Append-only is enforced at the database boundary, not just by repository
convention (roadmap: "database-level enforcement ... if practical") -- see
the ``forbid_update_delete()`` trigger installed by the P9 migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class EvidenceRow(Base):
    """§22 ``evidence``."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    external_ref: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    """The opaque ``EvidenceId`` a pre-persistence caller minted (e.g. P8's
    ``IdAllocator``-produced ``e_001``) -- mirrors ``EventRow.external_ref``.
    A ``ProofClaim``/``MasteryOutcome.evidence_ids`` list carries these
    opaque strings; claim resolution looks them up here rather than
    requiring the caller to already know each row's real UUID."""
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    turn_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("turns.id", ondelete="SET NULL"), nullable=True
    )
    mastery_estimate_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("mastery_estimates.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    misconception_belief_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("misconception_beliefs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    source_event_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True
    )
    weight: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=1.00)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (CheckConstraint("weight BETWEEN 0 AND 3", name="weight_between_0_and_3"),)
