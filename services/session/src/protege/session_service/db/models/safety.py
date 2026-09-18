"""§22 ``safety_events`` (append-only, 36 mo), ``audit_events``."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, uuid_pk


class SafetyEventRow(Base):
    """§22 ``safety_events``. Append-only -- the P9 migration installs the
    same ``forbid_update_delete()`` trigger it installs on ``evidence`` and
    ``events`` (roadmap: "Where the roadmap defines evidence and safety
    events as append-only, enforce that property at the persistence
    boundary")."""

    __tablename__ = "safety_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    # SET NULL, not CASCADE: 36-month retention (§22 table register) is a
    # roadmap retention/audit exception -- a safety incident record must
    # outlive the account it was raised against, for the same reason
    # ``events`` is SET NULL (see that model's docstring).
    learner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    raw_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(256), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    at: Mapped[datetime] = mapped_column(nullable=False)


class AuditEventRow(Base):
    """§22 ``audit_events``: access log."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    at: Mapped[datetime] = mapped_column(nullable=False)
