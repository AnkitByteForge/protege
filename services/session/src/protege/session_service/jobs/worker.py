"""The P9 job worker loop (roadmap P9: "worker loop"; addendum §8: "jobs
table<br/>in-process worker loop").

Each claim, and each completion/failure write, runs in its own short
transaction (``db.engine.session_scope``) -- ``JobRepository.claim`` uses
``SELECT ... FOR UPDATE SKIP LOCKED`` inside that transaction, so multiple
worker processes calling :func:`claim_and_run_once` concurrently never claim
the same row (see ``repositories/jobs.py``). The job handler itself runs
*outside* any transaction the claim held, so a slow or failing handler never
holds a row lock.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable, Mapping

from ..db.engine import session_scope
from ..db.models import JobRow
from ..repositories.jobs import JobRepository
from ..settings import Settings, get_settings

JobHandler = Callable[[JobRow], Awaitable[None]]
"""One job type's execution logic. Raises on failure; ``claim_and_run_once``
converts any exception into ``JobRepository.fail`` (retry-or-terminal per
that repository's attempt-count rule) -- no business/retry decision lives
in this module beyond "an exception means the job failed"."""


async def claim_and_run_once(
    *, worker_id: str, handlers: Mapping[str, JobHandler], settings: Settings | None = None
) -> bool:
    """Claim and run at most one job. Returns ``True`` iff a job was claimed
    (regardless of whether it then succeeded or failed) -- the caller uses
    this to decide whether to poll again immediately or back off."""
    resolved_settings = settings if settings is not None else get_settings()
    async with session_scope(settings) as session:
        job = await JobRepository(session).claim(
            worker_id=worker_id, stale_after_s=resolved_settings.job_stale_claim_timeout_s
        )
        if job is None:
            return False
        job_id: uuid.UUID = job.id
        job_type = job.job_type
        job_snapshot = job

    handler = handlers.get(job_type)
    try:
        if handler is None:
            raise LookupError(f"no job handler registered for job_type={job_type!r}")
        await handler(job_snapshot)
    except Exception as exc:
        async with session_scope(settings) as session:
            await JobRepository(session).fail(job_id, error=str(exc))
        return True

    async with session_scope(settings) as session:
        await JobRepository(session).complete(job_id)
    return True


async def run_worker_loop(
    *,
    worker_id: str,
    handlers: Mapping[str, JobHandler],
    poll_interval_s: float = 1.0,
    settings: Settings | None = None,
    stop_when_idle: bool = False,
) -> None:
    """Run continuously, claiming and executing jobs one at a time.

    ``stop_when_idle=True`` returns as soon as the queue is empty instead of
    polling forever -- used by tests and by a one-shot ``drain`` invocation;
    the default (``False``) is the real long-running worker process.
    """
    while True:
        claimed = await claim_and_run_once(
            worker_id=worker_id, handlers=handlers, settings=settings
        )
        if not claimed:
            if stop_when_idle:
                return
            await asyncio.sleep(poll_interval_s)
