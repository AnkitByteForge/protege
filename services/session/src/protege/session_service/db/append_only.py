"""Database-level append-only enforcement (roadmap P9: "Do not weaken this to
'repository convention only' if database-level enforcement is practical").

One trigger function, installed once by the P9 migration, attached to every
table the roadmap marks append-only: ``events``, ``evidence``,
``safety_events``. ``TG_OP = 'DELETE'`` and ``TG_OP = 'UPDATE'`` both raise;
``INSERT`` is untouched.

**The one sanctioned exception.** Postgres implements ``ON DELETE CASCADE``
and ``ON DELETE SET NULL`` as, respectively, an internal ``DELETE``/``UPDATE``
against the referencing row -- the exact operations this trigger exists to
block. Learner deletion legitimately needs both: ``evidence.learner_id`` is
``CASCADE`` (roadmap: "Learner deletion must not leave orphaned ... evidence
where owned by the learner"), and ``events``/``safety_events``'s
``learner_id``/``session_id`` are ``SET NULL`` (the retention/audit
exception documented on those models). Rather than weakening the trigger to
allow all UPDATE/DELETE (which would defeat the point), it checks one
transaction-local flag, ``protege.allow_cascade_write``, that only
``LearnerRepository.delete`` sets (via ``SET LOCAL``, so it is scoped to
that one transaction and never leaks to any other caller). Any UPDATE/DELETE
against these tables outside that one sanctioned transaction is still
blocked -- proven by ``tests/test_append_only.py``, which never sets the flag.
"""

from __future__ import annotations

CREATE_FORBID_UPDATE_DELETE_FUNCTION = """
CREATE OR REPLACE FUNCTION forbid_update_delete() RETURNS trigger AS $$
BEGIN
    IF current_setting('protege.allow_cascade_write', true) = 'on' THEN
        RETURN COALESCE(NEW, OLD);
    END IF;
    RAISE EXCEPTION
        '% is append-only: % is not permitted on table %',
        TG_TABLE_NAME, TG_OP, TG_TABLE_NAME
        USING ERRCODE = 'restrict_violation';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

DROP_FORBID_UPDATE_DELETE_FUNCTION = "DROP FUNCTION IF EXISTS forbid_update_delete() CASCADE;"

ALLOW_CASCADE_WRITE_GUC = "protege.allow_cascade_write"


def append_only_trigger_ddl(table_name: str) -> str:
    """DDL installing the append-only trigger on ``table_name``."""
    return (
        f"CREATE TRIGGER {table_name}_append_only "
        f"BEFORE UPDATE OR DELETE ON {table_name} "
        f"FOR EACH ROW EXECUTE FUNCTION forbid_update_delete();"
    )


def drop_append_only_trigger_ddl(table_name: str) -> str:
    return f"DROP TRIGGER IF EXISTS {table_name}_append_only ON {table_name};"


APPEND_ONLY_TABLES: tuple[str, ...] = ("events", "evidence", "safety_events")
"""Tables the roadmap explicitly requires append-only enforcement for:
evidence and safety events by name, plus ``events`` (the domain event log
is append-only by definition, roadmap P9 "Implement the roadmap event log as
an append-only facts table")."""
