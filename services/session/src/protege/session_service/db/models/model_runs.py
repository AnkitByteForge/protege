"""§22 ``model_runs``, extended per addendum §2.7/§9 point 9. Column shape
mirrors ``packages/llm/src/protege/llm/telemetry.py``'s ``ModelRunRecord``
field-for-field (that module's own docstring: "P9 owns the actual table and
migration; P4 produces records in this shape so the future persistence layer
has nothing to invent") -- see
``services/session/src/protege/session_service/persistence/model_run_sink.py``
for the bulk-write from a router's telemetry buffer into this table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, uuid_pk


class ModelRunRow(Base):
    """§22 ``model_runs``."""

    __tablename__ = "model_runs"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    endpoint_base_url: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(16), nullable=False)
    attempt_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fallback_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    structured_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    credits_estimated: Mapped[float] = mapped_column(Numeric(8, 3), nullable=False, default=0)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recorded_at: Mapped[datetime] = mapped_column(nullable=False)
