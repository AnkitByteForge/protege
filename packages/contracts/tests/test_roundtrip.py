"""Round-trip serialisation: every contract survives
``model -> JSON -> model`` unchanged, and wire aliases dump to the document
names (roadmap P1 testing requirement)."""

from typing import get_args, get_origin

import builders
import pytest
from pydantic import BaseModel, TypeAdapter

import protege.contracts as contracts
from protege.contracts import (
    CardExplanation,
    VoiceExplanation,
)

ROUND_TRIP_MODELS: list[type[BaseModel]] = [
    builders.build_skill,
    builders.build_concept,
    builders.build_prerequisite,
    builders.build_misconception,
    builders.build_distractor,
    builders.build_learning_item,
    builders.build_item_version,
    builders.build_intervention,
    builders.build_sprout_script,
    builders.build_transfer_item,
    builders.build_transfer_observation,
    builders.build_evidence,
    builders.build_mastery_estimate,
    builders.build_misconception_belief,
    builders.build_teaching_episode,
    builders.build_mastery_outcome,
    builders.build_manipulative_action,
    builders.build_answer_submitted_event,
    builders.build_explanation_given_event,
    builders.build_manipulative_moved_event,
    builders.build_hint_requested_event,
    builders.build_voice_explanation,
    builders.build_text_explanation,
    builders.build_manipulative_explanation,
    builders.build_card_explanation,
    builders.build_diagnosis_label,
    builders.build_diagnosis_result,
    builders.build_policy_decision_state,
    builders.build_policy_decision_action,
    builders.build_policy_decision_reward,
    builders.build_policy_decision,
    builders.build_domain_event,
    builders.build_sprout_turn,
    builders.build_coach_hint,
    builders.build_report_sentence,
    builders.build_report_draft,
    builders.build_proof_claim,
    builders.build_tutor_briefing,
    builders.build_learner_evidence,
    builders.build_verification_record,
    builders.build_worked_example,
]


def test_every_exported_model_is_covered() -> None:
    """The round-trip list must cover every concrete model in __all__.

    The discriminated ``Explanation`` union is covered member-by-member.
    ``ProtegeBaseModel`` itself is excluded: it is the abstract base, never
    instantiated directly.
    """
    exported = {name for name in contracts.__all__ if isinstance(getattr(contracts, name), type)}
    exported.discard("ProtegeBaseModel")
    concrete = set()
    for model in exported:
        obj: object = getattr(contracts, model)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            concrete.add(obj)
        elif get_origin(obj) is not None:  # the Explanation union alias
            concrete.update(t for t in get_args(obj) if isinstance(t, type))
    covered = {type(builder()) for builder in ROUND_TRIP_MODELS}
    uncovered = concrete - covered
    assert not uncovered, (
        f"models missing round-trip coverage: {sorted(m.__name__ for m in uncovered)}"
    )


@pytest.mark.parametrize("builder", ROUND_TRIP_MODELS, ids=lambda b: b.__name__)
def test_json_round_trip(builder: type) -> None:
    instance = builder()
    restored = type(instance).model_validate_json(instance.model_dump_json())
    assert restored == instance


def test_learing_item_dumps_wire_names_by_alias() -> None:
    item = builders.build_learning_item()
    dumped = item.model_dump(by_alias=True)
    assert dumped["id"] == "i_0132"
    assert dumped["correct_answer"] == "1/4"


def test_misconception_belief_dumps_wire_names_by_alias() -> None:
    label = builders.build_diagnosis_result().labels[0]
    assert label.model_dump(by_alias=True)["misconception_id"] == "M003"


def test_explanation_union_discriminates_on_modality() -> None:
    """``Explanation`` is a discriminated-union type alias, not a BaseModel —
    it has no ``model_validate``. ``TypeAdapter`` is the correct Pydantic v2
    entry point for validating against a bare ``Annotated[Union[...]]``."""
    explanation_adapter = TypeAdapter(contracts.Explanation)
    voice = explanation_adapter.validate_python(
        {"modality": "voice", "text": "hello", "asr_confidence": 0.9}
    )
    assert isinstance(voice, VoiceExplanation)
    cards = explanation_adapter.validate_python({"modality": "explanation_card", "card_ids": ["a"]})
    assert isinstance(cards, CardExplanation)
