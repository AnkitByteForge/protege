"""``idempotency_keys`` aggregate (roadmap P10).

Two-phase per request, both phases inside the *same* ``AsyncSession``/
transaction as the work being guarded (never a separate connection):
``reserve`` inserts a placeholder row and ``flush()``es it immediately, so a
genuinely concurrent duplicate request's own ``reserve`` collides on the
unique constraint (``uq_idempotency_keys_actor_method_path_key``) right
away -- ``flush()`` raises ``IntegrityError`` synchronously, which
propagates out through ``db.engine.session_scope``'s
``except BaseException: rollback(); raise``, discarding *everything* that
request did (including any FSM state it had already persisted), not just
the idempotency row. ``complete`` then fills in the real response once the
guarded work has finished, in the same transaction. A caller that hits the
``IntegrityError`` re-queries (in a fresh transaction) for the row the
winner actually committed and serves its cached response instead of
redoing the work -- see ``idempotency.py`` (the service-layer helper) for
that orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import IdempotencyKeyRow


@dataclass(frozen=True)
class StoredResponse:
    status: int
    body: dict[str, object]


class IdempotencyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(
        self, *, actor_subject: str, method: str, path: str, key: str, now: datetime
    ) -> IdempotencyKeyRow | None:
        result = await self._session.execute(
            select(IdempotencyKeyRow).where(
                IdempotencyKeyRow.actor_subject == actor_subject,
                IdempotencyKeyRow.http_method == method,
                IdempotencyKeyRow.request_path == path,
                IdempotencyKeyRow.idempotency_key == key,
                IdempotencyKeyRow.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def reserve(
        self,
        *,
        actor_subject: str,
        method: str,
        path: str,
        key: str,
        request_hash: str,
        expires_at: datetime,
    ) -> IdempotencyKeyRow:
        """Insert the placeholder row for this request. Raises
        ``sqlalchemy.exc.IntegrityError`` (via ``flush()``) if a row for
        this exact ``(actor, method, path, key)`` already exists -- the
        caller's transaction is then rolled back by ``session_scope``."""
        row = IdempotencyKeyRow(
            actor_subject=actor_subject,
            http_method=method,
            request_path=path,
            idempotency_key=key,
            request_hash=request_hash,
            response_status=None,
            response_body=None,
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def complete(
        self, row: IdempotencyKeyRow, *, status: int, body: dict[str, object]
    ) -> None:
        row.response_status = status
        row.response_body = body
        await self._session.flush()
