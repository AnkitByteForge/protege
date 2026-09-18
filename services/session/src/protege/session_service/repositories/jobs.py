"""``jobs`` aggregate: queued -> claimed/running -> succeeded | failed/retryable.

``claim`` is the one method that matters for correctness: it uses
``SELECT ... FOR UPDATE SKIP LOCKED`` (roadmap P9 exact requirement) inside
the caller's own transaction, so two workers racing the same call never
claim the same row -- one gets it, the other's ``SKIP LOCKED`` scan simply
skips the locked row and finds the next (or nothing). The caller commits
promptly after claiming (see ``jobs/worker.py``) so the row-level lock is
held only for the claim itself, not for the job's full execution; once
claimed, ``status='running'`` is what prevents a second claim, not the lock.

**Stale-claim reclaim.** A worker that dies (crash, OOM-kill, deploy) after
claiming a job but before calling ``complete``/``fail`` leaves that job
stuck at ``status='running'`` forever -- no other worker's claim query
selects ``running`` rows, so nothing would ever retry it, contradicting the
roadmap's own queue semantics ("if the worker dies mid-job, it must be
retried"). ``claim`` therefore also selects ``running`` rows whose
``claimed_at`` is older than ``stale_after_s`` and treats them exactly like
a fresh claim (including the ``attempt_count`` increment and the
``max_attempts`` check) -- a stale job that has already exhausted its
attempts is marked terminally ``failed`` here rather than reclaimed again.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import JobRow

DEFAULT_STALE_CLAIM_TIMEOUT_S = 300.0
"""Mirrors ``Settings.job_stale_claim_timeout_s``'s default, for callers
that construct a ``JobRepository`` directly without going through
``Settings`` (e.g. tests). ``jobs/worker.py`` passes the real configured
value through explicitly."""


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        *,
        job_type: str,
        payload: dict[str, object] | None = None,
        max_attempts: int = 5,
        available_at: datetime | None = None,
    ) -> JobRow:
        row = JobRow(
            job_type=job_type,
            payload=payload or {},
            max_attempts=max_attempts,
            available_at=available_at or datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def claim(
        self, *, worker_id: str, stale_after_s: float = DEFAULT_STALE_CLAIM_TIMEOUT_S
    ) -> JobRow | None:
        """Atomically claim the oldest eligible job -- either genuinely
        ``queued``, or ``running`` with a claim stale enough to mean its
        worker died (see module docstring) -- or ``None`` if nothing is
        eligible. Must be called inside a transaction the caller commits
        soon after (see module docstring).

        A stale job already at ``max_attempts`` is marked terminally
        ``failed`` here (not reclaimed) and this call returns ``None`` for
        it; the caller's next ``claim`` picks up whatever is next.
        """
        now = datetime.now(UTC)
        stale_cutoff = now - timedelta(seconds=stale_after_s)
        stmt = (
            select(JobRow)
            .where(
                or_(
                    and_(JobRow.status == "queued", JobRow.available_at <= func.now()),
                    and_(JobRow.status == "running", JobRow.claimed_at <= stale_cutoff),
                )
            )
            .order_by(JobRow.available_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if row.attempt_count >= row.max_attempts:
            row.status = "failed"
            row.error = (
                row.error or ""
            ) + " | abandoned: claim exceeded the stale-claim timeout and max_attempts was reached"
            row.finished_at = now
            row.updated_at = now
            await self._session.flush()
            return None
        row.status = "running"
        row.claimed_by = worker_id
        row.claimed_at = now
        row.started_at = now
        row.attempt_count += 1
        row.updated_at = now
        await self._session.flush()
        return row

    async def complete(self, job_id: uuid.UUID) -> None:
        row = await self._session.get(JobRow, job_id)
        if row is None:
            return
        now = datetime.now(UTC)
        row.status = "succeeded"
        row.finished_at = now
        row.updated_at = now
        await self._session.flush()

    async def fail(
        self, job_id: uuid.UUID, *, error: str, retry_backoff_s: float = 5.0
    ) -> JobRow | None:
        """Record a failure. Retries (re-queues with backoff) while
        ``attempt_count < max_attempts``; marks permanently ``failed``
        once attempts are exhausted."""
        row = await self._session.get(JobRow, job_id)
        if row is None:
            return None
        now = datetime.now(UTC)
        row.error = error
        row.updated_at = now
        if row.attempt_count < row.max_attempts:
            row.status = "queued"
            row.available_at = now + timedelta(seconds=retry_backoff_s)
            row.claimed_by = None
            row.claimed_at = None
        else:
            row.status = "failed"
            row.finished_at = now
        await self._session.flush()
        return row

    async def get(self, job_id: uuid.UUID) -> JobRow | None:
        return await self._session.get(JobRow, job_id)
