"""``jobs`` -- work items, not the event bus (roadmap P9 rule 6). One
consumer, must complete; claiming uses ``SELECT ... FOR UPDATE SKIP LOCKED``
(``jobs/worker.py``), never row-level polling that could double-claim.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk

JOB_STATUSES = ("queued", "running", "succeeded", "failed")


class JobRow(Base):
    """One work item. ``available_at`` gates both initial visibility and
    retry backoff -- a claim query only ever selects rows with
    ``status='queued' AND available_at <= now()``."""

    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    job_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued", index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    error: Mapped[str | None] = mapped_column(String, nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)
    available_at: Mapped[datetime] = created_at_column()
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        CheckConstraint(f"status IN {JOB_STATUSES!r}", name="status_in_job_statuses"),
    )
