"""``policy_decisions`` aggregate -- the RL trajectory log (§11.3, §22).
Persistence only; P9 makes no policy decisions (roadmap: "Do not implement
... Policy logic ... in P9")."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import PolicyDecision

from ..db.models import PolicyDecisionRow


class PolicyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self, decision: PolicyDecision, *, session_row_id: uuid.UUID
    ) -> PolicyDecisionRow:
        row = PolicyDecisionRow(
            session_id=session_row_id,
            trajectory_id=decision.trajectory_id,
            step=decision.step,
            state_vector=list(decision.state.vector),
            state_schema_version=decision.state.schema_version,
            action_type=str(decision.action.type),
            action_params=dict(decision.action.params),
            source=decision.action.source,
            shield_overrode=decision.action.shield_overrode,
            counterfactual_bandit_choice=(
                str(decision.action.counterfactual_bandit_choice)
                if decision.action.counterfactual_bandit_choice is not None
                else None
            ),
            observation=dict(decision.observation),
            reward_immediate=decision.reward.immediate,
            reward_deferred_pending=list(decision.reward.deferred_pending),
            next_state_ref=decision.next_state_ref,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_session(self, session_row_id: uuid.UUID) -> list[PolicyDecisionRow]:
        result = await self._session.execute(
            select(PolicyDecisionRow)
            .where(PolicyDecisionRow.session_id == session_row_id)
            .order_by(PolicyDecisionRow.step)
        )
        return list(result.scalars().all())
