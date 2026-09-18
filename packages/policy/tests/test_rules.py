"""Tests for protege.policy.rules: deterministic pacing.

One test per branch (task instruction), plus determinism and
counterfactual-never-becomes-the-action checks.
"""

from __future__ import annotations

from _context_factory import make_context

from protege.contracts import PolicyAction
from protege.policy.rules import counterfactual_choice, propose_action, rank_actions


def test_below_readiness_with_misconception_proposes_guided_example() -> None:
    context = make_context(p_known=0.2, n_active_misconceptions=1)
    assert propose_action(context) == PolicyAction.GUIDED_EXAMPLE


def test_below_readiness_without_misconception_proposes_new_concept() -> None:
    context = make_context(p_known=0.2, n_active_misconceptions=0)
    assert propose_action(context) == PolicyAction.NEW_CONCEPT


def test_in_band_with_misconception_and_streak_proposes_teach_back() -> None:
    context = make_context(p_known=0.5, n_active_misconceptions=1, streak_correct=1)
    assert propose_action(context) == PolicyAction.TEACH_BACK


def test_in_band_with_misconception_no_streak_proposes_practice() -> None:
    context = make_context(p_known=0.5, n_active_misconceptions=1, streak_correct=0)
    assert propose_action(context) == PolicyAction.PRACTICE


def test_in_band_no_misconception_strong_streak_proposes_visualization() -> None:
    context = make_context(p_known=0.5, n_active_misconceptions=0, streak_correct=3)
    assert propose_action(context) == PolicyAction.VISUALIZATION


def test_in_band_no_misconception_weak_streak_proposes_practice() -> None:
    context = make_context(p_known=0.5, n_active_misconceptions=0, streak_correct=1)
    assert propose_action(context) == PolicyAction.PRACTICE


def test_above_readiness_strong_streak_proposes_difficulty_up() -> None:
    context = make_context(p_known=0.9, streak_correct=3)
    assert propose_action(context) == PolicyAction.DIFFICULTY_UP


def test_above_readiness_no_misconception_some_streak_proposes_transfer() -> None:
    context = make_context(p_known=0.9, n_active_misconceptions=0, streak_correct=1)
    assert propose_action(context) == PolicyAction.TRANSFER


def test_above_readiness_default_proposes_review() -> None:
    context = make_context(p_known=0.9, n_active_misconceptions=1, streak_correct=0)
    assert propose_action(context) == PolicyAction.REVIEW


def test_distress_outranks_everything() -> None:
    context = make_context(p_known=0.9, streak_correct=3, distress_signal=True)
    assert propose_action(context) == PolicyAction.HUMAN_TUTOR


def test_loop_exhaustion_proposes_human_tutor() -> None:
    context = make_context(loop_count=3)
    assert propose_action(context) == PolicyAction.HUMAN_TUTOR


def test_struggle_at_shield_floor_proposes_hint() -> None:
    context = make_context(struggle_seconds=90.0)
    assert propose_action(context) == PolicyAction.HINT


def test_two_consecutive_errors_proposes_difficulty_down() -> None:
    context = make_context(p_known=0.9, streak_correct=3, streak_incorrect=2)
    assert propose_action(context) == PolicyAction.DIFFICULTY_DOWN


def test_retrieval_due_outranks_mastery_band() -> None:
    context = make_context(p_known=0.6, time_since_last_review_days=5.0)
    assert propose_action(context) == PolicyAction.RETRIEVAL


def test_moderate_struggle_with_misconception_proposes_analogy() -> None:
    context = make_context(p_known=0.5, n_active_misconceptions=1, struggle_seconds=60.0)
    assert propose_action(context) == PolicyAction.ANALOGY


def test_rank_actions_never_empty() -> None:
    for p_known in (0.0, 0.1, 0.35, 0.5, 0.8, 0.81, 1.0):
        context = make_context(p_known=p_known)
        assert len(rank_actions(context)) >= 1


def test_counterfactual_is_none_when_only_one_rule_matches() -> None:
    # In-band, no misconception, weak streak, no overlay rule triggered:
    # only _rule_in_readiness_band matches.
    context = make_context(p_known=0.5)
    assert len(rank_actions(context)) == 1
    assert counterfactual_choice(context) is None


def test_counterfactual_differs_from_proposal_when_two_rules_match() -> None:
    context = make_context(p_known=0.9, streak_correct=3, streak_incorrect=2)
    proposed = propose_action(context)
    counterfactual = counterfactual_choice(context)
    assert counterfactual is not None
    assert counterfactual != proposed


def test_counterfactual_never_influences_propose_action() -> None:
    context = make_context(p_known=0.9, streak_correct=3, streak_incorrect=2)
    proposed_before = propose_action(context)
    counterfactual_choice(context)
    proposed_after = propose_action(context)
    assert proposed_before == proposed_after


def test_propose_action_is_deterministic() -> None:
    context = make_context(p_known=0.62, n_active_misconceptions=1, streak_correct=2)
    assert propose_action(context) == propose_action(context)
    assert rank_actions(context) == rank_actions(context)
