"""§24 ``events`` -- the domain event log (append-only facts; the RL training
substrate and the audit trail). ``external_ref`` preserves whatever opaque
event id a pre-persistence caller used (e.g. P8's in-memory
``IdAllocator``-minted ``evt_001`` strings) -- P9 assigns the real ``id``
(``packages/contracts/src/protege/contracts/ids.py``: "opaque IDs are
deliberately loose because the persistence layer (P9) assigns UUIDs while
documents and events use prefixed strings").

Append-only is enforced at the database boundary (see the P9 migration's
``forbid_update_delete()`` trigger) -- queue/event-bus semantics stay
conceptually separate from ``jobs`` even though both live in Postgres
(roadmap P9 rule).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, uuid_pk


class EventRow(Base):
    """§24 ``events`` envelope, persisted."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = uuid_pk()
    external_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    """Mirrors ``EvidenceRow.external_ref``: scoped unique per learner, not
    globally, for the same reason (a pre-persistence id minter like P8's
    ``IdAllocator`` restarts its counter every run) -- see that column's
    docstring."""
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1.0")
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    # SET NULL, not CASCADE: the event log is the RL training substrate and
    # audit trail (module docstring) -- a roadmap retention/audit exception
    # to "learner deletion cascades everywhere" (roadmap P9: "Respect any
    # roadmap retention/audit exceptions instead of blindly cascading every
    # table"). Deleting a learner un-links their events rather than erasing
    # the fact that something happened; `evidence.source_event_id` still
    # resolves (evidence itself IS cascade-deleted with the learner, so no
    # evidence row survives to dangle on a since-anonymized event).
    learner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("learner_id", "external_ref", name="uq_events_learner_external_ref"),
    )
