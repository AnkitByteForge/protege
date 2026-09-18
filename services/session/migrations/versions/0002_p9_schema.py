"""P9: persistence, evidence ledger, events & jobs.

Implements the full ARCHITECTURE.md §22 database register (all tables named
in the table register, including ``proof_artifacts``/``tutor_briefings``/
``safety_events``/``audit_events``/``retrieval_schedule``, which P10+ does
not yet consume but the P9 roadmap contract requires schema for), plus
§24's ``events`` log and the roadmap P9 ``jobs`` table.

Every table is created directly from
``protege.session_service.db.models.Base.metadata`` -- the ORM models are
the single source of the schema; this migration does not duplicate column
definitions, it sequences their creation in dependency order and adds the
handful of things that are not expressible as plain ``Table`` metadata:

- the append-only enforcement trigger (``forbid_update_delete()``) on
  ``events``, ``evidence``, ``safety_events``;
- the pgvector HNSW index on ``embedding_records.embedding``;
- the one deferred foreign key, ``misconception_beliefs.resolution_evidence_id
  -> evidence.id``, added by ``ALTER TABLE`` after ``evidence`` exists,
  because ``evidence`` itself references ``misconception_beliefs``
  (``misconception_belief_id``) -- a genuine mutual reference between the
  two tables that no single linear ``CREATE TABLE`` order can express.

``embedding_records.embedding``'s dimension is read from
``protege.session_service.db.models.memory.EMBEDDING_DIM``, itself sourced
from ``Settings.embedding_dimension`` (docs/DECISIONS.md D2) -- never a
literal 384/1536 in this file.
"""

from collections.abc import Sequence

from alembic import op

from protege.session_service.db.append_only import (
    APPEND_ONLY_TABLES,
    CREATE_FORBID_UPDATE_DELETE_FUNCTION,
    DROP_FORBID_UPDATE_DELETE_FUNCTION,
    append_only_trigger_ddl,
    drop_append_only_trigger_ddl,
)
from protege.session_service.db.models import Base

revision: str = "0002_p9_schema"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Dependency order: every table's foreign keys reference only a table
# already created earlier in this sequence (verified by inspection; see the
# module docstring for the one exception, handled as a deferred ALTER).
TABLE_ORDER: tuple[str, ...] = (
    "parents",
    "learners",
    "skills",
    "skill_prereq",
    "misconceptions",
    "learning_items",
    "item_versions",
    "sessions",
    "session_states",
    "turns",
    "model_runs",
    "events",
    "responses",
    "explanations",
    "diagnoses",
    "mastery_estimates",
    "misconception_beliefs",
    "teaching_episodes",
    "evidence",
    "policy_decisions",
    "retrieval_schedule",
    "memory_items",
    "embedding_records",
    "proof_artifacts",
    "tutor_briefings",
    "safety_events",
    "audit_events",
    "jobs",
)


def upgrade() -> None:
    bind = op.get_bind()

    for table_name in TABLE_ORDER:
        Base.metadata.tables[table_name].create(bind, checkfirst=False)

    op.create_foreign_key(
        "fk_misconception_beliefs_resolution_evidence_id_evidence",
        "misconception_beliefs",
        "evidence",
        ["resolution_evidence_id"],
        ["id"],
    )

    op.create_index(
        "ix_embedding_records_embedding_hnsw",
        "embedding_records",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.execute(CREATE_FORBID_UPDATE_DELETE_FUNCTION)
    for table_name in APPEND_ONLY_TABLES:
        op.execute(append_only_trigger_ddl(table_name))


def downgrade() -> None:
    for table_name in APPEND_ONLY_TABLES:
        op.execute(drop_append_only_trigger_ddl(table_name))
    op.execute(DROP_FORBID_UPDATE_DELETE_FUNCTION)

    op.drop_constraint(
        "fk_misconception_beliefs_resolution_evidence_id_evidence",
        "misconception_beliefs",
        type_="foreignkey",
    )

    bind = op.get_bind()
    for table_name in reversed(TABLE_ORDER):
        Base.metadata.tables[table_name].drop(bind, checkfirst=False)
