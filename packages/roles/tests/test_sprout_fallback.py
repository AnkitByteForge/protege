from __future__ import annotations

from protege.authoring.loader import ContentPack
from protege.contracts import SproutPresentationEmotion
from protege.roles.sprout import emit_authored_fallback, select_candidate_pool


def test_fallback_is_deterministic_for_the_same_turn_index(content_pack: ContentPack) -> None:
    pool = select_candidate_pool(content_pack.sprout_scripts, "M003")
    first = emit_authored_fallback(
        pool,
        turn_index=2,
        misconception_id="M003",
        presentation_emotion=SproutPresentationEmotion.CONFUSED,
    )
    second = emit_authored_fallback(
        pool,
        turn_index=2,
        misconception_id="M003",
        presentation_emotion=SproutPresentationEmotion.CONFUSED,
    )
    assert first == second


def test_fallback_cycles_through_the_pool_by_turn_index(content_pack: ContentPack) -> None:
    pool = select_candidate_pool(content_pack.sprout_scripts, "M003")
    utterances = {
        emit_authored_fallback(
            pool,
            turn_index=i,
            misconception_id="M003",
            presentation_emotion=SproutPresentationEmotion.CONFUSED,
        ).utterance
        for i in range(len(pool))
    }
    # Every distinct turn_index in [0, len(pool)) selects a distinct script.
    assert len(utterances) == len(pool)


def test_fallback_always_exhibits_the_assigned_misconception(content_pack: ContentPack) -> None:
    pool = select_candidate_pool(content_pack.sprout_scripts, "M001")
    for i in range(10):
        turn = emit_authored_fallback(
            pool,
            turn_index=i,
            misconception_id="M001",
            presentation_emotion=SproutPresentationEmotion.CONFUSED,
        )
        assert turn.exhibits == "M001"


def test_fallback_emotion_is_the_presentation_emotion_never_the_scripts_own_tone(
    content_pack: ContentPack,
) -> None:
    """Critical rule: emotion is driven by resolution belief, never sentiment
    -- not even an authored script's own tone tag."""
    pool = select_candidate_pool(content_pack.sprout_scripts, "M003")
    for emotion in SproutPresentationEmotion:
        turn = emit_authored_fallback(
            pool, turn_index=0, misconception_id="M003", presentation_emotion=emotion
        )
        assert turn.emotion == emotion
