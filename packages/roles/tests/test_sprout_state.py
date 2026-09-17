from __future__ import annotations

import pytest

from protege.contracts import SproutPresentationEmotion
from protege.roles.sprout import SproutState, presentation_emotion_for


def test_sprout_state_rejects_out_of_range_resolution_belief() -> None:
    with pytest.raises(ValueError, match="resolution_belief"):
        SproutState(misconception_id="M003", resolution_belief=1.5)
    with pytest.raises(ValueError, match="resolution_belief"):
        SproutState(misconception_id="M003", resolution_belief=-0.1)


def test_sprout_state_rejects_negative_turn_index() -> None:
    with pytest.raises(ValueError, match="turn_index"):
        SproutState(misconception_id="M003", turn_index=-1)


def test_sprout_state_accepts_boundary_values() -> None:
    SproutState(misconception_id="M003", resolution_belief=0.0, turn_index=0)
    SproutState(misconception_id="M003", resolution_belief=1.0, turn_index=0)


@pytest.mark.parametrize(
    ("belief", "expected"),
    [
        (0.0, SproutPresentationEmotion.CONFUSED),
        (0.10, SproutPresentationEmotion.CONFUSED),
        (0.34, SproutPresentationEmotion.CONFUSED),
        (0.35, SproutPresentationEmotion.THINKING),
        (0.50, SproutPresentationEmotion.THINKING),
        (0.64, SproutPresentationEmotion.THINKING),
        (0.65, SproutPresentationEmotion.DAWNING),
        (0.89, SproutPresentationEmotion.DAWNING),
        (0.90, SproutPresentationEmotion.DELIGHTED),
        (1.0, SproutPresentationEmotion.DELIGHTED),
    ],
)
def test_presentation_emotion_is_a_pure_function_of_resolution_belief(
    belief: float, expected: SproutPresentationEmotion
) -> None:
    assert presentation_emotion_for(belief) == expected


def test_presentation_emotion_never_reaches_delighted_below_the_top_threshold() -> None:
    """Architecture §8.3/§14: 'Sprout is never delighted before the
    misconception clears' -- exercised as a monotonicity property over a
    dense sweep, not just the boundary table above."""
    for hundredths in range(0, 90):
        belief = hundredths / 100
        assert presentation_emotion_for(belief) != SproutPresentationEmotion.DELIGHTED
