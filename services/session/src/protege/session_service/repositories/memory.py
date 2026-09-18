"""``memory_items`` + ``embedding_records`` aggregate. Storage only -- no
retrieval, no scoring, and nothing here ever reads ``embedding`` to move a
mastery or misconception probability (roadmap P9 rule 9; §12: "structured
learner state is NEVER derived from semantic memory").
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import EmbeddingRecord, MemoryItem


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_memory_item(
        self,
        *,
        learner_id: uuid.UUID,
        content: str,
        kind: str,
        session_id: uuid.UUID | None = None,
        skill_id: uuid.UUID | None = None,
        metadata: dict[str, object] | None = None,
    ) -> MemoryItem:
        row = MemoryItem(
            learner_id=learner_id,
            session_id=session_id,
            skill_id=skill_id,
            content=content,
            kind=kind,
            metadata_=metadata or {},
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_embedding(
        self,
        *,
        memory_item_id: uuid.UUID,
        learner_id: uuid.UUID,
        embedding: Sequence[float],
        metadata: dict[str, object] | None = None,
    ) -> EmbeddingRecord:
        row = EmbeddingRecord(
            memory_item_id=memory_item_id,
            learner_id=learner_id,
            embedding=list(embedding),
            metadata_=metadata or {},
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def count_embeddings_for_learner(self, learner_id: uuid.UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(EmbeddingRecord)
            .where(EmbeddingRecord.learner_id == learner_id)
        )
        return int(result.scalar_one())
