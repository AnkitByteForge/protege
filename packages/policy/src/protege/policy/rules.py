"""Deterministic rule-based pacing (roadmap P11 §5; ARCHITECTURE.md §11.2
"rules + a shielded contextual bandit" -- the "rules" half).

Every rule here is a small, independent, pure predicate over
:class:`~protege.policy.context.PolicyContext` -- no LLM call, no I/O, no
randomness, no clock read (the caller supplies elapsed time as a plain
float, exactly ``protege.session.machine``'s guard functions do for P7).
Same input always produces the same output (roadmap P11 testing:
"determinism").

**This module never talks to the safety shield.** It proposes a
pedagogically reasonable action from the raw signals alone; :mod:`.shield`
is a separate, unconditional final gate applied *after* this module runs
(roadmap P11 §6: "The shield must be impossible for the rule policy to
bypass"). Several rules below (distress, loop exhaustion, the error-streak
DIFFICULTY_DOWN redirect) happen to already propose the same safe action
the shield would force -- that overlap is intentional (a sensible pacing
policy shouldn't need the shield to catch its every decision), but it is
not load-bearing: the shield re-checks every one of its own rules from
scratch against whatever action ends up here, including a context
deliberately constructed to make this module propose something unsafe (see
``tests/test_shield.py``).

:func:`rank_actions` returns every rule's match, in priority order, not
just the winner -- :func:`propose_action` is ``rank_actions(...)[0]``,
:func:`counterfactual_choice` is the entry at index 1 if one exists
(roadmap P11 §8: the counterfactual is a second, *logged-only* candidate,
never a second policy -- see the module's own contract in
``counterfactual_choice``'s docstring).
"""

from __future__ import annotations

from collections.abc import Callable

from protege.contracts import PolicyAction
from protege.session.constants import READINESS_HIGH_THRESHOLD, READINESS_LOW_THRESHOLD

from .constants import (
    RULES_ANALOGY_STRUGGLE_SECONDS,
    RULES_DIFFICULTY_UP_STREAK_CORRECT,
    RULES_RETRIEVAL_MIN_P_KNOWN,
    RULES_RETRIEVAL_REVIEW_DAYS,
    RULES_TEACH_BACK_MIN_STREAK_CORRECT,
    RULES_TRANSFER_MIN_STREAK_CORRECT,
    RULES_VISUALIZATION_STREAK_CORRECT,
    SHIELD_HINT_STRUGGLE_SECONDS,
    SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP,
    SHIELD_MAX_LOOPS,
)
from .context import PolicyContext

__all__ = [
    "counterfactual_choice",
    "low_readiness_action",
    "propose_action",
    "rank_actions",
]

_RuleFn = Callable[[PolicyContext], PolicyAction | None]


def low_readiness_action(context: PolicyContext) -> PolicyAction:
    """The pedagogically appropriate action below the 0.35 readiness floor:
    re-teach through the already-implicated misconception if one is
    tracked, else start from a fresh concept. Public (not a private rule
    function) because :mod:`.shield` reuses it verbatim as the safe
    replacement whenever it must reroute a forbidden TEACH_BACK -- a single
    source of truth for "what does this learner need instead," rather than
    the shield inventing a second answer to the same question."""
    if context.n_active_misconceptions > 0:
        return PolicyAction.GUIDED_EXAMPLE
    return PolicyAction.NEW_CONCEPT


def _rule_distress(context: PolicyContext) -> PolicyAction | None:
    return PolicyAction.HUMAN_TUTOR if context.distress_signal else None


def _rule_loop_exhaustion(context: PolicyContext) -> PolicyAction | None:
    return PolicyAction.HUMAN_TUTOR if context.loop_count >= SHIELD_MAX_LOOPS else None


def _rule_struggle_hint(context: PolicyContext) -> PolicyAction | None:
    return PolicyAction.HINT if context.struggle_seconds >= SHIELD_HINT_STRUGGLE_SECONDS else None


def _rule_error_streak_difficulty_down(context: PolicyContext) -> PolicyAction | None:
    if context.streak_incorrect >= SHIELD_MAX_CONSECUTIVE_ERRORS_FOR_DIFFICULTY_UP:
        return PolicyAction.DIFFICULTY_DOWN
    return None


def _rule_retrieval_due(context: PolicyContext) -> PolicyAction | None:
    if (
        context.time_since_last_review_days >= RULES_RETRIEVAL_REVIEW_DAYS
        and context.p_known >= RULES_RETRIEVAL_MIN_P_KNOWN
    ):
        return PolicyAction.RETRIEVAL
    return None


def _rule_struggle_analogy(context: PolicyContext) -> PolicyAction | None:
    if (
        context.struggle_seconds >= RULES_ANALOGY_STRUGGLE_SECONDS
        and context.n_active_misconceptions > 0
    ):
        return PolicyAction.ANALOGY
    return None


def _rule_below_readiness(context: PolicyContext) -> PolicyAction | None:
    if context.p_known < READINESS_LOW_THRESHOLD:
        return low_readiness_action(context)
    return None


def _rule_in_readiness_band(context: PolicyContext) -> PolicyAction | None:
    if not (READINESS_LOW_THRESHOLD <= context.p_known <= READINESS_HIGH_THRESHOLD):
        return None
    if (
        context.n_active_misconceptions > 0
        and context.streak_correct >= RULES_TEACH_BACK_MIN_STREAK_CORRECT
    ):
        return PolicyAction.TEACH_BACK
    if context.n_active_misconceptions > 0:
        return PolicyAction.PRACTICE
    if context.streak_correct >= RULES_VISUALIZATION_STREAK_CORRECT:
        return PolicyAction.VISUALIZATION
    return PolicyAction.PRACTICE


def _rule_above_readiness(context: PolicyContext) -> PolicyAction | None:
    if context.p_known <= READINESS_HIGH_THRESHOLD:
        return None
    if context.streak_correct >= RULES_DIFFICULTY_UP_STREAK_CORRECT:
        return PolicyAction.DIFFICULTY_UP
    if context.n_active_misconceptions == 0 and context.streak_correct >= (
        RULES_TRANSFER_MIN_STREAK_CORRECT
    ):
        return PolicyAction.TRANSFER
    return PolicyAction.REVIEW


_ORDERED_RULES: tuple[_RuleFn, ...] = (
    _rule_distress,
    _rule_loop_exhaustion,
    _rule_struggle_hint,
    _rule_error_streak_difficulty_down,
    _rule_retrieval_due,
    _rule_struggle_analogy,
    _rule_below_readiness,
    _rule_in_readiness_band,
    _rule_above_readiness,
)
"""Priority order, highest first. The last three (``_rule_below_readiness``,
``_rule_in_readiness_band``, ``_rule_above_readiness``) partition the full
``p_known`` domain ``[0, 1]`` and each *always* returns an action for its
band, so ``rank_actions`` below is never empty."""


def rank_actions(context: PolicyContext) -> list[PolicyAction]:
    """Every rule's match, in priority order -- the full ranked candidate
    list this module can produce for one context. Never empty: the three
    mastery-band rules jointly cover every possible ``p_known`` value."""
    return [action for rule in _ORDERED_RULES if (action := rule(context)) is not None]


def propose_action(context: PolicyContext) -> PolicyAction:
    """The rules' top choice -- ``source="rules"`` in the persisted
    decision (roadmap P11 §8). This is a *proposal*: :mod:`.engine` always
    passes it through :func:`protege.policy.shield.evaluate_shield` before
    it becomes the final logged action."""
    return rank_actions(context)[0]


def counterfactual_choice(context: PolicyContext) -> PolicyAction | None:
    """The second-ranked candidate, logged only (``counterfactual_bandit_
    choice`` on ``PolicyDecisionAction``) -- **never** consulted by
    :func:`propose_action`, :mod:`.shield`, or :mod:`.engine`'s final
    action (roadmap P11 §8: "The counterfactual choice is LOGGED ONLY. It
    must NOT act as the policy."). ``None`` when only one rule matched (no
    second candidate exists for this context) -- matching
    ``PolicyDecisionAction.counterfactual_bandit_choice``'s optional type.

    This is explicitly *not* a bandit (roadmap P11 §8: "Do not implement an
    actual learning bandit in P11. That belongs to P32"): it never learns
    from outcomes, never updates weights, and carries no state between
    calls. It exists only so a future offline policy-evaluation pass (P32,
    gated on P24) has a second, equally deterministic candidate action to
    compare the real trajectory against.
    """
    ranked = rank_actions(context)
    return ranked[1] if len(ranked) > 1 else None
