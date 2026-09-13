"""Baseline: enable the pgvector extension.

P0 ships an intentionally empty schema — domain tables arrive with the P1
contracts and the P9 persistence schema. The extension is created here so the
database is pgvector-ready from the first `make dev`.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
