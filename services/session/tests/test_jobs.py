"""P9 exit gates 13-14: a job cannot be claimed by two workers
simultaneously (``SELECT ... FOR UPDATE SKIP LOCKED``), and job
failure/retry semantics work.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from _db_helpers import ensure_p9_schema, run_async, truncate_all_p9_tables

from protege.session_service.db.engine import session_scope
from protege.session_service.db.models import JobRow
from protege.session_service.jobs.worker import claim_and_run_once
from protege.session_service.repositories.jobs import JobRepository


def setup_function() -> None:
    ensure_p9_schema()
    run_async(truncate_all_p9_tables())


def test_enqueue_and_claim_transitions_queued_to_running() -> None:
    async def scenario() -> None:
        async with session_scope() as session:
            job = await JobRepository(session).enqueue(job_type="demo", payload={"n": 1})
            job_id = job.id

        async with session_scope() as session:
            claimed = await JobRepository(session).claim(worker_id="w1")
            assert claimed is not None
            assert claimed.id == job_id
            assert claimed.status == "running"
            assert claimed.attempt_count == 1
            assert claimed.claimed_by == "w1"

        async with session_scope() as session:
            # already claimed -- nothing left to claim
            second = await JobRepository(session).claim(worker_id="w2")
            assert second is None

    run_async(scenario())


def test_two_concurrent_workers_never_claim_the_same_job() -> None:
    """The core SKIP LOCKED guarantee: enqueue N jobs, race two workers
    claiming concurrently, assert the union of what each worker claimed is
    a disjoint partition of all N jobs with no job claimed twice."""

    async def scenario() -> None:
        job_ids: set[str] = set()
        async with session_scope() as session:
            repo = JobRepository(session)
            for i in range(20):
                job = await repo.enqueue(job_type="demo", payload={"n": i})
                job_ids.add(str(job.id))

        async def claim_all(worker_id: str) -> list[str]:
            claimed: list[str] = []
            while True:
                async with session_scope() as session:
                    job = await JobRepository(session).claim(worker_id=worker_id)
                if job is None:
                    return claimed
                claimed.append(str(job.id))

        results = await asyncio.gather(claim_all("worker-a"), claim_all("worker-b"))
        all_claimed = results[0] + results[1]
        assert sorted(all_claimed) == sorted(job_ids)
        assert len(set(all_claimed)) == len(all_claimed)  # no duplicate claim

    run_async(scenario())


def test_job_failure_retries_until_max_attempts_then_terminally_fails() -> None:
    async def scenario() -> None:
        async with session_scope() as session:
            job = await JobRepository(session).enqueue(
                job_type="always_fails", payload={}, max_attempts=2
            )
            job_id = job.id

        async def handler(_job: object) -> None:
            raise RuntimeError("boom")

        # Attempt 1: fails, retried (available_at pushed into the future).
        claimed = await claim_and_run_once(
            worker_id="w1", handlers={"always_fails": handler}, settings=None
        )
        assert claimed is True
        async with session_scope() as session:
            row = await JobRepository(session).get(job_id)
            assert row is not None
            assert row.status == "queued"
            assert row.attempt_count == 1
            assert row.error == "boom"

        # Force it immediately available again for the test (skip the
        # backoff wait) and force a second attempt: exhausts max_attempts=2.
        async with session_scope() as session:
            row = await session.get(JobRow, job_id)
            assert row is not None
            row.available_at = datetime.now(UTC)

        claimed_again = await claim_and_run_once(
            worker_id="w1", handlers={"always_fails": handler}, settings=None
        )
        assert claimed_again is True
        async with session_scope() as session:
            row = await JobRepository(session).get(job_id)
            assert row is not None
            assert row.status == "failed"
            assert row.attempt_count == 2

    run_async(scenario())


def test_stale_running_claim_is_reclaimed_after_a_simulated_worker_crash() -> None:
    """Audit 8: "worker crashes do not permanently lose work." A job whose
    claim (``claimed_at``) is older than the stale-claim timeout is treated
    as abandoned by a dead worker and becomes reclaimable -- otherwise it
    would sit at ``status='running'`` forever, since no claim query ever
    selects a merely-``running`` row again on its own."""

    async def scenario() -> None:
        async with session_scope() as session:
            job = await JobRepository(session).enqueue(job_type="demo", payload={})
            job_id = job.id

        async with session_scope() as session:
            first_claim = await JobRepository(session).claim(worker_id="worker-a")
            assert first_claim is not None
            assert first_claim.attempt_count == 1

        # Simulate "worker-a died mid-job": backdate claimed_at well past
        # any stale-claim window this test will use.
        async with session_scope() as session:
            row = await session.get(JobRow, job_id)
            assert row is not None
            row.claimed_at = datetime.now(UTC) - timedelta(seconds=9999)

        async with session_scope() as session:
            # Too short a window: nothing looks stale yet relative to "now"
            # if the backdate above were smaller -- but 9999s comfortably
            # exceeds even a generous 60s test window either way.
            reclaimed = await JobRepository(session).claim(worker_id="worker-b", stale_after_s=60.0)
            assert reclaimed is not None
            assert reclaimed.id == job_id
            assert reclaimed.status == "running"
            assert reclaimed.claimed_by == "worker-b"
            assert reclaimed.attempt_count == 2  # incremented again, same as any retry

    run_async(scenario())


def test_stale_running_claim_at_max_attempts_terminally_fails_instead_of_looping() -> None:
    async def scenario() -> None:
        async with session_scope() as session:
            job = await JobRepository(session).enqueue(job_type="demo", payload={}, max_attempts=1)
            job_id = job.id

        async with session_scope() as session:
            first_claim = await JobRepository(session).claim(worker_id="worker-a")
            assert first_claim is not None
            assert first_claim.attempt_count == 1  # already at max_attempts=1

        async with session_scope() as session:
            row = await session.get(JobRow, job_id)
            assert row is not None
            row.claimed_at = datetime.now(UTC) - timedelta(seconds=9999)

        async with session_scope() as session:
            result = await JobRepository(session).claim(worker_id="worker-b", stale_after_s=60.0)
            assert result is None  # not reclaimed for execution

        async with session_scope() as session:
            row = await JobRepository(session).get(job_id)
            assert row is not None
            assert row.status == "failed"
            assert row.finished_at is not None

    run_async(scenario())


def test_job_success_marks_succeeded() -> None:
    async def scenario() -> None:
        async with session_scope() as session:
            job = await JobRepository(session).enqueue(job_type="always_succeeds", payload={})
            job_id = job.id

        async def handler(_job: object) -> None:
            return None

        claimed = await claim_and_run_once(
            worker_id="w1", handlers={"always_succeeds": handler}, settings=None
        )
        assert claimed is True
        async with session_scope() as session:
            row = await JobRepository(session).get(job_id)
            assert row is not None
            assert row.status == "succeeded"
            assert row.finished_at is not None

    run_async(scenario())
