"""``idempotency_keys`` (roadmap P10: "``Idempotency-Key`` with 24 h dedupe
-- Postgres at this scale"). See the P10 migration's module docstring for
the scoping rationale.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class IdempotencyKeyRow(Base):
    """One ``Idempotency-Key`` ledger entry, scoped to the actor, endpoint,
    and resource path that produced it."""

    __tablename__ = "idempotency_keys"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    http_method: Mapped[str] = mapped_column(String(8), nullable=False)
    request_path: Mapped[str] = mapped_column(String(512), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = created_at_column()
    expires_at: Mapped[datetime] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "actor_subject",
            "http_method",
            "request_path",
            "idempotency_key",
            name="uq_idempotency_keys_actor_method_path_key",
        ),
    )
