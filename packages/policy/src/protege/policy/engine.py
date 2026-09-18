"""The P11 policy engine's single entry point: :func:`decide`.

    context
      -> build_state_vector           (.context)
      -> propose_action                (.rules)  \\_ source="rules"
      -> counterfactual_choice         (.rules)  /   (logged only, .rules'
      -> evaluate_shield(proposed)     (.shield)      own docstring)
      -> final_action = shield.final_action
      -> [optional] select_item_by_target_elo  (.item_selection)
      -> compute_reward                (.reward)
      -> PolicyDecision                (protege.contracts, ready for
                                         services.session.repositories.
                                         policy.PolicyRepository.append)

This is the *only* function in this package that assembles a full
``PolicyDecision`` -- every other module stays independently callable and
independently testable (roadmap P11: "Separate: context/state
construction, rule-based action selection, safety shield, shield override
explanation, counterfactual choice/logging, reward calculation,
trajectory/policy decision persistence"). :func:`decide` performs no I/O
itself; persistence is the caller's job, exactly as P9's own
``PolicyRepository`` docstring states ("P9 makes no policy decisions") --
symmetrically, P11 makes no persistence calls.

**The shield is never optional here.** There is no parameter, flag, or
code path that returns ``propose_action``'s output without first passing
it through :func:`~protege.policy.shield.evaluate_shield` -- see
``shield.py``'s own docstring for why that makes the shield unconditional
by construction, not by convention.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from protege.contracts import (
    EloRating,
    JSONValue,
    LearningItem,
    PolicyAction,
    PolicyDecision,
    PolicyDecisionAction,
)

from .context import PolicyContext, build_state_vector
from .item_selection import select_item_by_target_elo
from .reward import RewardComponents, compute_reward
from .rules import counterfactual_choice, propose_action
from .shield import evaluate_shield

__all__ = ["ITEM_SERVING_ACTIONS", "decide"]

ITEM_SERVING_ACTIONS: frozenset[PolicyAction] = frozenset(
    {
        PolicyAction.PRACTICE,
        PolicyAction.DIFFICULTY_UP,
        PolicyAction.DIFFICULTY_DOWN,
        PolicyAction.TRANSFER,
        PolicyAction.REVIEW,
        PolicyAction.RETRIEVAL,
    }
)
"""The subset of the 13-action set that needs a concrete next item, as
opposed to a Sprout/teach-back/human hand-off action (SPROUT_SETUP already
selects the misconception; TEACH_BACK/HUMAN_TUTOR/HINT/ANALOGY need no new
item; NEW_CONCEPT/GUIDED_EXAMPLE/VISUALIZATION are worked-example driven,
not a scored item)."""


def decide(
    *,
    trajectory_id: str,
    step: int,
    context: PolicyContext,
    observation: Mapping[str, JSONValue] | None = None,
    reward_components: RewardComponents | None = None,
    item_candidates: Sequence[LearningItem] | None = None,
    learner_elo_rating: EloRating | None = None,
    next_state_ref: str | None = None,
) -> PolicyDecision:
    """Decide, shield, and package one complete, replayable trajectory
    step (roadmap P11 exit criterion: "Every decision produces a
    complete, replayable trajectory row").

    ``item_candidates``/``learner_elo_rating`` are both optional and only
    consulted when the shielded final action is one of
    :data:`ITEM_SERVING_ACTIONS` -- omitting them (e.g. for a TEACH_BACK
    or HUMAN_TUTOR decision, where no item selection applies) is not an
    error.
    """
    proposed = propose_action(context)
    counterfactual = counterfactual_choice(context)
    shield_result = evaluate_shield(context, proposed)
    final_action = shield_result.final_action

    params: dict[str, JSONValue] = {}
    if shield_result.shield_rule is not None:
        params["shield_rule"] = shield_result.shield_rule
        params["shield_rationale"] = shield_result.rationale

    if final_action in ITEM_SERVING_ACTIONS and item_candidates and learner_elo_rating is not None:
        selection = select_item_by_target_elo(item_candidates, learner_elo_rating)
        params["item_id"] = str(selection.item.item_id)
        params["target_elo"] = selection.target_rating
        params["predicted_success"] = selection.predicted_success

    action = PolicyDecisionAction(
        type=final_action,
        params=params,
        source="rules",
        shield_overrode=shield_result.shield_overrode,
        counterfactual_bandit_choice=counterfactual,
    )

    resolved_reward_components = (
        reward_components
        if reward_components is not None
        else RewardComponents(session_minutes=context.session_minutes)
    )
    reward = compute_reward(resolved_reward_components)

    return PolicyDecision(
        trajectory_id=trajectory_id,
        step=step,
        state=build_state_vector(context),
        action=action,
        observation=dict(observation) if observation is not None else {},
        reward=reward,
        next_state_ref=next_state_ref,
    )
