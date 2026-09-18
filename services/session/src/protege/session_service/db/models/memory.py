"""§22 ``memory_items`` + ``embedding_records`` -- semantic memory storage
only (roadmap P22 implements retrieval; P9 provides schema + HNSW index and
nothing else). pgvector is storage/retrieval infrastructure ONLY: nothing in
this package ever reads ``embedding_records.embedding`` to move
``mastery_estimates`` or ``misconception_beliefs`` (§12, roadmap P9 rule 9).

``embedding``'s dimension is **configuration**, per docs/DECISIONS.md D2
(local ``bge-small``, 384-d) -- read once from ``Settings`` at import time,
matching ``migrations/env.py``'s own precedent of reading ``get_settings()``
for connection configuration. Neither this module nor the P9 migration
hardcodes 384 or 1536 as a literal; both read ``Settings.embedding_dimension``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ...settings import get_settings
from ..base import Base, created_at_column, uuid_pk

EMBEDDING_DIM = get_settings().embedding_dimension
"""D2: configuration-driven, never hardcoded. Seed value 384 (``bge-small``)."""


class MemoryItem(Base):
    """§22 ``memory_items``."""

    __tablename__ = "memory_items"

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
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id"), nullable=True
    )
    content: Mapped[str] = mapped_column(String, nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = created_at_column()


class EmbeddingRecord(Base):
    """§22 ``embedding_records``. HNSW index added by the P9 migration."""

    __tablename__ = "embedding_records"

    id: Mapped[uuid.UUID] = uuid_pk()
    memory_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("memory_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learners.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )
