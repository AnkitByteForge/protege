"""§22 ``policy_decisions`` -- the RL trajectory log. ``state_vector`` is a
fixed ``vector(14)`` because it mirrors
``protege.contracts.session.PolicyDecisionState.vector``, which is a
contract-fixed 14-dim invariant (``Field(min_length=14, max_length=14)``,
§11.2/§11.3) -- not a configurable embedding dimension like
``embedding_records.embedding`` (docs/DECISIONS.md D2), so it is not driven
by ``Settings``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..base import Base, created_at_column, uuid_pk

POLICY_STATE_VECTOR_DIM = 14
"""§11.2/§11.3's fixed 14-dim RL context vector -- see module docstring."""


class PolicyDecisionRow(Base):
    """§22 ``policy_decisions``."""

    __tablename__ = "policy_decisions"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    trajectory_id: Mapped[str] = mapped_column(String(128), nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    state_vector: Mapped[list[float]] = mapped_column(
        Vector(POLICY_STATE_VECTOR_DIM), nullable=False
    )
    state_schema_version: Mapped[str] = mapped_column(
        String(16), nullable=False, default="state.v1"
    )
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    action_params: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(16), nullable=False, default="rules")
    shield_overrode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    counterfactual_bandit_choice: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observation: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False, default=dict)
    reward_immediate: Mapped[float | None] = mapped_column(nullable=True)
    reward_deferred_pending: Mapped[list[object]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    next_state_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = created_at_column()

    __table_args__ = (
        UniqueConstraint("session_id", "step", name="uq_policy_decisions_session_step"),
    )
