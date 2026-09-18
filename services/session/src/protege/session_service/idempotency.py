"""Service-layer idempotency orchestration (roadmap P10), sitting on top of
``repositories/idempotency.py``.

Every ``POST`` route wraps its work in :func:`run_idempotent_request`,
passing a ``handler`` that does the actual work (creating a session,
applying an event, ...) using the exact ``AsyncSession`` it is given --
never opening its own transaction -- so the idempotency ledger row and the
work it guards commit or roll back together, atomically, in one Postgres
transaction. See ``repositories/idempotency.py``'s module docstring for why
this gives correct exactly-once semantics even under a genuine race.
"""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .db.engine import session_scope
from .errors import IdempotencyKeyReusedError
from .repositories.idempotency import IdempotencyRepository
from .settings import Settings

Handler = Callable[[AsyncSession], Awaitable[tuple[int, dict[str, Any]]]]


def hash_request_body(raw_body: bytes) -> str:
    return hashlib.sha256(raw_body).hexdigest()


async def _cached_response(
    session: AsyncSession,
    *,
    actor_subject: str,
    method: str,
    path: str,
    key: str,
    request_hash: str,
) -> tuple[int, dict[str, Any]] | None:
    repo = IdempotencyRepository(session)
    row = await repo.find(
        actor_subject=actor_subject,
        method=method,
        path=path,
        key=key,
        now=datetime.now(UTC),
    )
    if row is None:
        return None
    if row.request_hash != request_hash:
        raise IdempotencyKeyReusedError(
            "this Idempotency-Key was already used with a different request body"
        )
    if row.response_status is None:
        # Cannot happen in steady state -- reserve() and complete() share one
        # transaction, so no other transaction ever observes a committed row
        # with no response yet (see repositories/idempotency.py). Guarded
        # defensively rather than assumed.
        raise IdempotencyKeyReusedError("a request with this Idempotency-Key is already in flight")
    return row.response_status, dict(row.response_body or {})


async def run_idempotent_request(
    *,
    settings: Settings,
    actor_subject: str,
    method: str,
    path: str,
    idempotency_key: str,
    request_hash: str,
    handler: Handler,
) -> tuple[int, dict[str, Any]]:
    expires_at = datetime.now(UTC) + timedelta(hours=settings.idempotency_ttl_hours)
    try:
        async with session_scope() as session:
            cached = await _cached_response(
                session,
                actor_subject=actor_subject,
                method=method,
                path=path,
                key=idempotency_key,
                request_hash=request_hash,
            )
            if cached is not None:
                return cached
            repo = IdempotencyRepository(session)
            row = await repo.reserve(
                actor_subject=actor_subject,
                method=method,
                path=path,
                key=idempotency_key,
                request_hash=request_hash,
                expires_at=expires_at,
            )
            status_code, body = await handler(session)
            await repo.complete(row, status=status_code, body=body)
            return status_code, body
    except IntegrityError:
        # A concurrent request with the identical key committed first,
        # rolling this entire transaction back (including any FSM state it
        # had already persisted) -- serve the winner's response instead.
        async with session_scope() as session:
            cached = await _cached_response(
                session,
                actor_subject=actor_subject,
                method=method,
                path=path,
                key=idempotency_key,
                request_hash=request_hash,
            )
            if cached is not None:
                return cached
            raise
