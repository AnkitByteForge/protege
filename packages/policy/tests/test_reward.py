"""Tests for protege.policy.reward: the un-gameable §11.2 reward formula.

Explicitly tests the zero time-on-task coefficient (roadmap P11 testing:
"Explicitly test the zero coefficient: time_on_task coefficient == 0").
"""

from __future__ import annotations

import pytest

from protege.policy.constants import (
    HINT_DEPENDENCY_COEFFICIENT,
    MASTERY_DELTA_COEFFICIENT,
    RETENTION_COEFFICIENT,
    SESSION_OVERAGE_COEFFICIENT,
    SESSION_OVERAGE_MINUTES,
    TIME_ON_TASK_COEFFICIENT,
    TRANSFER_SUCCESS_COEFFICIENT,
)
from protege.policy.reward import RETENTION_DEFERRED_KEY, RewardComponents, compute_reward


def test_time_on_task_coefficient_is_exactly_zero() -> None:
    assert TIME_ON_TASK_COEFFICIENT == 0.0


def test_time_on_task_never_changes_the_reward() -> None:
    low = compute_reward(RewardComponents(time_on_task_seconds=0.0))
    high = compute_reward(RewardComponents(time_on_task_seconds=100_000.0))
    assert low.immediate == high.immediate


def test_empty_components_yield_zero_immediate_and_deferred_retention() -> None:
    reward = compute_reward(RewardComponents())
    assert reward.immediate == 0.0
    assert reward.deferred_pending == [RETENTION_DEFERRED_KEY]


def test_mastery_delta_scales_by_its_coefficient() -> None:
    reward = compute_reward(RewardComponents(mastery_delta_verified=0.2))
    assert reward.immediate == pytest.approx(MASTERY_DELTA_COEFFICIENT * 0.2)


def test_transfer_success_true_adds_its_coefficient() -> None:
    reward = compute_reward(RewardComponents(transfer_success=True))
    assert reward.immediate == pytest.approx(TRANSFER_SUCCESS_COEFFICIENT)


def test_transfer_success_false_adds_nothing() -> None:
    reward = compute_reward(RewardComponents(transfer_success=False))
    assert reward.immediate == 0.0


def test_transfer_not_attempted_adds_nothing_and_is_distinct_from_failure() -> None:
    not_attempted = compute_reward(RewardComponents(transfer_success=None))
    failed = compute_reward(RewardComponents(transfer_success=False))
    assert not_attempted.immediate == failed.immediate == 0.0


def test_retention_known_adds_its_coefficient_and_is_not_deferred() -> None:
    reward = compute_reward(RewardComponents(next_session_retention=0.5))
    assert reward.immediate == pytest.approx(RETENTION_COEFFICIENT * 0.5)
    assert reward.deferred_pending == []


def test_retention_unknown_is_deferred_and_contributes_nothing() -> None:
    reward = compute_reward(RewardComponents(next_session_retention=None))
    assert reward.immediate == 0.0
    assert reward.deferred_pending == [RETENTION_DEFERRED_KEY]


def test_hint_dependency_increase_is_penalized() -> None:
    reward = compute_reward(RewardComponents(hint_dependency_increase=0.5))
    assert reward.immediate == pytest.approx(-HINT_DEPENDENCY_COEFFICIENT * 0.5)


def test_session_overage_penalty_triggers_just_above_20_minutes() -> None:
    reward = compute_reward(RewardComponents(session_minutes=SESSION_OVERAGE_MINUTES + 0.01))
    assert reward.immediate == pytest.approx(-SESSION_OVERAGE_COEFFICIENT)


def test_session_overage_penalty_does_not_trigger_at_exactly_20_minutes() -> None:
    reward = compute_reward(RewardComponents(session_minutes=SESSION_OVERAGE_MINUTES))
    assert reward.immediate == 0.0


def test_session_overage_penalty_does_not_trigger_below_20_minutes() -> None:
    reward = compute_reward(RewardComponents(session_minutes=10.0))
    assert reward.immediate == 0.0


def test_all_components_combine_additively() -> None:
    reward = compute_reward(
        RewardComponents(
            mastery_delta_verified=0.1,
            transfer_success=True,
            hint_dependency_increase=0.2,
            session_minutes=25.0,
            next_session_retention=0.4,
            time_on_task_seconds=999.0,
        )
    )
    expected = (
        MASTERY_DELTA_COEFFICIENT * 0.1
        + TRANSFER_SUCCESS_COEFFICIENT * 1.0
        + RETENTION_COEFFICIENT * 0.4
        - HINT_DEPENDENCY_COEFFICIENT * 0.2
        - SESSION_OVERAGE_COEFFICIENT * 1.0
    )
    assert reward.immediate == pytest.approx(expected)
    assert reward.deferred_pending == []


def test_compute_reward_is_deterministic() -> None:
    components = RewardComponents(mastery_delta_verified=0.3, session_minutes=5.0)
    assert compute_reward(components) == compute_reward(components)


def test_reward_never_rewards_engagement_signals_directly() -> None:
    # RewardComponents has no field for clicks, streaks, or return rate at
    # all -- there is nothing to accidentally reward. time_on_task_seconds
    # is the one engagement-shaped field, and it is proven inert above.
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(RewardComponents)}
    assert "clicks" not in field_names
    assert "streak" not in field_names
    assert "return_rate" not in field_names
