from __future__ import annotations

from collections.abc import Sequence

from protege.contracts import DiagnosisResult, Misconception
from protege.learning_engine.mastery_engine import misconception_belief_update
from protege.roles.beliefs import apply_diagnosis_to_beliefs
from protege.roles.constants import OTHER_OBSERVED_BEHAVIOR


def test_unresolved_label_updates_belief_via_the_real_p2_api(
    misconception_set: Sequence[Misconception], m003: Misconception
) -> None:
    diagnosis = DiagnosisResult(
        labels=[
            {
                "misconception_id": "M003",
                "state": "unresolved",
                "confidence": 0.7,
                "evidence_span": "eight is more than four",
            }
        ]
    )
    priors = {"M003": m003.prevalence_prior}
    updated = apply_diagnosis_to_beliefs(
        diagnosis, misconception_set=misconception_set, priors=priors
    )

    expected = misconception_belief_update(
        {"M003": m003.prevalence_prior},
        {"M003": m003.distractor_likelihood},
        {"M003": m003.require_complement_likelihood()},
        OTHER_OBSERVED_BEHAVIOR,
    )
    assert updated["M003"] == expected["M003"]
    assert updated["M003"] != priors["M003"]  # a real update happened


def test_resolved_label_leaves_the_prior_untouched(
    misconception_set: Sequence[Misconception], m003: Misconception
) -> None:
    diagnosis = DiagnosisResult(
        labels=[
            {
                "misconception_id": "M003",
                "state": "resolved",
                "confidence": 0.9,
                "evidence_span": "more pieces are littler",
            }
        ]
    )
    priors = {"M003": m003.prevalence_prior}
    updated = apply_diagnosis_to_beliefs(
        diagnosis, misconception_set=misconception_set, priors=priors
    )
    assert updated == priors


def test_abstained_diagnosis_leaves_all_priors_untouched(
    misconception_set: Sequence[Misconception],
) -> None:
    diagnosis = DiagnosisResult(abstained=True, labels=[])
    priors = {"M003": 0.42, "M001": 0.35}
    updated = apply_diagnosis_to_beliefs(
        diagnosis, misconception_set=misconception_set, priors=priors
    )
    assert updated == priors


def test_code_absent_from_priors_is_left_out(misconception_set: Sequence[Misconception]) -> None:
    diagnosis = DiagnosisResult(
        labels=[
            {
                "misconception_id": "M003",
                "state": "unresolved",
                "confidence": 0.7,
                "evidence_span": None,
            }
        ]
    )
    updated = apply_diagnosis_to_beliefs(diagnosis, misconception_set=misconception_set, priors={})
    assert updated == {}


def test_missing_complement_likelihood_is_skipped_not_raised() -> None:
    legacy_misconception = Misconception.model_validate(
        {
            "code": "M003",
            "title": "Larger denominator means larger fraction",
            "cognitive_origin": "whole-number bias",
            "distractor_likelihood": {"picks_1_8": 0.82, "other": 0.12},
            # distractor_likelihood_if_not_misconception intentionally omitted
            # (legacy content, D13's None-means-not-yet-authored case).
        }
    )
    diagnosis = DiagnosisResult(
        labels=[
            {
                "misconception_id": "M003",
                "state": "unresolved",
                "confidence": 0.7,
                "evidence_span": None,
            }
        ]
    )
    priors = {"M003": 0.42}
    updated = apply_diagnosis_to_beliefs(
        diagnosis, misconception_set=[legacy_misconception], priors=priors
    )
    assert updated == priors  # left untouched, never a fabricated value
