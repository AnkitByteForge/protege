"""``proof_artifacts`` aggregate (roadmap P20; §22 ``proof_artifacts``).

Reuses the P9 schema exactly as it stands -- no migration, no duplicate
evidence storage. ``ProofArtifact.claims`` (JSONB) carries the enum-selected
claim, its grounded sentences, and caveats; ``evidence_ids`` (a real
``ARRAY(UUID)`` column) carries the resolved evidence rows this snapshot
touched, for a cheap "what did this card touch" query without re-parsing
the JSONB. The evidence TREE itself (source event, session, turn) is never
duplicated here -- a reader resolves it live from ``EvidenceRepository``
(append-only, so it never drifts from what was actually persisted).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import ProofArtifact


class ProofRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        learner_row_id: uuid.UUID,
        session_row_id: uuid.UUID | None,
        claims: list[dict[str, Any]],
        evidence_ids: list[uuid.UUID],
    ) -> ProofArtifact:
        row = ProofArtifact(
            learner_id=learner_row_id,
            session_id=session_row_id,
            claims=claims,
            evidence_ids=evidence_ids,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get_latest_for_learner(self, learner_row_id: uuid.UUID) -> ProofArtifact | None:
        result = await self._session.execute(
            select(ProofArtifact)
            .where(ProofArtifact.learner_id == learner_row_id)
            .order_by(ProofArtifact.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()

    async def get_for_session(self, session_row_id: uuid.UUID) -> ProofArtifact | None:
        result = await self._session.execute(
            select(ProofArtifact).where(ProofArtifact.session_id == session_row_id)
        )
        return result.scalar_one_or_none()
