"""20 scripted golden-trace sessions (roadmap P7 Testing: "Golden traces: 20
scripted sessions replayed with assertion of identical state sequences").

Each :class:`GoldenTrace` is a session script: an ordered list of
``(event, context field updates applied first)`` steps. ``run_trace``
starts a fresh :class:`~protege.session.machine.SessionContext` at
``ARRIVAL`` and calls :func:`~protege.session.machine.step` once per
:class:`ScriptStep`, applying that step's context updates immediately
before the call -- exactly modelling what an orchestrator does when it has
already decided (from real role/validator output, outside this module's
concern) which event to fire and what the observed signals were.

Deliberately exercises :func:`~protege.session.machine.step` directly
rather than :class:`~protege.session.orchestrator.SessionOrchestrator`:
these traces are a golden record of the **pure FSM's** state sequence,
independent of any dwell-counter bookkeeping convention the orchestrator
layer happens to use.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from protege.session.machine import Event, S, SessionContext, step


@dataclass(frozen=True)
class ScriptStep:
    event: Event
    updates: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GoldenTrace:
    name: str
    steps: tuple[ScriptStep, ...]
    expected_states: tuple[S, ...]
    """``(ARRIVAL, *one entry per step, in order)`` -- the golden record."""


def run_trace(steps: tuple[ScriptStep, ...]) -> tuple[S, ...]:
    context = SessionContext()
    sequence: list[S] = [context.current]
    for s in steps:
        for key, value in s.updates.items():
            setattr(context, key, value)
        sequence.append(step(context, s.event))
    return tuple(sequence)


# --- Shared step fragments ---------------------------------------------------

_ARRIVE_AND_TEASE = (
    ScriptStep(Event.PROFILE_LOADED),
    ScriptStep(Event.TEASE_ELAPSED),
)


def _diagnostic_to_practice_via_discovery(p_known: float) -> tuple[ScriptStep, ...]:
    """DIAGNOSTIC (low prior) -> DISCOVERY -> GUIDED_LEARNING -> PRACTICE."""
    return (
        ScriptStep(Event.PRIORS_SET, {"p_known": p_known}),
        ScriptStep(Event.EXPLORATION_DONE),
        ScriptStep(Event.WORKED_EXAMPLE_COMPLETE),
    )


_PRACTICE_EXIT_FULL_ATTEMPT = ScriptStep(
    Event.ITEM_SCORED, {"items_attempted": 4, "consecutive_errors": 0}
)


def _to_explanation(p_known_at_diagnostic: float = 0.5) -> tuple[ScriptStep, ...]:
    """Full ARRIVAL -> EXPLANATION prefix via the normal (non-skip) path."""
    return (
        *_ARRIVE_AND_TEASE,
        *_diagnostic_to_practice_via_discovery(p_known_at_diagnostic),
        _PRACTICE_EXIT_FULL_ATTEMPT,
    )


_TO_SUMMARY_AND_COMPLETE = (
    ScriptStep(Event.ARTIFACTS_PERSISTED),
    ScriptStep(Event.SCHEDULE_COMPUTED),
)


# =============================================================================
# The 20 golden traces
# =============================================================================

TRACES: list[GoldenTrace] = []


def _register(name: str, steps: tuple[ScriptStep, ...], expected: tuple[S, ...]) -> None:
    """Pins ``expected`` as a literal, independent of ``run_trace`` --
    the golden record a future regression in ``TRANSITIONS`` must be
    caught against, not a value recomputed from the same code under
    test. Each literal below was produced by one verified run of
    ``run_trace(steps)`` and hand-checked against the guard/effect logic
    in ``protege.session.machine`` before being pinned here."""
    TRACES.append(GoldenTrace(name=name, steps=steps, expected_states=expected))


# 1. Full 3-loop READINESS recovery cascade -> escalation -> session close.
_register(
    "readiness_recovery_escalates_at_three_loops",
    (
        *_to_explanation(),
        ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.10}),  # loops 0->1 -> GUIDED_LEARNING
        ScriptStep(Event.WORKED_EXAMPLE_COMPLETE),
        _PRACTICE_EXIT_FULL_ATTEMPT,
        ScriptStep(Event.EXPLANATION_CAPTURED),  # loops 1 -> 2, -> GUIDED_LEARNING
        ScriptStep(Event.WORKED_EXAMPLE_COMPLETE),
        _PRACTICE_EXIT_FULL_ATTEMPT,
        ScriptStep(Event.EXPLANATION_CAPTURED),  # 3rd encounter, loops == 2 -> ESCALATE_TO_HUMAN
        ScriptStep(Event.ESCALATION_ACKNOWLEDGED),
        *_TO_SUMMARY_AND_COMPLETE,
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.ESCALATE_TO_HUMAN,
        S.SUMMARY,
        S.RETRIEVAL_SCHEDULE,
        S.COMPLETE,
    ),
)

# 2. Teach-back band, resolves turn 1, full verify pass, transfer attempted,
#    positive mastery delta -> REWARD.
_register(
    "readiness_teach_back_band_full_happy_path_with_reward",
    (
        *_to_explanation(),
        ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.50}),  # -> SPROUT_SETUP
        ScriptStep(Event.MISCONCEPTION_SELECTED),
        ScriptStep(Event.TURN_COMPLETED, {"misconception_resolved": True}),  # -> REFLECTION
        ScriptStep(Event.REFLECTION_CAPTURED),
        ScriptStep(Event.VERIFY_ITEMS_SCORED, {"verify_correct_count": 3}),  # -> TRANSFER
        ScriptStep(Event.TRANSFER_ATTEMPTED),  # -> MASTERY_DECISION
        ScriptStep(Event.MASTERY_COMPUTED, {"mastery_delta": 0.4}),  # -> REWARD
        ScriptStep(Event.REWARD_PROCESSED),
        *_TO_SUMMARY_AND_COMPLETE,
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP,
        S.TEACH_BACK,
        S.REFLECTION,
        S.INDEPENDENT_VERIFY,
        S.TRANSFER,
        S.MASTERY_DECISION,
        S.REWARD,
        S.SUMMARY,
        S.RETRIEVAL_SCHEDULE,
        S.COMPLETE,
    ),
)

# 3. Hard variant, caps out unresolved, fails verify (recovery loop), then
#    resolves + passes verify but skips transfer -> no reward.
_register(
    "readiness_hard_variant_recovers_after_verify_failure",
    (
        *_to_explanation(),
        ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.95}),  # -> SPROUT_SETUP_HARD
        ScriptStep(Event.MISCONCEPTION_SELECTED),
        ScriptStep(Event.TURN_COMPLETED, {"teach_back_turns": 6}),  # cap -> REFLECTION
        ScriptStep(Event.REFLECTION_CAPTURED),
        ScriptStep(Event.VERIFY_ITEMS_SCORED, {"verify_correct_count": 1}),  # under 2/3 -> loop
        ScriptStep(Event.WORKED_EXAMPLE_COMPLETE),
        _PRACTICE_EXIT_FULL_ATTEMPT,
        ScriptStep(Event.EXPLANATION_CAPTURED),  # loops==1, p_known 0.95 -> SPROUT_SETUP_HARD
        ScriptStep(Event.MISCONCEPTION_SELECTED),
        ScriptStep(Event.TURN_COMPLETED, {"misconception_resolved": True}),  # -> REFLECTION
        ScriptStep(Event.REFLECTION_CAPTURED),
        ScriptStep(Event.VERIFY_ITEMS_SCORED, {"verify_correct_count": 3}),  # -> TRANSFER
        ScriptStep(Event.TIMEOUT),  # TRANSFER timeout -> MASTERY_DECISION, unattempted
        ScriptStep(Event.MASTERY_COMPUTED, {"mastery_delta": 0.0}),  # -> SUMMARY
        *_TO_SUMMARY_AND_COMPLETE,
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP_HARD,
        S.TEACH_BACK,
        S.REFLECTION,
        S.INDEPENDENT_VERIFY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP_HARD,
        S.TEACH_BACK,
        S.REFLECTION,
        S.INDEPENDENT_VERIFY,
        S.TRANSFER,
        S.MASTERY_DECISION,
        S.SUMMARY,
        S.RETRIEVAL_SCHEDULE,
        S.COMPLETE,
    ),
)

# 4-7. READINESS boundary sweep at the exact 0.35 / 0.80 breakpoints.
_register(
    "readiness_boundary_exactly_0_35_goes_teach_back",
    (*_to_explanation(), ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.35})),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP,
    ),
)
_register(
    "readiness_boundary_exactly_0_80_goes_teach_back",
    (*_to_explanation(), ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.80})),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP,
    ),
)
_register(
    "readiness_boundary_just_above_0_80_goes_hard_variant",
    (*_to_explanation(), ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.800001})),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP_HARD,
    ),
)
_register(
    "readiness_boundary_just_below_0_35_goes_recovery",
    (*_to_explanation(), ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.349999})),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.GUIDED_LEARNING,
    ),
)

# 8. DIAGNOSTIC high-prior skip straight to PRACTICE.
_register(
    "diagnostic_high_prior_skips_to_practice",
    (*_ARRIVE_AND_TEASE, ScriptStep(Event.PRIORS_SET, {"p_known": 0.85})),
    (S.ARRIVAL, S.SPROUT_TEASE, S.DIAGNOSTIC, S.PRACTICE),
)

# 9-10. DIAGNOSTIC timeout / failure both default to DISCOVERY.
_register(
    "diagnostic_timeout_defaults_to_discovery",
    (*_ARRIVE_AND_TEASE, ScriptStep(Event.TIMEOUT)),
    (S.ARRIVAL, S.SPROUT_TEASE, S.DIAGNOSTIC, S.DISCOVERY),
)
_register(
    "diagnostic_failure_defaults_to_discovery",
    (*_ARRIVE_AND_TEASE, ScriptStep(Event.FAILURE)),
    (S.ARRIVAL, S.SPROUT_TEASE, S.DIAGNOSTIC, S.DISCOVERY),
)

# 11. SPROUT_TEASE timeout skips straight to DIAGNOSTIC.
_register(
    "sprout_tease_timeout_skips_to_diagnostic",
    (ScriptStep(Event.PROFILE_LOADED), ScriptStep(Event.TIMEOUT)),
    (S.ARRIVAL, S.SPROUT_TEASE, S.DIAGNOSTIC),
)

# 12. PRACTICE: 3 consecutive errors routes back to GUIDED_LEARNING.
_register(
    "practice_three_consecutive_errors_returns_to_guided_learning",
    (
        *_ARRIVE_AND_TEASE,
        *_diagnostic_to_practice_via_discovery(0.5),
        ScriptStep(Event.ITEM_SCORED, {"items_attempted": 3, "consecutive_errors": 3}),
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.GUIDED_LEARNING,
    ),
)

# 13. PRACTICE timeout advances with partial evidence, no error/attempt gate.
_register(
    "practice_timeout_advances_with_partial_evidence",
    (*_ARRIVE_AND_TEASE, *_diagnostic_to_practice_via_discovery(0.5), ScriptStep(Event.TIMEOUT)),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
    ),
)

# 14. TEACH_BACK: child stuck 2 turns -> COACH_ASSIST -> hint -> resolves.
_register(
    "teach_back_stuck_child_routes_through_coach_assist_then_resolves",
    (
        *_to_explanation(),
        ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.50}),
        ScriptStep(Event.MISCONCEPTION_SELECTED),
        ScriptStep(Event.TURN_COMPLETED, {"stuck_turns": 2}),  # -> COACH_ASSIST
        ScriptStep(Event.HINT_DELIVERED),  # -> TEACH_BACK, stuck_turns reset
        ScriptStep(Event.TURN_COMPLETED, {"misconception_resolved": True}),  # -> REFLECTION
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP,
        S.TEACH_BACK,
        S.COACH_ASSIST,
        S.TEACH_BACK,
        S.REFLECTION,
    ),
)

# 15. TEACH_BACK idle timeout abandons the session outright.
_register(
    "teach_back_idle_timeout_abandons_session",
    (
        *_to_explanation(),
        ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.50}),
        ScriptStep(Event.MISCONCEPTION_SELECTED),
        ScriptStep(Event.IDLE_TIMEOUT),
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP,
        S.TEACH_BACK,
        S.ABANDONED,
    ),
)

# 16. ARRIVAL idle timeout abandons before the session ever really starts.
_register(
    "arrival_idle_timeout_abandons_session",
    (ScriptStep(Event.IDLE_TIMEOUT),),
    (S.ARRIVAL, S.ABANDONED),
)

# 17. DISCOVERY timeout advances straight to GUIDED_LEARNING.
_register(
    "discovery_timeout_advances_to_guided_learning",
    (*_ARRIVE_AND_TEASE, ScriptStep(Event.PRIORS_SET, {"p_known": 0.2}), ScriptStep(Event.TIMEOUT)),
    (S.ARRIVAL, S.SPROUT_TEASE, S.DIAGNOSTIC, S.DISCOVERY, S.GUIDED_LEARNING),
)

# 18. GUIDED_LEARNING failure still advances to PRACTICE (authored fallback).
_register(
    "guided_learning_failure_advances_with_authored_fallback",
    (
        *_ARRIVE_AND_TEASE,
        ScriptStep(Event.PRIORS_SET, {"p_known": 0.2}),
        ScriptStep(Event.EXPLORATION_DONE),
        ScriptStep(Event.FAILURE),
    ),
    (S.ARRIVAL, S.SPROUT_TEASE, S.DIAGNOSTIC, S.DISCOVERY, S.GUIDED_LEARNING, S.PRACTICE),
)

# 19. REFLECTION is skippable: timeout advances to INDEPENDENT_VERIFY.
_register(
    "reflection_timeout_skips_to_independent_verify",
    (
        *_to_explanation(),
        ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.50}),
        ScriptStep(Event.MISCONCEPTION_SELECTED),
        ScriptStep(Event.TURN_COMPLETED, {"misconception_resolved": True}),
        ScriptStep(Event.TIMEOUT),
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP,
        S.TEACH_BACK,
        S.REFLECTION,
        S.INDEPENDENT_VERIFY,
    ),
)

# 20. TRANSFER timeout records the probe as unattempted and MASTERY_DECISION
#     sees no delta -> no reward.
_register(
    "transfer_timeout_records_unattempted_and_no_reward",
    (
        *_to_explanation(),
        ScriptStep(Event.EXPLANATION_CAPTURED, {"p_known": 0.50}),
        ScriptStep(Event.MISCONCEPTION_SELECTED),
        ScriptStep(Event.TURN_COMPLETED, {"misconception_resolved": True}),
        ScriptStep(Event.REFLECTION_CAPTURED),
        ScriptStep(Event.VERIFY_ITEMS_SCORED, {"verify_correct_count": 2}),
        ScriptStep(Event.TIMEOUT),  # TRANSFER timeout, transfer_attempted stays False
        ScriptStep(Event.MASTERY_COMPUTED, {"mastery_delta": 0.0}),
    ),
    (
        S.ARRIVAL,
        S.SPROUT_TEASE,
        S.DIAGNOSTIC,
        S.DISCOVERY,
        S.GUIDED_LEARNING,
        S.PRACTICE,
        S.EXPLANATION,
        S.SPROUT_SETUP,
        S.TEACH_BACK,
        S.REFLECTION,
        S.INDEPENDENT_VERIFY,
        S.TRANSFER,
        S.MASTERY_DECISION,
        S.SUMMARY,
    ),
)


assert len(TRACES) == 20, f"expected exactly 20 golden traces, got {len(TRACES)}"
assert len({t.name for t in TRACES}) == 20, "golden trace names must be unique"
