from __future__ import annotations

from conftest import make_router, sprout_turn_json

from protege.authoring.loader import ContentPack
from protege.contracts import SproutPresentationEmotion
from protege.llm.errors import FallbackReason
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.roles.sprout import (
    SproutConstraints,
    SproutGenerator,
    SproutState,
    SproutValidationStage,
    build_sprout_messages,
    load_prompt_template,
)

_STEM = "Which is bigger: 1/4 or 1/8?"
_CORRECT_ANSWER = "1/4"


def _m003_generator(provider: FakeProvider, content_pack: ContentPack) -> SproutGenerator:
    return SproutGenerator(make_router(provider), content=content_pack)


# --- The correct answer never reaches the prompt ----------------------------


def test_correct_answer_is_absent_from_every_message_sent_to_the_model() -> None:
    # A stem where the answer is not already one of the two visible options
    # (unlike a bare "1/4 or 1/8?" comparison, where the answer necessarily
    # appears in the problem statement itself) -- the only route the answer
    # could reach the prompt through is a `correct_answer` parameter, and
    # `build_sprout_messages` has none.
    stem = "This rectangle is cut into 4 equal parts and 3 are shaded. What fraction is shaded?"
    correct_answer = "3/4"
    template = load_prompt_template()
    constraints = SproutConstraints(
        misconception_id="M003",
        title="Larger denominator means larger fraction",
        cognitive_origin="Whole-number bias.",
        forbidden_phrases=("numerator", "denominator"),
    )
    messages = build_sprout_messages(
        template,
        constraints=constraints,
        item_stem=stem,
        grade_band="3-4",
    )
    for message in messages:
        assert correct_answer not in message.content


def test_build_sprout_messages_has_no_correct_answer_parameter() -> None:
    """Structural guarantee, not just a runtime check: the function that
    builds what the LLM sees cannot accept a correct answer at all."""
    import inspect

    assert "correct_answer" not in inspect.signature(build_sprout_messages).parameters


# --- Misconception is code-selected, never model-selected -------------------


def test_a_model_that_names_a_different_misconception_is_rejected_and_falls_back(
    content_pack: ContentPack,
) -> None:
    # The model claims M001, but the caller (deterministic code) assigned M003.
    bad = sprout_turn_json(utterance="Three and four, two separate numbers!", exhibits="M001")
    provider = FakeProvider(script=[FakeOutcome.ok(bad), FakeOutcome.ok(bad)])
    generator = _m003_generator(provider, content_pack)

    result = generator.generate_turn(
        state=SproutState(misconception_id="M003"),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )

    assert result.used_fallback
    assert result.fallback_reason == FallbackReason.VALIDATOR
    assert result.turn.exhibits == "M003"  # the CALLER's choice, never the model's
    failed_stage = result.attempts[0].validation.failed_stage
    assert failed_stage == SproutValidationStage.MISCONCEPTION_CONSISTENCY


# --- Answer leakage: caught even when the model tries to leak ---------------


def test_a_leaking_candidate_never_reaches_the_final_turn(content_pack: ContentPack) -> None:
    leaking = sprout_turn_json(utterance="I think 1/4 is bigger, it just is!", exhibits="M003")
    provider = FakeProvider(script=[FakeOutcome.ok(leaking), FakeOutcome.ok(leaking)])
    generator = _m003_generator(provider, content_pack)

    result = generator.generate_turn(
        state=SproutState(misconception_id="M003"),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )

    assert result.used_fallback
    assert result.fallback_reason == FallbackReason.VALIDATOR
    assert _CORRECT_ANSWER not in result.turn.utterance
    assert result.attempts[0].validation.failed_stage == SproutValidationStage.ANSWER_LEAK


def test_two_consecutive_validator_failures_produce_the_authored_fallback(
    content_pack: ContentPack,
) -> None:
    """Roadmap P5 exit criterion: 'Forcing two validator failures produces
    an authored line.'"""
    leaking = sprout_turn_json(utterance="1/4 wins, easy.", exhibits="M003")
    provider = FakeProvider(script=[FakeOutcome.ok(leaking), FakeOutcome.ok(leaking)])
    generator = _m003_generator(provider, content_pack)

    result = generator.generate_turn(
        state=SproutState(misconception_id="M003"),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )

    assert result.used_fallback
    assert len(result.attempts) == 2
    assert all(not a.validation.passed for a in result.attempts)
    # The fallback line is one of the real authored M003 candidates.
    authored_utterances = {
        s.utterance for s in content_pack.sprout_scripts if s.misconception_code == "M003"
    }
    assert result.turn.utterance in authored_utterances


# --- Malformed / invalid model output ---------------------------------------


def test_malformed_model_output_produces_the_authored_fallback(content_pack: ContentPack) -> None:
    provider = FakeProvider(
        script=[
            FakeOutcome.malformed(),
            FakeOutcome.malformed(),  # exhausts the one router-level repair too
            FakeOutcome.malformed(),
            FakeOutcome.malformed(),
        ]
    )
    generator = _m003_generator(provider, content_pack)

    result = generator.generate_turn(
        state=SproutState(misconception_id="M003"),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )

    assert result.used_fallback
    assert result.fallback_reason == FallbackReason.SCHEMA
    assert result.attempts[0].validation.failed_stage == SproutValidationStage.SCHEMA


def test_schema_invalid_json_produces_the_authored_fallback(content_pack: ContentPack) -> None:
    provider = FakeProvider(
        script=[
            FakeOutcome.schema_invalid(),
            FakeOutcome.schema_invalid(),
            FakeOutcome.schema_invalid(),
            FakeOutcome.schema_invalid(),
        ]
    )
    generator = _m003_generator(provider, content_pack)

    result = generator.generate_turn(
        state=SproutState(misconception_id="M003"),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )

    assert result.used_fallback
    assert result.fallback_reason == FallbackReason.SCHEMA


# --- Happy path ---------------------------------------------------------------


def test_a_valid_consistent_non_leaking_candidate_is_used_as_is(content_pack: ContentPack) -> None:
    utterance = "I think 1/8 is bigger! Eight is way more than four."
    good = sprout_turn_json(utterance=utterance, exhibits="M003")
    provider = FakeProvider(script=[FakeOutcome.ok(good)])
    generator = _m003_generator(provider, content_pack)

    result = generator.generate_turn(
        state=SproutState(misconception_id="M003", resolution_belief=0.0),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )

    assert not result.used_fallback
    assert result.fallback_reason is None
    assert result.turn.exhibits == "M003"
    assert result.turn.emotion == SproutPresentationEmotion.CONFUSED


def test_emotion_is_always_overridden_by_resolution_belief_never_by_the_candidate(
    content_pack: ContentPack,
) -> None:
    # The model claims "delighted", but resolution_belief says otherwise.
    good = sprout_turn_json(
        utterance="I think 1/8 is bigger! Eight is way more than four.",
        exhibits="M003",
        emotion="delighted",
    )
    provider = FakeProvider(script=[FakeOutcome.ok(good)])
    generator = _m003_generator(provider, content_pack)

    result = generator.generate_turn(
        state=SproutState(misconception_id="M003", resolution_belief=0.0),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )

    assert not result.used_fallback
    assert result.turn.emotion == SproutPresentationEmotion.CONFUSED


def test_router_temperature_default_is_0_7_and_is_not_overridden(content_pack: ContentPack) -> None:
    """Roadmap P5: 'Temperature 0.7.' The ModelRouter's own default already
    satisfies this (packages/llm/src/protege/llm/router.py
    DEFAULT_TEMPERATURE); Sprout must not override it away from that."""
    provider = FakeProvider()
    router = make_router(provider)
    generator = SproutGenerator(router, content=content_pack)
    generator.generate_turn(
        state=SproutState(misconception_id="M003"),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )
    assert router._temperature == 0.7


def test_never_instantiates_a_provider_directly(content_pack: ContentPack) -> None:
    """Critical rule: 'Never directly instantiate an NVIDIA client.' The
    generator only ever calls through the router it was constructed with."""
    provider = FakeProvider()
    router = make_router(provider)
    generator = SproutGenerator(router, content=content_pack)
    generator.generate_turn(
        state=SproutState(misconception_id="M003"),
        item_stem=_STEM,
        correct_answer=_CORRECT_ANSWER,
    )
    assert len(provider.calls) >= 1  # generation happened only via the injected router/provider
