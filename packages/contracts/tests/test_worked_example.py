"""P1 exit criterion: the v1.0 §38 worked example validates as a single JSON
document, verbatim."""

import json

import builders

from protege.contracts import LearnerEvidence, LearningItem, MasteryOutcome, WorkedExample


def test_worked_example_validates_verbatim(worked_example_json: str) -> None:
    example = WorkedExample.model_validate_json(worked_example_json)
    assert example.skill.code == "S004"
    assert example.misconception.code == "M003"
    assert example.misconception.distractor_likelihood["picks_1_8"] == 0.82
    # §38 predates the complement-likelihood field (D13, locked on
    # feature/p2-learning's docs/DECISIONS.md); the bare envelope must
    # keep validating with it absent.
    assert example.misconception.distractor_likelihood_if_not_misconception is None
    assert example.sprout_forbidden == [
        "stating 1/4 > 1/8 before resolution",
        "the words numerator/denominator",
    ]
    assert example.diagnostic_item.correct_answer == "1/4"
    assert [d.maps_to for d in example.diagnostic_item.distractors] == ["M003", "M011"]
    assert example.learner_evidence.diagnosis.labels[0].misconception_code == "M003"
    assert example.verification.results == [True, True, True]
    assert example.verification.transfer_item is not None
    assert example.verification.transfer_item.representation == "number_line"
    assert example.mastery_outcome.claim == "Ava can compare unit fractions"


def test_worked_example_aliases_preserved_on_dump(worked_example_json: str) -> None:
    """Dumping with aliases keeps the §38 document's wire names intact."""
    example = WorkedExample.model_validate_json(worked_example_json)
    dumped = json.loads(example.model_dump_json(by_alias=True))
    assert dumped["diagnostic_item"]["id"] == "i_0132"
    assert dumped["verification"]["transfer_item"]["id"] == "i_0201"
    assert dumped["mastery_outcome"]["evidence_ids"][0] == "e_901"


def test_flat_misconception_posterior_lifts_into_dict() -> None:
    outcome = MasteryOutcome.model_validate(
        {
            "p_known_before": 0.31,
            "p_known_after": 0.91,
            "misconception_M003_after": 0.04,
            "transfer_verified": True,
            "claim": "Ava can compare unit fractions",
            "evidence_ids": ["e_901"],
        }
    )
    assert outcome.misconception_posteriors == {"M003": 0.04}


def test_structured_posteriors_survive_round_trip() -> None:
    outcome = MasteryOutcome.model_validate(
        {
            "p_known_before": 0.31,
            "p_known_after": 0.91,
            "misconception_posteriors": {"M007": 0.64},
            "transfer_verified": False,
            "claim": "practiced comparing fractions",
            "evidence_ids": ["e_901"],
        }
    )
    restored = MasteryOutcome.model_validate_json(outcome.model_dump_json())
    assert restored.misconception_posteriors == {"M007": 0.64}


def test_diagnostic_item_accepts_correct_and_correct_answer() -> None:
    via_alias = LearningItem.model_validate(
        {"id": "i_1", "stem": "s", "representation": "area_model", "correct": "1/4"}
    )
    via_name = LearningItem.model_validate(
        {
            "id": "i_1",
            "stem": "s",
            "representation": "area_model",
            "correct_answer": "1/4",
        }
    )
    assert via_alias == via_name


def test_learner_evidence_accepts_explanation_alias() -> None:
    """§38's wire key is ``explanation``; ``explanation_text`` is the
    canonical field name. Both input spellings must produce an equivalent
    object — the same alias-choice contract ``LearningItem.correct`` /
    ``correct_answer`` already gets covered by the test above."""
    diagnosis = builders.build_diagnosis_result()
    via_alias = LearnerEvidence.model_validate(
        {"explanation": "the bottom number is how many pieces", "diagnosis": diagnosis}
    )
    via_name = LearnerEvidence.model_validate(
        {"explanation_text": "the bottom number is how many pieces", "diagnosis": diagnosis}
    )
    assert via_alias == via_name
    assert via_alias.explanation_text == "the bottom number is how many pieces"


def test_learner_evidence_dumps_explanation_text_by_alias() -> None:
    """The alias path must not silently regress: dumping always emits the
    canonical ``explanation_text`` key, never the legacy ``explanation`` key
    (mirrors ``test_learing_item_dumps_wire_names_by_alias`` in
    test_roundtrip.py for the analogous ``correct_answer``/``correct`` case)."""
    evidence = builders.build_learner_evidence()
    dumped = evidence.model_dump(by_alias=True)
    assert dumped["explanation_text"] == evidence.explanation_text
    assert "explanation" not in dumped
