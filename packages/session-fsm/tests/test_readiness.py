"""READINESS choice-node property tests (roadmap P7 exact spec; Testing:
"Property test: TEACH_BACK is unreachable when p_known < 0.35").
"""

from __future__ import annotations

import random

import pytest

from protege.session.constants import (
    MAX_READINESS_LOOPS,
    READINESS_HIGH_THRESHOLD,
    READINESS_LOW_THRESHOLD,
)
from protege.session.machine import TRANSITIONS, Event, S, SessionContext, step


def _fire_explanation_captured(p_known: float, loops: int = 0) -> S:
    context = SessionContext(current=S.EXPLANATION, p_known=p_known, loops=loops)
    return step(context, Event.EXPLANATION_CAPTURED)


# --- TEACH_BACK unreachable when p_known < 0.35 -----------------------------


def test_structurally_only_sprout_setup_states_lead_fresh_into_teach_back() -> None:
    """The *only* way to freshly enter TEACH_BACK from outside the
    teach-back subsystem is via SPROUT_SETUP or SPROUT_SETUP_HARD -- both
    only reachable (per the READINESS guard list) when p_known >= 0.35.
    TEACH_BACK's own self-loop and COACH_ASSIST's return edge are
    internal to that subsystem, not a fresh entry, and are excluded here
    by construction (not merely by an allow-list)."""
    sources_of_teach_back = {
        state
        for (state, _event), transitions in TRANSITIONS.items()
        for t in transitions
        if t.to == S.TEACH_BACK and state not in {S.TEACH_BACK, S.COACH_ASSIST}
    }
    assert sources_of_teach_back == {S.SPROUT_SETUP, S.SPROUT_SETUP_HARD}


@pytest.mark.parametrize("loops", [0, 1])
def test_readiness_never_enters_sprout_setup_when_p_known_below_threshold(loops: int) -> None:
    rng = random.Random(20260918)
    for _ in range(500):
        p_known = rng.uniform(0.0, READINESS_LOW_THRESHOLD - 1e-9)
        result = _fire_explanation_captured(p_known, loops=loops)
        assert result != S.SPROUT_SETUP
        assert result != S.SPROUT_SETUP_HARD
        assert result == S.GUIDED_LEARNING


def test_readiness_never_enters_sprout_setup_at_the_exact_boundary_from_below() -> None:
    result = _fire_explanation_captured(READINESS_LOW_THRESHOLD - 1e-12, loops=0)
    assert result == S.GUIDED_LEARNING


def test_full_session_can_never_reach_teach_back_while_p_known_stays_below_threshold() -> None:
    """End-to-end: drive the full recovery cycle (EXPLANATION ->
    GUIDED_LEARNING -> PRACTICE -> EXPLANATION) repeatedly with a
    below-threshold p_known until escalation, and confirm TEACH_BACK (and
    its two gateway states) never appear anywhere in the visited
    sequence."""
    context = SessionContext(current=S.EXPLANATION, p_known=0.10)
    visited: list[S] = [context.current]
    while context.current != S.ESCALATE_TO_HUMAN:
        if context.current == S.EXPLANATION:
            visited.append(step(context, Event.EXPLANATION_CAPTURED))
        elif context.current == S.GUIDED_LEARNING:
            visited.append(step(context, Event.WORKED_EXAMPLE_COMPLETE))
        elif context.current == S.PRACTICE:
            context.items_attempted = 4
            context.consecutive_errors = 0
            visited.append(step(context, Event.ITEM_SCORED))
        else:  # pragma: no cover - defensive; would indicate a bug above
            raise AssertionError(f"unexpected state in recovery cycle: {context.current}")
    assert S.TEACH_BACK not in visited
    assert S.SPROUT_SETUP not in visited
    assert S.SPROUT_SETUP_HARD not in visited
    assert visited.count(S.GUIDED_LEARNING) == MAX_READINESS_LOOPS


# --- READINESS band routing (roadmap P7 exact spec) -------------------------


def test_readiness_teach_back_band_is_inclusive_of_both_endpoints() -> None:
    assert _fire_explanation_captured(READINESS_LOW_THRESHOLD) == S.SPROUT_SETUP
    assert _fire_explanation_captured(READINESS_HIGH_THRESHOLD) == S.SPROUT_SETUP


def test_readiness_routes_mid_band_to_sprout_setup() -> None:
    rng = random.Random(20260918)
    for _ in range(500):
        p_known = rng.uniform(READINESS_LOW_THRESHOLD, READINESS_HIGH_THRESHOLD)
        assert _fire_explanation_captured(p_known) == S.SPROUT_SETUP


def test_readiness_routes_above_high_threshold_to_hard_variant() -> None:
    rng = random.Random(20260918)
    for _ in range(500):
        p_known = rng.uniform(READINESS_HIGH_THRESHOLD + 1e-9, 1.0)
        assert _fire_explanation_captured(p_known) == S.SPROUT_SETUP_HARD


# --- Escalation at 3 loops ---------------------------------------------------


def test_escalates_on_exactly_the_third_low_p_known_encounter() -> None:
    """ARCHITECTURE.md: "max 2 loops... 3rd failure -> ESCALATE_TO_HUMAN".
    See constants.MAX_READINESS_LOOPS's docstring for how this reconciles
    with roadmap P7's "escalation at 3 loops" phrasing."""
    context = SessionContext(current=S.EXPLANATION, p_known=0.10)
    first = step(context, Event.EXPLANATION_CAPTURED)
    assert first == S.GUIDED_LEARNING
    assert context.loops == 1

    context.current = S.EXPLANATION
    second = step(context, Event.EXPLANATION_CAPTURED)
    assert second == S.GUIDED_LEARNING
    assert context.loops == 2

    context.current = S.EXPLANATION
    third = step(context, Event.EXPLANATION_CAPTURED)
    assert third == S.ESCALATE_TO_HUMAN


def test_escalation_guard_outranks_the_low_p_known_guard() -> None:
    """A learner who is both out of loops AND below 0.35 must escalate,
    not take a further loop-back -- the ordered guard list checks
    loop-exhaustion first."""
    context = SessionContext(current=S.EXPLANATION, p_known=0.05, loops=MAX_READINESS_LOOPS)
    assert step(context, Event.EXPLANATION_CAPTURED) == S.ESCALATE_TO_HUMAN


def test_independent_verify_failure_uses_the_same_loop_counter_as_readiness() -> None:
    """INDEPENDENT_VERIFY's "under 2 of 3" -> GUIDED_LEARNING path feeds
    the identical `loops` counter READINESS checks -- so a learner who
    fails verification twice, then fails READINESS once more, still
    escalates on their third overall recovery attempt rather than being
    granted extra unlimited verify-failure loops."""
    context = SessionContext(current=S.INDEPENDENT_VERIFY, verify_correct_count=0)
    assert step(context, Event.VERIFY_ITEMS_SCORED) == S.GUIDED_LEARNING
    assert context.loops == 1

    context.current = S.INDEPENDENT_VERIFY
    context.verify_correct_count = 0
    assert step(context, Event.VERIFY_ITEMS_SCORED) == S.GUIDED_LEARNING
    assert context.loops == 2

    context.current = S.EXPLANATION
    context.p_known = 0.05
    assert step(context, Event.EXPLANATION_CAPTURED) == S.ESCALATE_TO_HUMAN
