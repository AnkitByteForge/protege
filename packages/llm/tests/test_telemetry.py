"""Tests for `ModelRunRecord` and the in-memory telemetry sink."""

from datetime import UTC as _UTC
from datetime import datetime, timedelta

from protege.llm.errors import FallbackReason
from protege.llm.structured import StructuredMode
from protege.llm.telemetry import InMemoryTelemetrySink, ModelRunRecord


def _record(**overrides: object) -> ModelRunRecord:
    defaults: dict[str, object] = {
        "provider": "nvidia",
        "endpoint_base_url": "https://integrate.api.nvidia.com/v1",
        "model_id": "m1",
        "role": "SPROUT",
        "prompt_version": "v1",
        "attempt_index": 0,
        "fallback_reason": None,
        "structured_mode": StructuredMode.NATIVE,
        "tokens_in": 1,
        "tokens_out": 1,
        "latency_ms": 1,
        "trace_id": "t1",
        "credits_estimated": 1.0,
    }
    defaults.update(overrides)
    return ModelRunRecord(**defaults)  # type: ignore[arg-type]


def test_recorded_at_is_a_real_wall_clock_utc_timestamp() -> None:
    """P1-4 regression: `recorded_at` must be an actual point in time
    (timezone-aware UTC), not a `time.monotonic()` value — a monotonic
    clock has an arbitrary, process-relative epoch and cannot be stored as
    a real timestamp by a future P9 `timestamptz` column."""
    before = datetime.now(_UTC)
    run = _record()
    after = datetime.now(_UTC)

    assert isinstance(run.recorded_at, datetime)
    assert run.recorded_at.tzinfo is not None  # timezone-aware, matching timestamptz
    assert before - timedelta(seconds=1) <= run.recorded_at <= after + timedelta(seconds=1)


def test_recorded_at_reflects_real_elapsed_wall_clock_time() -> None:
    """Two records created moments apart must have `recorded_at` values
    that agree with real wall-clock elapsed time — the property a
    monotonic-clock value cannot provide across a process restart, and
    which this test would fail to demonstrate meaningfully with one."""
    import time

    first = _record()
    time.sleep(0.01)
    second = _record()
    assert second.recorded_at > first.recorded_at
    assert (second.recorded_at - first.recorded_at) < timedelta(seconds=5)


def test_in_memory_sink_records_in_order() -> None:
    sink = InMemoryTelemetrySink()
    sink.record(_record(attempt_index=0))
    sink.record(_record(attempt_index=1, fallback_reason=FallbackReason.SCHEMA))
    assert len(sink) == 2
    assert [r.attempt_index for r in sink.runs] == [0, 1]


def test_model_run_record_never_carries_prompt_or_response_text() -> None:
    """Telemetry must stay metadata-only — no field on `ModelRunRecord`
    is capable of carrying raw prompt/response text, a child's words, or
    a secret, by construction (there is no such field to populate)."""
    run = _record()
    field_names = set(run.__dataclass_fields__)
    assert field_names == {
        "provider",
        "endpoint_base_url",
        "model_id",
        "role",
        "prompt_version",
        "attempt_index",
        "fallback_reason",
        "structured_mode",
        "tokens_in",
        "tokens_out",
        "latency_ms",
        "trace_id",
        "credits_estimated",
        "cache_hit",
        "recorded_at",
    }
