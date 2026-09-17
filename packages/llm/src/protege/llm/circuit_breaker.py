"""Per-``(provider, model_id)`` circuit breaker (addendum §2.4, §2.8: opens
after 3 consecutive failures).
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class _BreakerState:
    consecutive_failures: int = 0
    opened_at: float | None = None


class CircuitBreaker:
    """Opens a ``(provider, model_id)`` key after ``failure_threshold``
    consecutive failures.

    While open, ``is_open`` returns ``True`` for ``cooldown_s``. After the
    cooldown, the breaker half-opens: the next check reports closed so the
    router lets exactly one trial call through — the caller reports that
    trial's outcome via ``record_success``/``record_failure``, which either
    closes the breaker or reopens it with a fresh cooldown.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        cooldown_s: float = 30.0,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_s = cooldown_s
        self._clock = clock
        self._lock = threading.Lock()
        self._state: dict[tuple[str, str], _BreakerState] = {}

    def is_open(self, provider: str, model_id: str) -> bool:
        with self._lock:
            state = self._state.get((provider, model_id))
            if state is None or state.opened_at is None:
                return False
            return (self._clock() - state.opened_at) < self._cooldown_s

    def record_success(self, provider: str, model_id: str) -> None:
        with self._lock:
            self._state[(provider, model_id)] = _BreakerState()

    def record_failure(self, provider: str, model_id: str) -> None:
        with self._lock:
            state = self._state.setdefault((provider, model_id), _BreakerState())
            state.consecutive_failures += 1
            if state.consecutive_failures >= self._failure_threshold:
                state.opened_at = self._clock()
