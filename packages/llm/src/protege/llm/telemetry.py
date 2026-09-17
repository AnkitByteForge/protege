"""``model_runs`` telemetry record (addendum §2.7, §9 point 9).

This is the runtime record *shape* only — P9 owns the actual table and
migration; P4 produces records in this shape so the future persistence layer
has nothing to invent.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol

from .errors import FallbackReason
from .structured import StructuredMode


@dataclass(frozen=True)
class ModelRunRecord:
    """One ``model_runs`` row (addendum §2.7).

    ``attempt_index`` counts attempts *within* one fallback-chain entry's
    structured-output tiering (0 = first attempt, 1 = the single repair
    attempt) — moving to the next chain entry starts a new record at
    ``attempt_index`` 0. This attribution is a documented implementation
    choice: no source document specifies the counting scheme.

    ``credits_estimated`` uses the addendum §2.3 heuristic ("~1 credit per
    call"): 1.0 for a completed provider call, 0.0 for a cache hit or a
    deterministic-fallback record (no network spent). Also a documented
    assumption — no document specifies a finer cost model.
    """

    provider: str
    endpoint_base_url: str
    model_id: str
    role: str
    prompt_version: str
    attempt_index: int
    fallback_reason: FallbackReason | None
    structured_mode: StructuredMode
    tokens_in: int
    tokens_out: int
    latency_ms: int
    trace_id: str | None
    credits_estimated: float
    cache_hit: bool = False
    recorded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    """Wall-clock UTC timestamp of this call — a real point in time,
    matching the repository's ``datetime``/``timestamptz`` convention
    (e.g. ``learning_state.py``'s ``created_at``/``computed_at``,
    ``session.py``'s ``occurred_at``) so a future P9 persistence layer can
    store it directly. Not ``time.monotonic()``: that clock has an
    arbitrary, process-relative epoch and cannot answer "when did this
    happen" across a process restart, which is exactly what this field
    must answer for cost/latency dashboards (ARCHITECTURE.md §25/§26)."""


class TelemetrySink(Protocol):
    """Where ``ModelRouter`` sends completed ``ModelRunRecord``s.

    P9 will provide a Postgres-backed implementation; tests and the eval
    harness (roadmap P24) use ``InMemoryTelemetrySink``.
    """

    def record(self, run: ModelRunRecord) -> None: ...


class InMemoryTelemetrySink:
    """Default sink: an in-process, thread-safe list."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.runs: list[ModelRunRecord] = []

    def record(self, run: ModelRunRecord) -> None:
        with self._lock:
            self.runs.append(run)

    def __len__(self) -> int:
        return len(self.runs)
