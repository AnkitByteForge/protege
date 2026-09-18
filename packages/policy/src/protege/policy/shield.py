"""The safety shield (roadmap P11 §6; ARCHITECTURE.md §11.2: "The safety
shield (deterministic, overrides the bandit unconditionally)").

    proposed_action
        v
    safety_shield
        v
    final_action

:func:`evaluate_shield` is the **unconditional final gate** every proposed
action passes through before it is ever logged or acted on
(``.engine.decide`` calls it exactly once, always, with no bypass path).
Six independent rules, each its own pure function taking only
``(context, proposed)`` -- roadmap P11 §6: "Implement each shield
constraint independently so it can be property-tested." Ordered by
severity, most urgent first; the **first** rule whose trigger condition
holds wins and the rest are not consulted for that decision (matching
``protege.session.machine``'s own "ordered guard list = priority list"
convention) -- this is what keeps the shield's output single-valued when
more than one condition holds at once (roadmap P11 testing: "Test every
safety rule independently and in combinations").

**Why this can never be bypassed by the rule policy.** ``.engine.decide``
is the only caller of both ``.rules.propose_action`` and this module, and
it always threads the former's return value through the latter before
constructing the persisted ``PolicyDecisionAction`` -- there is no code
path in this package that logs or returns a ``.rules`` proposal directly.
Nothing here can make an FSM transition happen either: this module only
ever returns a member of the 13-action ``PolicyAction`` vocabulary and
never touches ``protege.session.machine``. That statement means two
different things for the two rules it might sound like it covers equally,
and they should not be conflated:

- **TEACH_BACK below 0.35** is genuinely belt-and-braces:
  ``protege.session.machine``'s own READINESS guards independently make
  TEACH_BACK unreachable below 0.35 regardless of what this module
  decides (roadmap P11 §11: "The policy must NEVER be able to bypass a
  forbidden FSM transition") -- rule 1 here narrows the *policy's* action
  space to match what the FSM already refuses; it does not, and could
  not, grant the policy any transition authority the FSM itself does not
  already have.
- **The 25-minute hard cap is not the same kind of case.** P7 does not
  currently enforce that wall-clock threshold anywhere in
  ``machine.py``/``orchestrator.py`` (see ``_check_session_hard_cap``'s
  own docstring for the specifics). Rule 6 here is a **policy-layer
  decision only**: it forces HUMAN_TUTOR once the threshold is reached,
  but this module has no execution authority to stop anything. Actually
  terminating the session, or wiring this rule's output into an FSM
  event, is a **future orchestration-integration concern** -- it is not
  already guaranteed by this module or by P7 today.

Two of the six boundary constants (the 0.35 TEACH_BACK floor and the
25-minute hard cap) are imported from P7's already-locked
``protege.session.constants`` rather than redeclared -- see
``constants.py``'s module docstring for why the other four are P11-owned
instead.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from protege.contracts import PolicyAction
from protege.session.constants import READINESS_LOW_THRESHOLD, SESSION_HARD_CAP_SECONDS

from .constants import (
    SHIELD_HINT_STRUGGLE_SECONDS,
    SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP,
    SHIELD_MAX_LOOPS,
)
from .context import PolicyContext
from .rules import low_readiness_action

__all__ = ["ShieldResult", "evaluate_shield"]


@dataclass(frozen=True)
class ShieldResult:
    """Deterministic metadata for one shield evaluation (roadmap P11 §6:
    "For every override, produce deterministic metadata explaining:
    proposed action, final action, shield rule, override = true/false")."""

    proposed_action: PolicyAction
    final_action: PolicyAction
    shield_overrode: bool
    shield_rule: str | None
    rationale: str


_CheckFn = Callable[[PolicyContext, PolicyAction], tuple[PolicyAction, str, str] | None]


def _check_distress(
    context: PolicyContext, proposed: PolicyAction
) -> tuple[PolicyAction, str, str] | None:
    """Rule 5: architecture §11.2 -- "Always HUMAN_TUTOR on ... a distress signal." """
    if context.distress_signal:
        return (
            PolicyAction.HUMAN_TUTOR,
            "distress",
            "distress_signal is set -- escalate to a human tutor unconditionally",
        )
    return None


def _check_loop_exhaustion(
    context: PolicyContext, proposed: PolicyAction
) -> tuple[PolicyAction, str, str] | None:
    """Rule 4: "Force HUMAN_TUTOR after 3 loops." Triggers at
    ``loop_count >= SHIELD_MAX_LOOPS`` -- exactly 3 loops already forces
    the escalation, not only a 4th (roadmap boundary test)."""
    if context.loop_count >= SHIELD_MAX_LOOPS:
        return (
            PolicyAction.HUMAN_TUTOR,
            "loop_exhaustion",
            f"loop_count={context.loop_count} >= {SHIELD_MAX_LOOPS}",
        )
    return None


def _check_session_hard_cap(
    context: PolicyContext, proposed: PolicyAction
) -> tuple[PolicyAction, str, str] | None:
    """Rule 6: "Never allow the session to exceed the 25-minute hard cap."

    This is a **policy-layer enforcement decision only**: once
    ``session_minutes`` reaches the threshold, the shield forces every
    subsequent proposal to HUMAN_TUTOR, unconditionally, for as long as
    this function keeps being asked. The policy has no dedicated "end
    session" action in the 13-action set, and this module has no
    execution authority of its own -- it returns a value, it does not
    stop anything.

    §28.1's termination logic (the FSM actually ending the session,
    recording ``SessionEndReason.TIME``, and refusing further events) is
    documented in ARCHITECTURE.md but is **not currently wired up** in
    ``protege.session`` (P7): ``SESSION_HARD_CAP_SECONDS`` is declared
    there but nothing in ``machine.py``/``orchestrator.py`` reads it, and
    ``SessionEndReason`` is never constructed outside ``packages/
    contracts``. Driving an actual FSM event/session termination from this
    rule's output remains an **orchestration integration concern** for
    whichever phase wires P11 into a live session loop (P10 or later) --
    until that wiring exists, this rule does not by itself guarantee the
    wall-clock session cannot continue beyond 25 minutes; it only
    guarantees the *policy* never again recommends continuing it.
    Compared in seconds (``session_minutes * 60``) against P7's own
    ``SESSION_HARD_CAP_SECONDS`` to avoid a second, independently-rounded
    25.0-minutes literal for the threshold itself."""
    if context.session_minutes * 60.0 >= SESSION_HARD_CAP_SECONDS:
        return (
            PolicyAction.HUMAN_TUTOR,
            "session_hard_cap",
            f"session_minutes={context.session_minutes} exceeds the "
            f"{SESSION_HARD_CAP_SECONDS / 60.0:.0f}-minute hard cap",
        )
    return None


def _check_teach_back_floor(
    context: PolicyContext, proposed: PolicyAction
) -> tuple[PolicyAction, str, str] | None:
    """Rule 1: "Never allow TEACH_BACK when p_known < 0.35." Strict ``<``:
    ``p_known == 0.35`` is allowed (matches ARCHITECTURE.md §1 / P7's own
    ``READINESS_LOW_THRESHOLD`` guard, ``p_known < 0.35``)."""
    if proposed == PolicyAction.TEACH_BACK and context.p_known < READINESS_LOW_THRESHOLD:
        return (
            low_readiness_action(context),
            "teach_back_below_readiness_floor",
            f"p_known={context.p_known} < {READINESS_LOW_THRESHOLD} -- TEACH_BACK is unreachable",
        )
    return None


def _check_difficulty_up_after_errors(
    context: PolicyContext, proposed: PolicyAction
) -> tuple[PolicyAction, str, str] | None:
    """Rule 2: "Never choose DIFFICULTY_UP after 2 consecutive errors."
    Triggers at ``streak_incorrect >= 2`` -- exactly 2 already forbids it
    (roadmap boundary test)."""
    if (
        proposed == PolicyAction.DIFFICULTY_UP
        and context.streak_incorrect >= SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP
    ):
        return (
            PolicyAction.DIFFICULTY_DOWN,
            "difficulty_up_after_errors",
            f"streak_incorrect={context.streak_incorrect} >= "
            f"{SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP}",
        )
    return None


def _check_struggle_hint_floor(
    context: PolicyContext, proposed: PolicyAction
) -> tuple[PolicyAction, str, str] | None:
    """Rule 3: "Never withhold HINT past 90s of struggle." Only overrides
    when a HINT is not already the proposal -- there is nothing to
    "withhold" if HINT is what was already chosen. Triggers at
    ``struggle_seconds >= 90`` (roadmap boundary test: exactly 90s)."""
    if context.struggle_seconds >= SHIELD_HINT_STRUGGLE_SECONDS and proposed != PolicyAction.HINT:
        return (
            PolicyAction.HINT,
            "struggle_hint_floor",
            f"struggle_seconds={context.struggle_seconds} >= {SHIELD_HINT_STRUGGLE_SECONDS} "
            "and HINT was withheld",
        )
    return None


_ORDERED_SHIELD_CHECKS: tuple[_CheckFn, ...] = (
    _check_distress,
    _check_loop_exhaustion,
    _check_session_hard_cap,
    _check_struggle_hint_floor,
    _check_teach_back_floor,
    _check_difficulty_up_after_errors,
)
"""Priority order, most urgent first.

The three "get a human"/hard-stop rules (distress, loop exhaustion,
session hard cap) come first -- each is strictly the strongest available
intervention and always wins.

``_check_struggle_hint_floor`` is checked *before* the two action-specific
reroute rules (teach-back floor, difficulty-up-after-errors) deliberately,
not merely for convenience: the HINT floor's own wording is just as
unconditional as every other rule ("never withhold HINT past 90s of
struggle"), with no carve-out for "unless some other rule already reroutes
this decision elsewhere." Checking it first closes what would otherwise be
a real bypass -- an adversarial ``proposed=TEACH_BACK`` with both
``p_known < 0.35`` *and* ``struggle_seconds >= 90`` would, under the
opposite order, get corrected by ``_check_teach_back_floor`` to
GUIDED_EXAMPLE/NEW_CONCEPT and never reach the struggle check at all,
silently satisfying rule 1 while violating rule 3. With this order, that
same input is forced to HINT instead -- itself a safe, directly responsive
answer to 90s of visible struggle, and neither TEACH_BACK nor
DIFFICULTY_UP, so rules 1 and 2's own invariants ("final action is never
TEACH_BACK below the floor" / "never DIFFICULTY_UP after 2 errors") still
hold trivially. See ``tests/test_shield.py``'s
``test_no_unsafe_action_survives_the_shield`` for the property test this
ordering exists to satisfy."""


def evaluate_shield(context: PolicyContext, proposed: PolicyAction) -> ShieldResult:
    """Run every shield rule, in priority order, and return the final,
    unconditional result. The first rule whose trigger condition holds
    wins; if none apply, ``proposed`` passes through unchanged.

    Deterministic: identical ``(context, proposed)`` always yields an
    identical :class:`ShieldResult` (roadmap P11 testing: "Same context +
    same state must always produce the same rule decision" -- applies
    equally to the shield stage)."""
    for check in _ORDERED_SHIELD_CHECKS:
        result = check(context, proposed)
        if result is None:
            continue
        final_action, rule_name, rationale = result
        return ShieldResult(
            proposed_action=proposed,
            final_action=final_action,
            shield_overrode=final_action != proposed,
            shield_rule=rule_name,
            rationale=rationale,
        )
    return ShieldResult(
        proposed_action=proposed,
        final_action=proposed,
        shield_overrode=False,
        shield_rule=None,
        rationale="no shield rule applies",
    )
