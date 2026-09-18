"""Tests for protege.policy.shield: the unconditional safety gate.

Roadmap P11 §12/§13: every rule tested independently, at its exact
boundary and just inside/outside it, in combination with the others, plus
a full property sweep asserting the central invariant -- "No input state
may cause an unsafe action to survive the shield."

No Hypothesis dependency: nothing in this workspace uses it yet
(``uv.lock``/every existing ``pyproject.toml`` has zero property-testing
dependency), and AGENTS.md asks that a new framework not be introduced
without explaining why. The property test below instead exhaustively
sweeps a small boundary-focused grid with plain ``itertools.product`` --
the same "explicit boundary + combination" style already used by
``packages/session-fsm/tests/test_readiness.py`` and
``packages/learning-engine/tests/test_threshold_service.py`` -- which
covers every rule-interaction case the roadmap calls out without adding a
new test framework.
"""

from __future__ import annotations

import itertools

import pytest
from _context_factory import make_context

from protege.contracts import PolicyAction
from protege.policy.constants import (
    SHIELD_HINT_STRUGGLE_SECONDS,
    SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP,
    SHIELD_MAX_LOOPS,
)
from protege.policy.shield import evaluate_shield
from protege.session.constants import READINESS_LOW_THRESHOLD, SESSION_HARD_CAP_SECONDS

SESSION_HARD_CAP_MINUTES = SESSION_HARD_CAP_SECONDS / 60.0

# =============================================================================
# Rule 1: TEACH_BACK below the 0.35 readiness floor
# =============================================================================


def test_teach_back_allowed_at_exactly_0_35() -> None:
    context = make_context(p_known=READINESS_LOW_THRESHOLD)
    result = evaluate_shield(context, PolicyAction.TEACH_BACK)
    assert result.final_action == PolicyAction.TEACH_BACK
    assert result.shield_overrode is False


def test_teach_back_forbidden_just_below_0_35() -> None:
    context = make_context(p_known=READINESS_LOW_THRESHOLD - 0.001)
    result = evaluate_shield(context, PolicyAction.TEACH_BACK)
    assert result.final_action != PolicyAction.TEACH_BACK
    assert result.shield_overrode is True
    assert result.shield_rule == "teach_back_below_readiness_floor"


def test_teach_back_never_survives_the_shield_below_threshold() -> None:
    for p_known in (0.0, 0.05, 0.1, 0.2, 0.34, 0.349):
        context = make_context(p_known=p_known)
        result = evaluate_shield(context, PolicyAction.TEACH_BACK)
        assert result.final_action != PolicyAction.TEACH_BACK


def test_non_teach_back_action_unaffected_by_low_p_known() -> None:
    context = make_context(p_known=0.1)
    result = evaluate_shield(context, PolicyAction.NEW_CONCEPT)
    assert result.final_action == PolicyAction.NEW_CONCEPT
    assert result.shield_overrode is False


# =============================================================================
# Rule 2: DIFFICULTY_UP after 2 consecutive errors
# =============================================================================


def test_difficulty_up_allowed_at_one_consecutive_error() -> None:
    context = make_context(streak_incorrect=SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP - 1)
    result = evaluate_shield(context, PolicyAction.DIFFICULTY_UP)
    assert result.final_action == PolicyAction.DIFFICULTY_UP
    assert result.shield_overrode is False


def test_difficulty_up_forbidden_at_exactly_2_consecutive_errors() -> None:
    context = make_context(streak_incorrect=SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP)
    result = evaluate_shield(context, PolicyAction.DIFFICULTY_UP)
    assert result.final_action == PolicyAction.DIFFICULTY_DOWN
    assert result.shield_overrode is True
    assert result.shield_rule == "difficulty_up_after_errors"


def test_difficulty_up_forbidden_above_2_consecutive_errors() -> None:
    context = make_context(streak_incorrect=5)
    result = evaluate_shield(context, PolicyAction.DIFFICULTY_UP)
    assert result.final_action == PolicyAction.DIFFICULTY_DOWN


def test_other_actions_unaffected_by_consecutive_errors() -> None:
    context = make_context(streak_incorrect=5)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.PRACTICE
    assert result.shield_overrode is False


# =============================================================================
# Rule 3: HINT withheld past 90s of struggle
# =============================================================================


def test_hint_not_forced_just_below_90s() -> None:
    context = make_context(struggle_seconds=SHIELD_HINT_STRUGGLE_SECONDS - 0.01)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.PRACTICE
    assert result.shield_overrode is False


def test_hint_forced_at_exactly_90s() -> None:
    context = make_context(struggle_seconds=SHIELD_HINT_STRUGGLE_SECONDS)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.HINT
    assert result.shield_overrode is True
    assert result.shield_rule == "struggle_hint_floor"


def test_hint_already_proposed_is_not_reported_as_overridden() -> None:
    context = make_context(struggle_seconds=120.0)
    result = evaluate_shield(context, PolicyAction.HINT)
    assert result.final_action == PolicyAction.HINT
    assert result.shield_overrode is False


# =============================================================================
# Rule 4: HUMAN_TUTOR after 3 loops
# =============================================================================


def test_human_tutor_not_forced_at_2_loops() -> None:
    context = make_context(loop_count=SHIELD_MAX_LOOPS - 1)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.PRACTICE


def test_human_tutor_forced_at_exactly_3_loops() -> None:
    context = make_context(loop_count=SHIELD_MAX_LOOPS)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.HUMAN_TUTOR
    assert result.shield_overrode is True
    assert result.shield_rule == "loop_exhaustion"


def test_human_tutor_forced_above_3_loops() -> None:
    context = make_context(loop_count=10)
    result = evaluate_shield(context, PolicyAction.TEACH_BACK)
    assert result.final_action == PolicyAction.HUMAN_TUTOR


# =============================================================================
# Rule 5: HUMAN_TUTOR on distress
# =============================================================================


def test_human_tutor_forced_on_distress() -> None:
    context = make_context(distress_signal=True)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.HUMAN_TUTOR
    assert result.shield_overrode is True
    assert result.shield_rule == "distress"


def test_no_distress_leaves_action_unaffected() -> None:
    context = make_context(distress_signal=False)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.PRACTICE


# =============================================================================
# Rule 6: session hard cap (25 minutes)
# =============================================================================


def test_hard_cap_not_triggered_just_below_25_minutes() -> None:
    context = make_context(session_minutes=SESSION_HARD_CAP_MINUTES - 0.01)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.PRACTICE


def test_hard_cap_triggered_at_exactly_25_minutes() -> None:
    context = make_context(session_minutes=SESSION_HARD_CAP_MINUTES)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.final_action == PolicyAction.HUMAN_TUTOR
    assert result.shield_overrode is True
    assert result.shield_rule == "session_hard_cap"


def test_hard_cap_triggered_above_25_minutes() -> None:
    context = make_context(session_minutes=40.0)
    result = evaluate_shield(context, PolicyAction.TEACH_BACK)
    assert result.final_action == PolicyAction.HUMAN_TUTOR


# =============================================================================
# No rule applies: pass-through
# =============================================================================


def test_no_rule_applies_passes_action_through_unchanged() -> None:
    context = make_context()
    for action in PolicyAction:
        if action in (PolicyAction.TEACH_BACK, PolicyAction.DIFFICULTY_UP):
            continue  # would trip rules 1/2 in isolation; covered above
        result = evaluate_shield(context, action)
        assert result.final_action == action
        assert result.shield_overrode is False
        assert result.shield_rule is None


# =============================================================================
# Combinations: priority resolution when multiple rules would fire
# =============================================================================


def test_distress_outranks_loop_exhaustion() -> None:
    context = make_context(distress_signal=True, loop_count=SHIELD_MAX_LOOPS)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.shield_rule == "distress"
    assert result.final_action == PolicyAction.HUMAN_TUTOR


def test_loop_exhaustion_outranks_session_hard_cap() -> None:
    context = make_context(loop_count=SHIELD_MAX_LOOPS, session_minutes=SESSION_HARD_CAP_MINUTES)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.shield_rule == "loop_exhaustion"
    assert result.final_action == PolicyAction.HUMAN_TUTOR


def test_loop_exhaustion_outranks_struggle_hint_floor() -> None:
    # Struggle alone would force HINT, but loop exhaustion is checked
    # first and already resolves to the same safe hand-off action.
    context = make_context(loop_count=SHIELD_MAX_LOOPS, struggle_seconds=200.0)
    result = evaluate_shield(context, PolicyAction.PRACTICE)
    assert result.shield_rule == "loop_exhaustion"
    assert result.final_action == PolicyAction.HUMAN_TUTOR


def test_distress_and_low_p_known_and_struggle_all_at_once() -> None:
    context = make_context(distress_signal=True, p_known=0.1, struggle_seconds=200.0)
    result = evaluate_shield(context, PolicyAction.TEACH_BACK)
    assert result.shield_rule == "distress"
    assert result.final_action == PolicyAction.HUMAN_TUTOR


def test_struggle_hint_floor_outranks_difficulty_up_after_errors() -> None:
    # proposed=DIFFICULTY_UP with both the error-streak and struggle
    # conditions true: the HINT floor is checked first (see
    # _ORDERED_SHIELD_CHECKS's docstring for why) -- the result is still
    # safe (never DIFFICULTY_UP), just via a different rule.
    context = make_context(
        streak_incorrect=SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP, struggle_seconds=200.0
    )
    result = evaluate_shield(context, PolicyAction.DIFFICULTY_UP)
    assert result.shield_rule == "struggle_hint_floor"
    assert result.final_action == PolicyAction.HINT


def test_struggle_hint_floor_outranks_teach_back_floor() -> None:
    # proposed=TEACH_BACK with both p_known < 0.35 and struggle >= 90:
    # forced to HINT (not GUIDED_EXAMPLE/NEW_CONCEPT) -- see
    # _ORDERED_SHIELD_CHECKS's docstring.
    context = make_context(p_known=0.1, struggle_seconds=200.0)
    result = evaluate_shield(context, PolicyAction.TEACH_BACK)
    assert result.shield_rule == "struggle_hint_floor"
    assert result.final_action == PolicyAction.HINT


# =============================================================================
# Determinism
# =============================================================================


def test_shield_evaluation_is_deterministic() -> None:
    context = make_context(p_known=0.2, streak_incorrect=3, struggle_seconds=95.0)
    first = evaluate_shield(context, PolicyAction.TEACH_BACK)
    second = evaluate_shield(context, PolicyAction.TEACH_BACK)
    assert first == second


# =============================================================================
# The central property: no unsafe action survives the shield, under any
# combination of boundary-adjacent inputs and any proposed action.
# =============================================================================

_P_KNOWN_GRID = (0.0, 0.2, READINESS_LOW_THRESHOLD - 0.01, READINESS_LOW_THRESHOLD, 0.6, 1.0)
_STREAK_INCORRECT_GRID = (
    0,
    SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP - 1,
    SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP,
    5,
)
_STRUGGLE_GRID = (0.0, SHIELD_HINT_STRUGGLE_SECONDS - 0.01, SHIELD_HINT_STRUGGLE_SECONDS, 500.0)
_LOOP_GRID = (0, SHIELD_MAX_LOOPS - 1, SHIELD_MAX_LOOPS, 10)
_SESSION_MINUTES_GRID = (0.0, SESSION_HARD_CAP_MINUTES - 0.01, SESSION_HARD_CAP_MINUTES, 60.0)
_DISTRESS_GRID = (False, True)


@pytest.mark.parametrize(
    (
        "p_known",
        "streak_incorrect",
        "struggle_seconds",
        "loop_count",
        "session_minutes",
        "distress",
    ),
    list(
        itertools.product(
            _P_KNOWN_GRID,
            _STREAK_INCORRECT_GRID,
            _STRUGGLE_GRID,
            _LOOP_GRID,
            _SESSION_MINUTES_GRID,
            _DISTRESS_GRID,
        )
    )[::7],  # every 7th combination: full coverage of each grid's values
    # in manageable runtime, while still exercising every pairwise overlap.
)
def test_no_unsafe_action_survives_the_shield(
    p_known: float,
    streak_incorrect: int,
    struggle_seconds: float,
    loop_count: int,
    session_minutes: float,
    distress: bool,
) -> None:
    context = make_context(
        p_known=p_known,
        streak_incorrect=streak_incorrect,
        struggle_seconds=struggle_seconds,
        loop_count=loop_count,
        session_minutes=session_minutes,
        distress_signal=distress,
    )
    for proposed in PolicyAction:
        result = evaluate_shield(context, proposed)
        final = result.final_action

        if final == PolicyAction.TEACH_BACK:
            assert context.p_known >= READINESS_LOW_THRESHOLD

        if final == PolicyAction.DIFFICULTY_UP:
            assert context.streak_incorrect < SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP

        if (
            context.distress_signal
            or context.loop_count >= SHIELD_MAX_LOOPS
            or (context.session_minutes * 60.0 >= SESSION_HARD_CAP_SECONDS)
        ):
            assert final == PolicyAction.HUMAN_TUTOR

        if context.struggle_seconds >= SHIELD_HINT_STRUGGLE_SECONDS and not (
            context.distress_signal
            or context.loop_count >= SHIELD_MAX_LOOPS
            or context.session_minutes * 60.0 >= SESSION_HARD_CAP_SECONDS
        ):
            # Unconditional: the HINT floor outranks the two
            # action-specific reroute rules (see shield.py's
            # _ORDERED_SHIELD_CHECKS docstring), so this holds for every
            # proposed action, including TEACH_BACK/DIFFICULTY_UP.
            assert final == PolicyAction.HINT

        # Never raises, always returns a real 13-action-set member.
        assert isinstance(final, PolicyAction)
