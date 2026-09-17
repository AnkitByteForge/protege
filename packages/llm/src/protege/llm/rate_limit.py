"""Global token-bucket rate limiter (addendum §2.3: 35 RPM, headroom below
NVIDIA's 40 RPM cap; addendum §9 point 7: "requests wait rather than fail").
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable


class RateLimitTimeout(Exception):
    """``acquire`` waited longer than ``timeout_s`` for a slot."""


class TokenBucket:
    """Thread-safe token bucket.

    Refills continuously at ``rate_per_minute``, capped at ``capacity``.
    ``acquire()`` blocks until a token is available or ``timeout_s`` elapses;
    ``try_acquire()`` never blocks.

    The clock and sleep functions are injectable so tests can drive the
    bucket deterministically without real wall-clock waits — see
    ``tests/test_rate_limit.py``.
    """

    def __init__(
        self,
        rate_per_minute: float = 35.0,
        capacity: float | None = None,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be positive")
        self._rate_per_second = rate_per_minute / 60.0
        self._capacity = capacity if capacity is not None else rate_per_minute
        self._clock = clock
        self._sleep = sleep
        self._tokens = self._capacity
        self._last_refill = clock()
        self._lock = threading.Lock()

    def _refill_locked(self) -> None:
        now = self._clock()
        elapsed = max(0.0, now - self._last_refill)
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate_per_second)
        self._last_refill = now

    def try_acquire(self) -> bool:
        """Non-blocking. Returns ``True`` and consumes one token iff one is available."""
        with self._lock:
            self._refill_locked()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def acquire(self, timeout_s: float = 30.0) -> None:
        """Block until a token is available.

        Raises ``RateLimitTimeout`` if none becomes available within
        ``timeout_s``.
        """
        deadline = self._clock() + timeout_s
        while True:
            if self.try_acquire():
                return
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise RateLimitTimeout(f"no token available within {timeout_s}s")
            with self._lock:
                self._refill_locked()
                needed = max(0.0, 1.0 - self._tokens)
            wait_for_refill = needed / self._rate_per_second if needed > 0 else 0.05
            self._sleep(max(0.001, min(remaining, wait_for_refill)))
