"""P9: persistence, evidence ledger, events & jobs.

Implements the full ARCHITECTURE.md §22 database register (all tables named
in the table register, including ``proof_artifacts``/``tutor_briefings``/
``safety_events``/``audit_events``/``retrieval_schedule``, which P10+ does
not yet consume but the P9 roadmap contract requires schema for), plus
§24's ``events`` log and the roadmap P9 ``jobs`` table.

**This migration is fully self-contained.** Every ``CREATE TABLE`` statement
below is frozen, literal SQL -- generated once, at development time, from
``protege.session_service.db.models.Base.metadata`` (a legitimate,
audit-sanctioned way to *author* a migration), then embedded verbatim here.
Applying this migration does **not** import or read ``Base.metadata`` at
runtime, and never will, regardless of how the ORM models change in a later
commit: a given revision id must always produce the exact same schema it
produced the day it was written, which a live reference to
``Base.metadata.tables[...]`` cannot guarantee (a later, unrelated model
edit would silently change what an *already-applied* revision id means if
it re-derived DDL from current metadata at every apply). Regenerate this
file's literal SQL deliberately (and bump the revision) if the schema needs
to change -- never edit the ORM models and expect this file to follow.

The one deliberate exception is ``embedding_records.embedding``'s vector
dimension, which docs/DECISIONS.md D2 requires to be read from
``Settings.embedding_dimension`` **by the migration itself** at apply time
(D2, verbatim: "consumed by the embedding worker and by the migration that
creates the pgvector column") -- a single scalar application-configuration
value, not a re-derivation of table structure from ORM metadata.

Non-literal additions, for the same reasons the original version of this
migration already used raw DDL for them (none of these are expressible as
plain ``CREATE TABLE`` statements):

- the append-only enforcement trigger (``forbid_update_delete()``) on
  ``events``, ``evidence``, ``safety_events``;
- the pgvector HNSW index on ``embedding_records.embedding``;
- the one deferred foreign key, ``misconception_beliefs.resolution_evidence_id
  -> evidence.id``, added by ``ALTER TABLE`` after ``evidence`` exists,
  because ``evidence`` itself references ``misconception_beliefs``
  (``misconception_belief_id``) -- a genuine mutual reference between the
  two tables that no single linear ``CREATE TABLE`` order can express.
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
from protege.session_service.settings import get_settings

revision: str = "0002_p9_schema"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Dependency order: every table's foreign keys reference only a table
# already created earlier in this sequence (verified by inspection; see the
# module docstring for the one exception, handled as a deferred ALTER). Also
# the order ``downgrade()`` drops tables in reverse.
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

_CREATE_PARENTS = """
CREATE TABLE parents (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    email VARCHAR(320) NOT NULL,
    consent_version VARCHAR(32) NOT NULL,
    consent_at TIMESTAMP WITH TIME ZONE,
    training_optin BOOLEAN DEFAULT 'false' NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_parents PRIMARY KEY (id),
    CONSTRAINT uq_parents_email UNIQUE (email)
);
"""

_CREATE_LEARNERS = """
CREATE TABLE learners (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    parent_id UUID NOT NULL,
    display_name VARCHAR(80) NOT NULL,
    grade_band VARCHAR(16) NOT NULL,
    dob_year INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_learners PRIMARY KEY (id),
    CONSTRAINT fk_learners_parent_id_parents FOREIGN KEY(parent_id) REFERENCES parents (id) ON DELETE CASCADE
);
CREATE INDEX ix_learners_parent_id ON learners (parent_id);
"""

_CREATE_SKILLS = """
CREATE TABLE skills (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    code VARCHAR(64) NOT NULL,
    title VARCHAR(256) NOT NULL,
    grade_band VARCHAR(16) NOT NULL,
    standard VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_skills PRIMARY KEY (id),
    CONSTRAINT uq_skills_code UNIQUE (code)
);
"""

_CREATE_SKILL_PREREQ = """
CREATE TABLE skill_prereq (
    skill_id UUID NOT NULL,
    prereq_id UUID NOT NULL,
    CONSTRAINT pk_skill_prereq PRIMARY KEY (skill_id, prereq_id),
    CONSTRAINT fk_skill_prereq_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id) ON DELETE CASCADE,
    CONSTRAINT fk_skill_prereq_prereq_id_skills FOREIGN KEY(prereq_id) REFERENCES skills (id) ON DELETE CASCADE
);
"""

_CREATE_MISCONCEPTIONS = """
CREATE TABLE misconceptions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    code VARCHAR(16) NOT NULL,
    skill_id UUID,
    title VARCHAR(256) NOT NULL,
    description VARCHAR,
    cognitive_origin VARCHAR(256) NOT NULL,
    distractor_likelihood JSONB NOT NULL,
    distractor_likelihood_if_not_misconception JSONB,
    prevalence_prior NUMERIC(4, 3) NOT NULL,
    citation VARCHAR,
    content_version VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_misconceptions PRIMARY KEY (id),
    CONSTRAINT uq_misconceptions_code UNIQUE (code),
    CONSTRAINT fk_misconceptions_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id)
);
CREATE INDEX ix_misconceptions_skill_id ON misconceptions (skill_id);
"""

_CREATE_LEARNING_ITEMS = """
CREATE TABLE learning_items (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    item_code VARCHAR(64) NOT NULL,
    skill_id UUID,
    stem VARCHAR NOT NULL,
    representation VARCHAR(32) NOT NULL,
    correct_answer VARCHAR NOT NULL,
    distractors JSONB NOT NULL,
    elo INTEGER,
    role VARCHAR(32) NOT NULL,
    content_version VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_learning_items PRIMARY KEY (id),
    CONSTRAINT uq_learning_items_item_code UNIQUE (item_code),
    CONSTRAINT fk_learning_items_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id)
);
CREATE INDEX ix_learning_items_skill_id_elo ON learning_items (skill_id, elo);
"""

_CREATE_ITEM_VERSIONS = """
CREATE TABLE item_versions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learning_item_id UUID NOT NULL,
    content_version VARCHAR(32) NOT NULL,
    stem VARCHAR NOT NULL,
    correct_answer VARCHAR NOT NULL,
    distractors JSONB NOT NULL,
    elo INTEGER,
    representation VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_item_versions PRIMARY KEY (id),
    CONSTRAINT fk_item_versions_learning_item_id_learning_items FOREIGN KEY(learning_item_id) REFERENCES learning_items (id) ON DELETE CASCADE
);
CREATE INDEX ix_item_versions_learning_item_id ON item_versions (learning_item_id);
"""

_CREATE_SESSIONS = """
CREATE TABLE sessions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    state VARCHAR(32) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    ended_at TIMESTAMP WITH TIME ZONE,
    end_reason VARCHAR(32),
    CONSTRAINT pk_sessions PRIMARY KEY (id),
    CONSTRAINT fk_sessions_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE
);
CREATE INDEX ix_sessions_learner_id ON sessions (learner_id);
"""

_CREATE_SESSION_STATES = """
CREATE TABLE session_states (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    session_id UUID NOT NULL,
    from_state VARCHAR(32) NOT NULL,
    to_state VARCHAR(32) NOT NULL,
    trigger VARCHAR(64) NOT NULL,
    step INTEGER NOT NULL,
    at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_session_states PRIMARY KEY (id),
    CONSTRAINT uq_session_states_session_step UNIQUE (session_id, step),
    CONSTRAINT fk_session_states_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);
CREATE INDEX ix_session_states_session_id ON session_states (session_id);
"""

_CREATE_TURNS = """
CREATE TABLE turns (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    session_id UUID NOT NULL,
    idx INTEGER NOT NULL,
    speaker VARCHAR(16) NOT NULL,
    modality VARCHAR(32) NOT NULL,
    content VARCHAR NOT NULL,
    asr_confidence FLOAT,
    latency_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_turns PRIMARY KEY (id),
    CONSTRAINT uq_turns_session_idx UNIQUE (session_id, idx),
    CONSTRAINT fk_turns_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);
CREATE INDEX ix_turns_session_id ON turns (session_id);
"""

_CREATE_MODEL_RUNS = """
CREATE TABLE model_runs (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    session_id UUID,
    role VARCHAR(32) NOT NULL,
    provider VARCHAR(32) NOT NULL,
    endpoint_base_url VARCHAR(256) NOT NULL,
    model_id VARCHAR(128) NOT NULL,
    prompt_version VARCHAR(16) NOT NULL,
    attempt_index INTEGER NOT NULL,
    fallback_reason VARCHAR(32),
    structured_mode VARCHAR(16) NOT NULL,
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    latency_ms INTEGER NOT NULL,
    trace_id VARCHAR(128),
    credits_estimated NUMERIC(8, 3) NOT NULL,
    cache_hit BOOLEAN NOT NULL,
    recorded_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_model_runs PRIMARY KEY (id),
    CONSTRAINT fk_model_runs_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL
);
CREATE INDEX ix_model_runs_session_id ON model_runs (session_id);
"""

_CREATE_EVENTS = """
CREATE TABLE events (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    external_ref VARCHAR(128),
    event_type VARCHAR(64) NOT NULL,
    schema_version VARCHAR(16) NOT NULL,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
    learner_id UUID,
    session_id UUID,
    trace_id VARCHAR(128),
    payload JSONB NOT NULL,
    CONSTRAINT pk_events PRIMARY KEY (id),
    CONSTRAINT uq_events_learner_external_ref UNIQUE (learner_id, external_ref),
    CONSTRAINT fk_events_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE SET NULL,
    CONSTRAINT fk_events_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL
);
CREATE INDEX ix_events_session_id ON events (session_id);
CREATE INDEX ix_events_learner_id ON events (learner_id);
"""

_CREATE_RESPONSES = """
CREATE TABLE responses (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    session_id UUID,
    item_id UUID,
    raw VARCHAR NOT NULL,
    is_correct BOOLEAN NOT NULL,
    hints_used INTEGER NOT NULL,
    unaided BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_responses PRIMARY KEY (id),
    CONSTRAINT fk_responses_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_responses_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL,
    CONSTRAINT fk_responses_item_id_learning_items FOREIGN KEY(item_id) REFERENCES learning_items (id)
);
CREATE INDEX ix_responses_session_id ON responses (session_id);
CREATE INDEX ix_responses_learner_id ON responses (learner_id);
CREATE INDEX ix_responses_item_id ON responses (item_id);
"""

_CREATE_EXPLANATIONS = """
CREATE TABLE explanations (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    session_id UUID,
    skill_id UUID,
    text VARCHAR,
    modality VARCHAR(32) NOT NULL,
    asr_confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_explanations PRIMARY KEY (id),
    CONSTRAINT fk_explanations_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_explanations_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL,
    CONSTRAINT fk_explanations_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id)
);
CREATE INDEX ix_explanations_session_id ON explanations (session_id);
CREATE INDEX ix_explanations_skill_id ON explanations (skill_id);
CREATE INDEX ix_explanations_learner_id ON explanations (learner_id);
"""

_CREATE_DIAGNOSES = """
CREATE TABLE diagnoses (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    explanation_id UUID NOT NULL,
    labels JSONB NOT NULL,
    confidence FLOAT,
    model_run_id UUID,
    abstained BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_diagnoses PRIMARY KEY (id),
    CONSTRAINT fk_diagnoses_explanation_id_explanations FOREIGN KEY(explanation_id) REFERENCES explanations (id) ON DELETE CASCADE,
    CONSTRAINT fk_diagnoses_model_run_id_model_runs FOREIGN KEY(model_run_id) REFERENCES model_runs (id)
);
CREATE INDEX ix_diagnoses_explanation_id ON diagnoses (explanation_id);
"""

_CREATE_MASTERY_ESTIMATES = """
CREATE TABLE mastery_estimates (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    skill_id UUID NOT NULL,
    p_known NUMERIC(5, 4) NOT NULL,
    evidence_count INTEGER NOT NULL,
    unaided_correct INTEGER NOT NULL,
    transfer_verified BOOLEAN NOT NULL,
    model_version VARCHAR(64) NOT NULL,
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_mastery_estimates PRIMARY KEY (id),
    CONSTRAINT uq_mastery_estimates_learner_skill UNIQUE (learner_id, skill_id),
    CONSTRAINT ck_mastery_estimates_p_known_between_0_and_1 CHECK (p_known BETWEEN 0 AND 1),
    CONSTRAINT fk_mastery_estimates_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_mastery_estimates_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id)
);
CREATE INDEX ix_mastery_estimates_learner_id ON mastery_estimates (learner_id);
CREATE INDEX ix_mastery_estimates_skill_id ON mastery_estimates (skill_id);
"""

_CREATE_MISCONCEPTION_BELIEFS = """
CREATE TABLE misconception_beliefs (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    misconception_id UUID NOT NULL,
    p_holds NUMERIC(5, 4) NOT NULL,
    state VARCHAR(16) NOT NULL,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_evidence_id UUID,
    CONSTRAINT pk_misconception_beliefs PRIMARY KEY (id),
    CONSTRAINT uq_misconception_beliefs_learner_misc UNIQUE (learner_id, misconception_id),
    CONSTRAINT ck_misconception_beliefs_p_holds_between_0_and_1 CHECK (p_holds BETWEEN 0 AND 1),
    CONSTRAINT fk_misconception_beliefs_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_misconception_beliefs_misconception_id_misconceptions FOREIGN KEY(misconception_id) REFERENCES misconceptions (id)
);
CREATE INDEX ix_misconception_beliefs_misconception_id ON misconception_beliefs (misconception_id);
CREATE INDEX ix_misconception_beliefs_learner_id ON misconception_beliefs (learner_id);
"""

_CREATE_TEACHING_EPISODES = """
CREATE TABLE teaching_episodes (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    session_id UUID,
    misconception_id UUID NOT NULL,
    turns INTEGER NOT NULL,
    resolved BOOLEAN NOT NULL,
    resolution_turn INTEGER,
    quality_score NUMERIC(5, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_teaching_episodes PRIMARY KEY (id),
    CONSTRAINT fk_teaching_episodes_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL,
    CONSTRAINT fk_teaching_episodes_misconception_id_misconceptions FOREIGN KEY(misconception_id) REFERENCES misconceptions (id)
);
CREATE INDEX ix_teaching_episodes_session_id ON teaching_episodes (session_id);
CREATE INDEX ix_teaching_episodes_misconception_id ON teaching_episodes (misconception_id);
"""

_CREATE_EVIDENCE = """
CREATE TABLE evidence (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    external_ref VARCHAR(128),
    learner_id UUID NOT NULL,
    session_id UUID,
    turn_id UUID,
    mastery_estimate_id UUID,
    misconception_belief_id UUID,
    kind VARCHAR(32) NOT NULL,
    source_event_id UUID NOT NULL,
    weight NUMERIC(3, 2) NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_evidence PRIMARY KEY (id),
    CONSTRAINT ck_evidence_weight_between_0_and_3 CHECK (weight BETWEEN 0 AND 3),
    CONSTRAINT uq_evidence_learner_external_ref UNIQUE (learner_id, external_ref),
    CONSTRAINT fk_evidence_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_evidence_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL,
    CONSTRAINT fk_evidence_turn_id_turns FOREIGN KEY(turn_id) REFERENCES turns (id) ON DELETE SET NULL,
    CONSTRAINT fk_evidence_mastery_estimate_id_mastery_estimates FOREIGN KEY(mastery_estimate_id) REFERENCES mastery_estimates (id) ON DELETE CASCADE,
    CONSTRAINT fk_evidence_misconception_belief_id_misconception_beliefs FOREIGN KEY(misconception_belief_id) REFERENCES misconception_beliefs (id) ON DELETE CASCADE,
    CONSTRAINT fk_evidence_source_event_id_events FOREIGN KEY(source_event_id) REFERENCES events (id)
);
CREATE INDEX ix_evidence_source_event_id ON evidence (source_event_id);
CREATE INDEX ix_evidence_misconception_belief_id ON evidence (misconception_belief_id);
CREATE INDEX ix_evidence_mastery_estimate_id ON evidence (mastery_estimate_id);
CREATE INDEX ix_evidence_learner_id ON evidence (learner_id);
CREATE INDEX ix_evidence_session_id ON evidence (session_id);
"""

_CREATE_POLICY_DECISIONS = """
CREATE TABLE policy_decisions (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    session_id UUID NOT NULL,
    trajectory_id VARCHAR(128) NOT NULL,
    step INTEGER NOT NULL,
    state_vector VECTOR(14) NOT NULL,
    state_schema_version VARCHAR(16) NOT NULL,
    action_type VARCHAR(32) NOT NULL,
    action_params JSONB NOT NULL,
    source VARCHAR(16) NOT NULL,
    shield_overrode BOOLEAN NOT NULL,
    counterfactual_bandit_choice VARCHAR(32),
    observation JSONB NOT NULL,
    reward_immediate FLOAT,
    reward_deferred_pending JSONB NOT NULL,
    next_state_ref VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_policy_decisions PRIMARY KEY (id),
    CONSTRAINT uq_policy_decisions_session_step UNIQUE (session_id, step),
    CONSTRAINT fk_policy_decisions_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);
CREATE INDEX ix_policy_decisions_session_id ON policy_decisions (session_id);
"""
# state_vector's vector(14) is a contract-fixed invariant (see
# db/models/policy.py's POLICY_STATE_VECTOR_DIM docstring), not a
# configurable embedding dimension -- unlike embedding_records below, it is
# a plain literal here.

_CREATE_RETRIEVAL_SCHEDULE = """
CREATE TABLE retrieval_schedule (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    skill_id UUID NOT NULL,
    due_at TIMESTAMP WITH TIME ZONE NOT NULL,
    interval_days INTEGER NOT NULL,
    stability NUMERIC(8, 4),
    difficulty NUMERIC(8, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_retrieval_schedule PRIMARY KEY (id),
    CONSTRAINT fk_retrieval_schedule_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_retrieval_schedule_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id)
);
CREATE INDEX ix_retrieval_schedule_learner_id ON retrieval_schedule (learner_id);
"""

_CREATE_MEMORY_ITEMS = """
CREATE TABLE memory_items (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    session_id UUID,
    skill_id UUID,
    content VARCHAR NOT NULL,
    kind VARCHAR(32) NOT NULL,
    metadata JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_memory_items PRIMARY KEY (id),
    CONSTRAINT fk_memory_items_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_memory_items_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL,
    CONSTRAINT fk_memory_items_skill_id_skills FOREIGN KEY(skill_id) REFERENCES skills (id)
);
CREATE INDEX ix_memory_items_learner_id ON memory_items (learner_id);
"""


def _create_embedding_records_sql(embedding_dimension: int) -> str:
    """The one table whose DDL is not a frozen literal: the vector column's
    dimension is read from ``Settings.embedding_dimension`` at apply time,
    per docs/DECISIONS.md D2 (see module docstring)."""
    return f"""
CREATE TABLE embedding_records (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    memory_item_id UUID NOT NULL,
    learner_id UUID NOT NULL,
    embedding VECTOR({embedding_dimension}) NOT NULL,
    metadata JSONB NOT NULL,
    CONSTRAINT pk_embedding_records PRIMARY KEY (id),
    CONSTRAINT fk_embedding_records_memory_item_id_memory_items FOREIGN KEY(memory_item_id) REFERENCES memory_items (id) ON DELETE CASCADE,
    CONSTRAINT fk_embedding_records_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE
);
CREATE INDEX ix_embedding_records_memory_item_id ON embedding_records (memory_item_id);
CREATE INDEX ix_embedding_records_learner_id ON embedding_records (learner_id);
"""


_CREATE_PROOF_ARTIFACTS = """
CREATE TABLE proof_artifacts (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    session_id UUID,
    claims JSONB NOT NULL,
    evidence_ids UUID[] NOT NULL,
    pdf_s3_key VARCHAR(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_proof_artifacts PRIMARY KEY (id),
    CONSTRAINT fk_proof_artifacts_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE,
    CONSTRAINT fk_proof_artifacts_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL
);
CREATE INDEX ix_proof_artifacts_learner_id ON proof_artifacts (learner_id);
"""

_CREATE_TUTOR_BRIEFINGS = """
CREATE TABLE tutor_briefings (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID NOT NULL,
    payload JSONB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    viewed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_tutor_briefings PRIMARY KEY (id),
    CONSTRAINT fk_tutor_briefings_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE CASCADE
);
CREATE INDEX ix_tutor_briefings_learner_id ON tutor_briefings (learner_id);
"""

_CREATE_SAFETY_EVENTS = """
CREATE TABLE safety_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    learner_id UUID,
    session_id UUID,
    kind VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    raw_ref VARCHAR(256),
    action_taken VARCHAR(256),
    notified_at TIMESTAMP WITH TIME ZONE,
    at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_safety_events PRIMARY KEY (id),
    CONSTRAINT fk_safety_events_learner_id_learners FOREIGN KEY(learner_id) REFERENCES learners (id) ON DELETE SET NULL,
    CONSTRAINT fk_safety_events_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE SET NULL
);
CREATE INDEX ix_safety_events_learner_id ON safety_events (learner_id);
"""

_CREATE_AUDIT_EVENTS = """
CREATE TABLE audit_events (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    actor VARCHAR(128) NOT NULL,
    action VARCHAR(64) NOT NULL,
    resource VARCHAR(256) NOT NULL,
    at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT pk_audit_events PRIMARY KEY (id)
);
CREATE INDEX ix_audit_events_resource ON audit_events (resource);
"""

_CREATE_JOBS = """
CREATE TABLE jobs (
    id UUID DEFAULT gen_random_uuid() NOT NULL,
    job_type VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL,
    payload JSONB NOT NULL,
    attempt_count INTEGER NOT NULL,
    max_attempts INTEGER NOT NULL,
    error VARCHAR,
    claimed_by VARCHAR(128),
    claimed_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    available_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    CONSTRAINT pk_jobs PRIMARY KEY (id),
    CONSTRAINT ck_jobs_status_in_job_statuses CHECK (status IN ('queued', 'running', 'succeeded', 'failed'))
);
CREATE INDEX ix_jobs_status ON jobs (status);
CREATE INDEX ix_jobs_job_type ON jobs (job_type);
"""

_CREATE_TABLE_SQL: dict[str, str] = {
    "parents": _CREATE_PARENTS,
    "learners": _CREATE_LEARNERS,
    "skills": _CREATE_SKILLS,
    "skill_prereq": _CREATE_SKILL_PREREQ,
    "misconceptions": _CREATE_MISCONCEPTIONS,
    "learning_items": _CREATE_LEARNING_ITEMS,
    "item_versions": _CREATE_ITEM_VERSIONS,
    "sessions": _CREATE_SESSIONS,
    "session_states": _CREATE_SESSION_STATES,
    "turns": _CREATE_TURNS,
    "model_runs": _CREATE_MODEL_RUNS,
    "events": _CREATE_EVENTS,
    "responses": _CREATE_RESPONSES,
    "explanations": _CREATE_EXPLANATIONS,
    "diagnoses": _CREATE_DIAGNOSES,
    "mastery_estimates": _CREATE_MASTERY_ESTIMATES,
    "misconception_beliefs": _CREATE_MISCONCEPTION_BELIEFS,
    "teaching_episodes": _CREATE_TEACHING_EPISODES,
    "evidence": _CREATE_EVIDENCE,
    "policy_decisions": _CREATE_POLICY_DECISIONS,
    "retrieval_schedule": _CREATE_RETRIEVAL_SCHEDULE,
    "memory_items": _CREATE_MEMORY_ITEMS,
    # "embedding_records" is generated by _create_embedding_records_sql(),
    # not present in this static map -- see upgrade().
    "proof_artifacts": _CREATE_PROOF_ARTIFACTS,
    "tutor_briefings": _CREATE_TUTOR_BRIEFINGS,
    "safety_events": _CREATE_SAFETY_EVENTS,
    "audit_events": _CREATE_AUDIT_EVENTS,
    "jobs": _CREATE_JOBS,
}


def _execute_statements(sql: str) -> None:
    """Execute each ``;``-terminated statement in ``sql`` separately --
    asyncpg's prepared-statement protocol (unlike psycopg2) refuses a single
    ``execute()`` call containing more than one SQL command, so each
    ``_CREATE_*`` block's ``CREATE TABLE`` and its ``CREATE INDEX``
    statement(s) must be sent one at a time. Safe to split naively on ``;``
    here: this is pure, literal DDL with no string/JSON literals containing
    a semicolon.
    """
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            op.execute(statement)


def upgrade() -> None:
    for table_name in TABLE_ORDER:
        if table_name == "embedding_records":
            dim = get_settings().embedding_dimension
            _execute_statements(_create_embedding_records_sql(dim))
        else:
            _execute_statements(_CREATE_TABLE_SQL[table_name])

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

    for table_name in reversed(TABLE_ORDER):
        op.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")
