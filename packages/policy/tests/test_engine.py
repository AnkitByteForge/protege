"""Tests for protege.policy.engine.decide: the full pipeline, end to end."""

from __future__ import annotations

from _context_factory import make_context

from protege.contracts import LearningItem, PolicyAction, PolicyDecision
from protege.policy.engine import decide
from protege.policy.item_selection import target_item_rating
from protege.policy.reward import RewardComponents
from protege.policy.rules import propose_action


def test_decide_returns_a_valid_policy_decision() -> None:
    context = make_context(p_known=0.5)
    result = decide(trajectory_id="traj_test_1", step=1, context=context)
    assert isinstance(result, PolicyDecision)
    assert result.trajectory_id == "traj_test_1"
    assert result.step == 1
    assert len(result.state.vector) == 14


def test_decide_source_is_always_rules() -> None:
    context = make_context()
    result = decide(trajectory_id="t", step=1, context=context)
    assert result.action.source == "rules"


def test_decide_shield_cannot_be_bypassed() -> None:
    # A context that would make the rules propose TEACH_BACK below the
    # readiness floor if the shield were skipped.
    context = make_context(p_known=0.1, n_active_misconceptions=1, streak_correct=5)
    result = decide(trajectory_id="t", step=1, context=context)
    assert result.action.type != PolicyAction.TEACH_BACK


def test_decide_records_shield_override_metadata() -> None:
    # Rules has no session-clock rule of its own (only the shield enforces
    # the hard cap), so this context makes rules propose ordinary PRACTICE
    # pacing while the shield forces HUMAN_TUTOR -- a genuine end-to-end
    # override, unlike the distress/loop cases where rules already agrees
    # with the shield (see .rules's module docstring).
    context = make_context(p_known=0.5, session_minutes=40.0)
    result = decide(trajectory_id="t", step=1, context=context)
    assert result.action.type == PolicyAction.HUMAN_TUTOR
    assert result.action.shield_overrode is True
    assert result.action.params["shield_rule"] == "session_hard_cap"


def test_decide_reports_shield_rule_even_when_rules_already_agrees() -> None:
    # Distress: rules.py already proposes HUMAN_TUTOR on its own, so the
    # shield's check is a no-op (shield_overrode is False) -- but the rule
    # name is still reported, since the constraint was checked and held.
    context = make_context(distress_signal=True)
    result = decide(trajectory_id="t", step=1, context=context)
    assert result.action.type == PolicyAction.HUMAN_TUTOR
    assert result.action.shield_overrode is False
    assert result.action.params["shield_rule"] == "distress"


def test_decide_no_override_leaves_params_without_shield_rule() -> None:
    context = make_context(p_known=0.5)
    result = decide(trajectory_id="t", step=1, context=context)
    assert result.action.shield_overrode is False
    assert "shield_rule" not in result.action.params


def test_decide_counterfactual_is_logged_but_not_the_action() -> None:
    context = make_context(p_known=0.9, streak_correct=3, streak_incorrect=2)
    result = decide(trajectory_id="t", step=1, context=context)
    assert result.action.counterfactual_bandit_choice is not None
    assert result.action.counterfactual_bandit_choice != result.action.type


def test_decide_is_deterministic() -> None:
    context = make_context(p_known=0.62, n_active_misconceptions=1, streak_correct=2)
    first = decide(trajectory_id="t", step=1, context=context)
    second = decide(trajectory_id="t", step=1, context=context)
    assert first == second


def test_decide_selects_an_item_for_practice_actions() -> None:
    context = make_context(p_known=0.5, n_active_misconceptions=0, streak_correct=0)
    assert propose_action(context) == PolicyAction.PRACTICE
    target = target_item_rating(1200, target_success=0.75)
    candidates = [
        LearningItem(
            id="close", stem="s", representation="symbolic", correct_answer="1/2", elo=target
        ),
        LearningItem(
            id="far", stem="s", representation="symbolic", correct_answer="1/2", elo=target + 900
        ),
    ]
    result = decide(
        trajectory_id="t",
        step=1,
        context=context,
        item_candidates=candidates,
        learner_elo_rating=1200,
    )
    assert result.action.type == PolicyAction.PRACTICE
    assert result.action.params["item_id"] == "close"


def test_decide_does_not_select_an_item_for_non_item_serving_actions() -> None:
    context = make_context(distress_signal=True)
    candidates = [
        LearningItem(id="x", stem="s", representation="symbolic", correct_answer="1/2", elo=1200)
    ]
    result = decide(
        trajectory_id="t",
        step=1,
        context=context,
        item_candidates=candidates,
        learner_elo_rating=1200,
    )
    assert result.action.type == PolicyAction.HUMAN_TUTOR
    assert "item_id" not in result.action.params


def test_decide_default_reward_defers_retention() -> None:
    context = make_context()
    result = decide(trajectory_id="t", step=1, context=context)
    assert result.reward.deferred_pending == ["retention_d7"]


def test_decide_accepts_explicit_reward_components() -> None:
    context = make_context()
    result = decide(
        trajectory_id="t",
        step=1,
        context=context,
        reward_components=RewardComponents(mastery_delta_verified=0.3),
    )
    assert result.reward.immediate == 0.3


def test_decide_passes_through_observation_and_next_state_ref() -> None:
    context = make_context()
    result = decide(
        trajectory_id="t",
        step=3,
        context=context,
        observation={"resolved": True, "turns": 4},
        next_state_ref="traj_x:4",
    )
    assert result.observation == {"resolved": True, "turns": 4}
    assert result.next_state_ref == "traj_x:4"
