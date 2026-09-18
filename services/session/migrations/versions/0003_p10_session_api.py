"""P10: session API support -- Clerk identity mapping, FSM context
checkpoint, and idempotency ledger.

Three additive changes, each minimal (roadmap P10 instruction: "Do not add
schema just for convenience; add the minimum persistent identity mapping
required by the authoritative P10 contract"):

1. ``parents.clerk_user_id`` -- the one persistent identity mapping P10's
   auth model actually needs: a verified Clerk JWT's ``sub`` claim proves
   *who* the caller is; this column is what lets the API resolve that
   caller to *their own* ``parents`` row for ownership checks
   (``LearnerRepository``/``SessionRepository`` already scope every query
   by ``learner_id``/``parent_id`` -- this column is the missing link from
   "a verified Clerk identity" to "one of those rows"). Nullable and
   uniquely indexed: a ``parents`` row can pre-date Clerk linkage (the
   existing ``get_or_create`` test/demo convenience path), but two parents
   can never share one Clerk identity.

2. ``sessions.context_snapshot`` -- a JSONB checkpoint of
   ``protege.session.machine.SessionContext`` (roadmap P7: "in-memory
   session context"). The FSM's transition table
   (``packages/session-fsm``) is deliberately pure/in-process and holds no
   persistence of its own (P7 Data field: "Journal in memory this phase;
   persisted in P9") -- P10 is the first caller that must *resume* a live
   orchestrator across separate HTTP requests, which a stateless API
   process cannot do purely in memory. This column is not a second source
   of truth for FSM transitions (``session_states`` remains the durable,
   append-only transition journal / audit trail, unchanged) -- it is a
   checkpoint of the same dataclass's own fields, written transactionally
   alongside each transition, so a request can reconstruct the exact
   ``SessionContext`` the orchestrator had after its last step. Nullable
   only until a session's first transition is persisted.

3. ``idempotency_keys`` -- the roadmap's ``Idempotency-Key`` ledger
   ("24 h dedupe ... Postgres at this scale"). Scoped by
   ``(actor_subject, method, path, idempotency_key)`` so the same key reused
   by a different actor, endpoint, or resource path is a distinct entry
   (roadmap: "same authenticated actor + same endpoint/resource + same key
   must not cause duplicate state transitions"); ``request_hash`` lets a
   replay with a *different* body under the same key be rejected rather
   than silently served the wrong cached response. Rows are never updated in
   place after ``response_status`` is set (a request either finds a
   completed row and returns it, or inserts a fresh one inside the same
   transaction as the work it is guarding -- see
   ``repositories/idempotency.py``), so no append-only trigger is needed
   here the way ``events``/``evidence`` need one.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_p10_session_api"
down_revision: str | None = "0002_p9_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADD_CLERK_USER_ID = """
ALTER TABLE parents ADD COLUMN clerk_user_id VARCHAR(128);
CREATE UNIQUE INDEX uq_parents_clerk_user_id ON parents (clerk_user_id)
    WHERE clerk_user_id IS NOT NULL;
"""

_DROP_CLERK_USER_ID = """
DROP INDEX IF EXISTS uq_parents_clerk_user_id;
ALTER TABLE parents DROP COLUMN IF EXISTS clerk_user_id;
"""

_ADD_CONTEXT_SNAPSHOT = """
ALTER TABLE sessions ADD COLUMN context_snapshot JSONB;
"""

_DROP_CONTEXT_SNAPSHOT = """
ALTER TABLE sessions DROP COLUMN IF EXISTS context_snapshot;
"""

_CREATE_IDEMPOTENCY_KEYS = """
CREATE TABLE idempotency_keys (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    actor_subject VARCHAR(255) NOT NULL,
    http_method VARCHAR(8) NOT NULL,
    request_path VARCHAR(512) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    request_hash VARCHAR(64) NOT NULL,
    response_status INTEGER,
    response_body JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_idempotency_keys PRIMARY KEY (id),
    CONSTRAINT uq_idempotency_keys_actor_method_path_key
        UNIQUE (actor_subject, http_method, request_path, idempotency_key)
);
CREATE INDEX ix_idempotency_keys_expires_at ON idempotency_keys (expires_at);
"""

_DROP_IDEMPOTENCY_KEYS = "DROP TABLE IF EXISTS idempotency_keys CASCADE;"


def _execute_statements(sql: str) -> None:
    """See ``0002_p9_schema``'s identical helper: asyncpg's prepared-
    statement protocol refuses more than one SQL command per ``execute()``
    call, so each ``;``-terminated statement here is sent separately. Safe
    to split naively on ``;``: pure, literal DDL, no string/JSON literals
    containing a semicolon."""
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            op.execute(statement)


def upgrade() -> None:
    _execute_statements(_ADD_CLERK_USER_ID)
    _execute_statements(_ADD_CONTEXT_SNAPSHOT)
    _execute_statements(_CREATE_IDEMPOTENCY_KEYS)


def downgrade() -> None:
    _execute_statements(_DROP_IDEMPOTENCY_KEYS)
    _execute_statements(_DROP_CONTEXT_SNAPSHOT)
    _execute_statements(_DROP_CLERK_USER_ID)
