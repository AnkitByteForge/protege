"""Golden-trace tests (roadmap P7 Testing: "Golden traces: 20 scripted
sessions replayed with assertion of identical state sequences"; exit
criterion: "golden traces deterministic across 10 runs").
"""

from __future__ import annotations

import pytest
from _golden_trace_fixtures import TRACES, GoldenTrace, run_trace


@pytest.mark.parametrize("trace", TRACES, ids=[t.name for t in TRACES])
def test_golden_trace_matches_pinned_sequence(trace: GoldenTrace) -> None:
    assert run_trace(trace.steps) == trace.expected_states


@pytest.mark.parametrize("trace", TRACES, ids=[t.name for t in TRACES])
def test_golden_trace_is_deterministic_across_ten_runs(trace: GoldenTrace) -> None:
    """Exit criterion: "golden traces deterministic across 10 runs" --
    each run starts a brand-new SessionContext, so this also proves no
    hidden shared/global state leaks between runs (e.g. the reused
    ``_READINESS_TRANSITIONS`` list in ``protege.session.machine`` is
    read-only, never mutated by a run)."""
    for _ in range(10):
        assert run_trace(trace.steps) == trace.expected_states


def test_exactly_twenty_golden_traces_with_unique_names() -> None:
    assert len(TRACES) == 20
    assert len({t.name for t in TRACES}) == 20
