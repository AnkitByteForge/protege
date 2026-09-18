"""Declarative base for the P9 persistence schema (roadmap P9; ARCHITECTURE.md
§22). One ``Base`` for every ORM model under ``db/models/`` so Alembic's
autogenerate (not used for the hand-written P9 migration, but kept correct
for any future migration) and ``target_metadata`` have a single source.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy.orm import Mapped as Mapped  # re-exported for model modules

# Deterministic constraint/index naming so Alembic-generated DDL (and the
# hand-written P9 migration, which mirrors this convention) never collides
# with an unnamed auto-generated constraint.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Every P9 table maps to a subclass of this base.

    ``type_annotation_map`` maps every bare ``Mapped[datetime]`` (and
    ``Mapped[datetime | None]``) column to ``timestamptz`` (``DateTime
    (timezone=True)``) by default -- every §22 table's timestamp columns are
    ``timestamptz`` (the abridged DDL's own ``created_at timestamptz NOT
    NULL DEFAULT now()``), and every value this application ever writes is
    an explicit UTC-aware ``datetime.now(UTC)``. Without this, a plain
    ``Mapped[datetime]`` defaults to ``TIMESTAMP WITHOUT TIME ZONE``, which
    asyncpg then rejects outright when handed a tz-aware value
    ("can't subtract offset-naive and offset-aware datetimes") -- a real
    schema-correctness bug, not just a test artifact.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[type, object]] = {datetime: DateTime(timezone=True)}


def uuid_pk() -> Mapped[uuid.UUID]:
    """A ``uuid primary key default gen_random_uuid()`` column (§22 convention:
    every table register row uses a ``uuid PRIMARY KEY DEFAULT
    gen_random_uuid()``). A function, not a shared column object, because
    SQLAlchemy ``Column``/``mapped_column`` instances are not shareable
    across tables.
    """
    from sqlalchemy.dialects.postgresql import UUID as PGUUID
    from sqlalchemy.sql import func

    return mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


def created_at_column() -> Mapped[datetime]:
    """A ``timestamptz NOT NULL DEFAULT now()`` column, matching every §22
    table's ``created_at``/``computed_at`` convention."""
    from sqlalchemy import DateTime
    from sqlalchemy.sql import func

    return mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
