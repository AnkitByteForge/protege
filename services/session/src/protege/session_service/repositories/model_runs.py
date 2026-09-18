"""``model_runs`` aggregate.

Consumes ``protege.llm.telemetry.ModelRunRecord`` directly (that dataclass's
own docstring: "P9 owns the actual table and migration; P4 produces records
in this shape so the future persistence layer has nothing to invent").

Deliberately a bulk, post-hoc write, not a live per-call synchronous one:
``ModelRouter`` sends every completed call to a ``TelemetrySink.record()``
that is a **synchronous** call (``packages/llm/src/protege/llm/telemetry.py``),
while P9's stack is asyncpg-only (roadmap P9 rule: "SQLAlchemy 2 + asyncpg").
Bridging a sync callback into an async DB write mid-request would need either
a second, sync DB driver (contradicting the asyncpg-only rule) or a real
event-loop bridge for zero benefit in this hackathon-scoped phase --
callers instead collect an ``InMemoryTelemetrySink``'s buffered records for
one session/run and hand them to ``record_many`` once, in the same
transaction as the rest of that session's persistence. See
``persistence/thin_thread_bridge.py`` for the call site.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from protege.llm.telemetry import ModelRunRecord

from ..db.models import ModelRunRow


class ModelRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_many(
        self, records: Sequence[ModelRunRecord], *, session_row_id: uuid.UUID | None
    ) -> list[ModelRunRow]:
        rows = [
            ModelRunRow(
                session_id=session_row_id,
                role=record.role,
                provider=record.provider,
                endpoint_base_url=record.endpoint_base_url,
                model_id=record.model_id,
                prompt_version=record.prompt_version,
                attempt_index=record.attempt_index,
                fallback_reason=(
                    str(record.fallback_reason) if record.fallback_reason is not None else None
                ),
                structured_mode=str(record.structured_mode),
                tokens_in=record.tokens_in,
                tokens_out=record.tokens_out,
                latency_ms=record.latency_ms,
                trace_id=record.trace_id,
                credits_estimated=record.credits_estimated,
                cache_hit=record.cache_hit,
                recorded_at=record.recorded_at,
            )
            for record in records
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return rows

    async def list_for_session(self, session_row_id: uuid.UUID) -> list[ModelRunRow]:
        result = await self._session.execute(
            select(ModelRunRow)
            .where(ModelRunRow.session_id == session_row_id)
            .order_by(ModelRunRow.recorded_at)
        )
        return list(result.scalars().all())
