"""Learning-state aggregate: ``mastery_estimates``, ``misconception_beliefs``,
``teaching_episodes`` -- the authoritative persisted state (roadmap P9:
"``mastery_estimates`` and ``misconception_beliefs`` become authoritative
persisted state"). ``upsert_mastery``/``upsert_misconception_belief`` accept
the P1 contracts (``protege.contracts.MasteryEstimate`` /
``MisconceptionBelief``) directly, matching ``learning-engine``'s own output
shape -- no P9-local reinterpretation of what the numbers mean, only where
they are stored.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import MasteryEstimate as MasteryEstimateContract
from protege.contracts import MisconceptionBelief as MisconceptionBeliefContract

from ..db.models import MasteryEstimateRow, MisconceptionBeliefRow, TeachingEpisodeRow


class LearningStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_mastery(
        self, *, learner_id: uuid.UUID, skill_id: uuid.UUID, estimate: MasteryEstimateContract
    ) -> MasteryEstimateRow:
        result = await self._session.execute(
            select(MasteryEstimateRow).where(
                MasteryEstimateRow.learner_id == learner_id, MasteryEstimateRow.skill_id == skill_id
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = MasteryEstimateRow(
                learner_id=learner_id, skill_id=skill_id, p_known=estimate.p_known
            )
            self._session.add(row)
        row.p_known = estimate.p_known
        row.evidence_count = estimate.evidence_count
        row.unaided_correct = estimate.unaided_correct
        row.transfer_verified = estimate.transfer_verified
        row.model_version = estimate.model_version
        await self._session.flush()
        return row

    async def get_mastery(
        self, learner_id: uuid.UUID, skill_id: uuid.UUID
    ) -> MasteryEstimateRow | None:
        result = await self._session.execute(
            select(MasteryEstimateRow).where(
                MasteryEstimateRow.learner_id == learner_id, MasteryEstimateRow.skill_id == skill_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert_misconception_belief(
        self,
        *,
        learner_id: uuid.UUID,
        misconception_id: uuid.UUID,
        belief: MisconceptionBeliefContract,
        resolution_evidence_row_id: uuid.UUID | None = None,
    ) -> MisconceptionBeliefRow:
        result = await self._session.execute(
            select(MisconceptionBeliefRow).where(
                MisconceptionBeliefRow.learner_id == learner_id,
                MisconceptionBeliefRow.misconception_id == misconception_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = MisconceptionBeliefRow(
                learner_id=learner_id, misconception_id=misconception_id, p_holds=belief.p_holds
            )
            self._session.add(row)
        row.p_holds = belief.p_holds
        row.state = str(belief.state)
        row.resolved_at = belief.resolved_at
        row.resolution_evidence_id = resolution_evidence_row_id
        await self._session.flush()
        return row

    async def get_misconception_belief(
        self, learner_id: uuid.UUID, misconception_id: uuid.UUID
    ) -> MisconceptionBeliefRow | None:
        result = await self._session.execute(
            select(MisconceptionBeliefRow).where(
                MisconceptionBeliefRow.learner_id == learner_id,
                MisconceptionBeliefRow.misconception_id == misconception_id,
            )
        )
        return result.scalar_one_or_none()

    async def append_teaching_episode(
        self,
        *,
        session_id: uuid.UUID | None,
        misconception_id: uuid.UUID,
        turns: int,
        resolved: bool,
        resolution_turn: int | None,
        quality_score: float | None = None,
    ) -> TeachingEpisodeRow:
        row = TeachingEpisodeRow(
            session_id=session_id,
            misconception_id=misconception_id,
            turns=turns,
            resolved=resolved,
            resolution_turn=resolution_turn,
            quality_score=quality_score,
        )
        self._session.add(row)
        await self._session.flush()
        return row
