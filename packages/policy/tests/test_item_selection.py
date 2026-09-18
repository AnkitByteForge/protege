"""Tests for protege.policy.item_selection: Elo-targeted item choice.

Reuses protege.learning_engine.mastery_engine.elo_expected_score --
verified directly rather than re-deriving the Elo formula in this test
file.
"""

from __future__ import annotations

import pytest

from protege.contracts import LearningItem
from protege.learning_engine import elo_expected_score
from protege.learning_engine.constants import MAX_ELO_RATING, MIN_ELO_RATING
from protege.policy.item_selection import select_item_by_target_elo, target_item_rating


def _item(item_id: str, elo: int | None) -> LearningItem:
    return LearningItem(
        id=item_id,
        stem="stem",
        representation="symbolic",
        correct_answer="1/2",
        elo=elo,
    )


@pytest.mark.parametrize("learner_rating", [200, 800, 1200, 1600, 2200, 2900])
def test_target_item_rating_yields_approximately_target_success(learner_rating: int) -> None:
    target = target_item_rating(learner_rating, target_success=0.75)
    predicted = elo_expected_score(learner_rating, target)
    assert predicted == pytest.approx(0.75, abs=0.01)


def test_target_item_rating_is_easier_than_learner_for_0_75_success() -> None:
    target = target_item_rating(1500, target_success=0.75)
    assert target < 1500


def test_target_item_rating_clamped_to_domain() -> None:
    assert target_item_rating(MIN_ELO_RATING, target_success=0.75) == MIN_ELO_RATING
    assert target_item_rating(MAX_ELO_RATING, target_success=0.99) >= MIN_ELO_RATING


def test_target_item_rating_rejects_invalid_target_success() -> None:
    with pytest.raises(ValueError, match="target_success"):
        target_item_rating(1200, target_success=0.0)
    with pytest.raises(ValueError, match="target_success"):
        target_item_rating(1200, target_success=1.0)


def test_target_item_rating_deterministic() -> None:
    assert target_item_rating(1200) == target_item_rating(1200)


def test_select_item_by_target_elo_picks_closest_candidate() -> None:
    target = target_item_rating(1200, target_success=0.75)
    candidates = [
        _item("far_low", target - 500),
        _item("closest", target + 2),
        _item("far_high", target + 500),
    ]
    result = select_item_by_target_elo(candidates, 1200)
    assert result.item.item_id == "closest"
    assert result.target_rating == target
    assert result.predicted_success == pytest.approx(0.75, abs=0.05)


def test_select_item_by_target_elo_skips_uncalibrated_items() -> None:
    target = target_item_rating(1200, target_success=0.75)
    candidates = [
        _item("uncalibrated", None),
        _item("calibrated", target),
    ]
    result = select_item_by_target_elo(candidates, 1200)
    assert result.item.item_id == "calibrated"


def test_select_item_by_target_elo_raises_with_no_calibrated_candidates() -> None:
    with pytest.raises(ValueError, match="Elo rating"):
        select_item_by_target_elo([_item("uncalibrated", None)], 1200)


def test_select_item_by_target_elo_ties_break_on_list_order() -> None:
    target = target_item_rating(1200, target_success=0.75)
    candidates = [
        _item("first", target + 1),
        _item("second", target - 1),
    ]
    result = select_item_by_target_elo(candidates, 1200)
    assert result.item.item_id == "first"
