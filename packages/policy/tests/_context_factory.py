"""Shared ``PolicyContext`` factory for the P11 test suite.

Leading underscore (not ``conftest.py``) matching ``packages/session-fsm/
tests/_golden_trace_fixtures.py`` and ``packages/thin-thread/tests/
_helpers.py``'s own precedent: no test directory in this monorepo uses
``__init__.py`` packages, so a second literal ``conftest.py`` name would
collide across directories under pytest's flat module cache.
"""

from __future__ import annotations

from protege.policy import PolicyContext


def make_context(**overrides: object) -> PolicyContext:
    """A valid, mid-band default context; override only the fields a test
    cares about."""
    base: dict[str, object] = {
        "p_known": 0.5,
        "max_misconception_belief": 0.0,
        "n_active_misconceptions": 0,
        "hints_requested_this_skill": 0,
        "mean_latency_z": 0.0,
        "streak_correct": 0,
        "streak_incorrect": 0,
        "session_minutes": 1.0,
        "items_this_skill": 1,
        "confidence_mean": 0.5,
        "calibration_error": 0.0,
        "prior_teachback_success": 0.0,
        "time_since_last_review_days": 0.0,
        "grade_band": "3-4",
        "struggle_seconds": 0.0,
        "loop_count": 0,
        "distress_signal": False,
    }
    base.update(overrides)
    return PolicyContext(**base)  # type: ignore[arg-type]
