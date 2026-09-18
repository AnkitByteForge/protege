"""``events`` aggregate: the append-only domain event log (§24).

``append`` is the only write this repository exposes -- there is no
``update``/``delete`` method, and the database itself additionally refuses
both (``db/append_only.py``'s trigger) so this is not "repository
convention only" (roadmap P9 rule). ``event.event_id`` (the opaque,
pre-persistence id a caller like P8's ``IdAllocator`` minted) is preserved
as ``external_ref`` -- the real, queryable identity is the row's own
``id`` (docs/DECISIONS.md: "the persistence layer (P9) assigns UUIDs").
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.contracts import DomainEvent

from ..db.models import EventRow


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        event: DomainEvent,
        *,
        learner_row_id: uuid.UUID | None,
        session_row_id: uuid.UUID | None,
    ) -> EventRow:
        row = EventRow(
            external_ref=event.event_id,
            event_type=str(event.event_type),
            schema_version=event.schema_version,
            occurred_at=event.occurred_at,
            learner_id=learner_row_id,
            session_id=session_row_id,
            trace_id=event.trace_id,
            payload=dict(event.payload),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, event_row_id: uuid.UUID) -> EventRow | None:
        return await self._session.get(EventRow, event_row_id)

    async def list_for_session(self, session_row_id: uuid.UUID) -> list[EventRow]:
        result = await self._session.execute(
            select(EventRow)
            .where(EventRow.session_id == session_row_id)
            .order_by(EventRow.occurred_at)
        )
        return list(result.scalars().all())
