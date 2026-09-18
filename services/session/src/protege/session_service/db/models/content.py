"""§22 content/domain tables: ``skills``, ``skill_prereq``, ``misconceptions``,
``learning_items``, ``item_versions``. Schema only -- P9 does not implement
content authoring (that is P3/``tools/authoring``, which remains file-based).
These tables exist so ``mastery_estimates``, ``misconceptions``, and
``evidence`` have real foreign-key targets, and so a future content-loading
job can populate them without a schema change.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk


class Skill(Base):
    """§22 ``skills``: graph node."""

    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    grade_band: Mapped[str] = mapped_column(String(16), nullable=False)
    standard: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = created_at_column()


class SkillPrereq(Base):
    """§22 ``skill_prereq``: directed skill-graph edges."""

    __tablename__ = "skill_prereq"

    skill_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    prereq_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )


class Misconception(Base):
    """§22 ``misconceptions``: the moat."""

    __tablename__ = "misconceptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    cognitive_origin: Mapped[str] = mapped_column(String(256), nullable=False)
    distractor_likelihood: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    distractor_likelihood_if_not_misconception: Mapped[dict[str, float] | None] = mapped_column(
        JSONB, nullable=True
    )
    prevalence_prior: Mapped[float] = mapped_column(Numeric(4, 3), nullable=False, default=0.200)
    citation: Mapped[str | None] = mapped_column(String, nullable=True)
    content_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = created_at_column()


class LearningItem(Base):
    """§22 ``learning_items``."""

    __tablename__ = "learning_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    item_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    skill_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("skills.id"), nullable=True, index=True
    )
    stem: Mapped[str] = mapped_column(String, nullable=False)
    representation: Mapped[str] = mapped_column(String(32), nullable=False)
    correct_answer: Mapped[str] = mapped_column(String, nullable=False)
    distractors: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="practice")
    content_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = ({"comment": "index (skill_id, elo) added in the P9 migration DDL"},)


class ItemVersion(Base):
    """§22 ``item_versions``: immutable content snapshot. Never mutated --
    rollback is flipping the ``content_version`` pointer elsewhere."""

    __tablename__ = "item_versions"

    id: Mapped[uuid.UUID] = uuid_pk()
    learning_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("learning_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content_version: Mapped[str] = mapped_column(String(32), nullable=False)
    stem: Mapped[str] = mapped_column(String, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String, nullable=False)
    distractors: Mapped[list[object]] = mapped_column(JSONB, nullable=False, default=list)
    elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    representation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = created_at_column()
