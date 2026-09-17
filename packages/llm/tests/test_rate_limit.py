"""Tests for the 35 RPM token-bucket rate limiter.

Deterministic tests drive a fake clock/sleep pair so nothing here waits on
real wall-clock time. `sleep` on the fake clock always advances the fake
`now` by the requested amount, matching how `time.sleep` really behaves —
this is the only sound way to fake this pairing (a frozen clock with a
no-op sleep would spin forever, since nothing ever un-starves the bucket).
"""

import threading

import pytest

from protege.llm.rate_limit import RateLimitTimeout, TokenBucket


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, dt: float) -> None:
        self.now += dt


def test_rejects_non_positive_rate() -> None:
    with pytest.raises(ValueError):
        TokenBucket(0.0)


def test_try_acquire_allows_burst_up_to_capacity() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60.0, capacity=5, clock=clock, sleep=clock.advance)
    for _ in range(5):
        assert bucket.try_acquire()
    assert not bucket.try_acquire()


def test_try_acquire_refills_over_simulated_time() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60.0, capacity=1, clock=clock, sleep=clock.advance)  # 1/sec
    assert bucket.try_acquire()
    assert not bucket.try_acquire()
    clock.advance(1.0)
    assert bucket.try_acquire()


def test_try_acquire_does_not_exceed_capacity_even_after_long_idle() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60.0, capacity=3, clock=clock, sleep=clock.advance)
    for _ in range(3):
        bucket.try_acquire()
    clock.advance(1000.0)  # far more than enough to overfill without the cap
    successes = sum(bucket.try_acquire() for _ in range(10))
    assert successes == 3


def test_acquire_blocks_via_injected_sleep_then_succeeds() -> None:
    clock = FakeClock()
    bucket = TokenBucket(60.0, capacity=1, clock=clock, sleep=clock.advance)
    bucket.acquire()  # consumes the only token
    bucket.acquire(timeout_s=5.0)  # "waits" via the fake sleep and succeeds


def test_acquire_raises_rate_limit_timeout_when_starved() -> None:
    clock = FakeClock()
    bucket = TokenBucket(1.0, capacity=1, clock=clock, sleep=clock.advance)  # 1/min refill
    bucket.try_acquire()  # consume the only token
    with pytest.raises(RateLimitTimeout):
        bucket.acquire(timeout_s=0.5)  # far less than the ~60s refill period


def test_concurrent_try_acquire_never_exceeds_capacity() -> None:
    """The 35 RPM ceiling under concurrent load: no more than `capacity`
    callers may succeed even when many race simultaneously. The refill rate
    is set near zero so thread-scheduling jitter during the burst cannot
    add a stray token and flake the assertion — this test is about the
    thread-safety of the capacity cap, not the refill rate."""
    bucket = TokenBucket(rate_per_minute=0.001, capacity=35.0)
    results: list[bool] = []
    lock = threading.Lock()

    def worker() -> None:
        ok = bucket.try_acquire()
        with lock:
            results.append(ok)

    threads = [threading.Thread(target=worker) for _ in range(200)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert sum(results) <= 35
    assert len(results) == 200
