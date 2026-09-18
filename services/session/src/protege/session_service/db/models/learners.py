"""``parents`` / ``learners`` (ARCHITECTURE.md §22 table register).

Deliberately no ORM ``relationship()`` graph anywhere in ``db/models`` --
every cross-table read goes through an explicit repository query
(``select()`` + an explicit join where needed). This keeps async-session
behaviour predictable (no surprise lazy-load I/O) and keeps "what a
repository actually queries" visible at the call site rather than hidden
behind attribute access, matching AGENTS.md's "no business decisions in
repositories" by making the repository the only place a join is decided.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class Parent(Base):
    """§22 ``parents``: account + consent."""

    __tablename__ = "parents"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    consent_version: Mapped[str] = mapped_column(String(32), nullable=False)
    consent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # server_default (not just the ORM-level `default=`) matches the §22
    # table register's own wording, "training_optin=false", as a real
    # database default -- any writer, not only this ORM, gets the safe
    # (opted-out) default.
    training_optin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = created_at_column()


class Learner(Base):
    """§22 ``learners``: child profile. Only first-name display, grade
    band, and birth year -- no further PII (§22 table register)."""

    __tablename__ = "learners"

    id: Mapped[uuid.UUID] = uuid_pk()
    parent_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("parents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    grade_band: Mapped[str] = mapped_column(String(16), nullable=False)
    dob_year: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = created_at_column()
