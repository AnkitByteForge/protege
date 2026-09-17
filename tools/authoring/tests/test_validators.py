"""Deterministic P3 validation rules (roadmap P3 "Testing" + "Validation").

The real content pack is the integration-level check (must validate clean).
Each rule additionally gets a focused unit test against a small, hand-built
:class:`ContentPack` so a rule regression is caught even if the real content
pack happens not to exercise it.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from protege.authoring.loader import ContentPack, load_content_pack
from protege.authoring.validators import (
    REQUIRED_GENERAL_TRANSFER_ITEMS,
    REQUIRED_MISCONCEPTION_COUNT,
    REQUIRED_PRACTICE_ITEMS,
    validate_content_pack,
)
from protege.contracts import (
    Intervention,
    LearningItem,
    Misconception,
    Prerequisite,
    Skill,
    SproutScript,
    TransferItem,
    WorkedExample,
)


@pytest.fixture(scope="module")
def real_pack():
    return load_content_pack()


def test_real_content_pack_validates_clean(real_pack) -> None:
    report = validate_content_pack(real_pack)
    assert report.ok, report.errors_by_rule
    assert report.misconception_count == REQUIRED_MISCONCEPTION_COUNT
    assert report.practice_item_count == REQUIRED_PRACTICE_ITEMS


def test_real_content_pack_reading_level_is_pending(real_pack) -> None:
    report = validate_content_pack(real_pack)
    assert report.reading_level_status == "not_evaluated (pending P2 merge)"


def test_real_content_pack_representation_coverage(real_pack) -> None:
    report = validate_content_pack(real_pack)
    assert set(report.representation_counts) == {
        "area_model",
        "number_line",
        "set_model",
        "symbolic",
    }


def test_real_content_pack_general_transfer_count(real_pack) -> None:
    general = [
        item
        for raw, item in zip(real_pack.transfer_items_raw, real_pack.transfer_items, strict=True)
        if raw.get("pool") == "general"
    ]
    assert len(general) == REQUIRED_GENERAL_TRANSFER_ITEMS


def test_real_content_pack_complement_likelihoods_are_present_and_independent(real_pack) -> None:
    """D13 adversarial-review guard: every one of the 8 real misconceptions'
    complement tables must be present, key-aligned with distractor_likelihood,
    independently authored (not a copy), and not reusing the primary table's
    'other' residual. Regressing any of these should fail this test, not just
    the CLI gate, so the property survives future content edits."""
    assert len(real_pack.misconceptions) == REQUIRED_MISCONCEPTION_COUNT
    for m in real_pack.misconceptions:
        complement = m.distractor_likelihood_if_not_misconception
        assert complement is not None, m.code
        assert set(complement) == set(m.distractor_likelihood), m.code
        assert abs(sum(complement.values()) - 1.0) < 0.02, m.code
        assert complement != m.distractor_likelihood, m.code
        assert complement["other"] != m.distractor_likelihood["other"], m.code


# --- minimal synthetic pack for negative-path unit tests ------------------------
#
# This fixture intentionally authors only ONE misconception (not the
# P3-required 8) to keep unit tests small and fast. That means
# `required_counts` always reports the 1-vs-8 mismatch on this fixture —
# expected and asserted once in `test_minimal_pack_is_valid`; every other
# test below only asserts that ITS injected bug's rule fires, not that the
# whole report is clean.


def _minimal_valid_pack() -> ContentPack:
    skill = Skill.model_validate({"code": "S001_a", "title": "A", "grade_band": "1-2"})
    misconception = Misconception.validate_authored(
        {
            "code": "M001",
            "title": "T",
            "cognitive_origin": "origin",
            "skill_code": "S001_a",
            "distractor_likelihood": {"bug": 0.8, "other": 0.2},
            "distractor_likelihood_if_not_misconception": {"bug": 0.1, "other": 0.9},
            "sprout_forbidden": ["forbidden_word"],
        }
    )
    sprout_scripts = [
        SproutScript.model_validate(
            {
                "id": f"SS_{n}",
                "utterance": "safe line",
                "emotion": "confident",
                "misconception_code": "M001",
            }
        )
        for n in range(6)
    ]
    interventions = [
        Intervention.model_validate(
            {
                "id": f"INT_{c}",
                "type": "HINT",
                "strategy": "s",
                "script": "x",
                "historical_success_rate": 0.5,
                "misconception_code": "M001",
            }
        )
        for c in "ABC"
    ]
    diagnostic_items = [
        LearningItem.model_validate(
            {
                "id": f"i_diag_{n}",
                "stem": "stem",
                "representation": "area_model",
                "correct_answer": "right",
                "distractors": [{"value": "wrong", "maps_to": "M001", "likelihood": 0.8}],
                "role": "diagnostic",
                "skill_code": "S001_a",
            }
        )
        for n in range(4)
    ]
    practice_items = [
        LearningItem.model_validate(
            {
                "id": f"i_prac_{n}",
                "stem": "stem",
                "representation": "symbolic",
                "correct_answer": "right",
                "distractors": [{"value": "wrong", "maps_to": "M001", "likelihood": 0.8}],
                "role": "practice",
                "skill_code": "S001_a",
            }
        )
        for n in range(40)
    ]
    transfer_raw: list[dict] = [
        {
            "id": "i_tr_m_1",
            "stem": "s",
            "representation": "number_line",
            "correct_answer": "r",
            "skill_code": "S001_a",
            "pool": "misconception",
        },
        {
            "id": "i_tr_m_2",
            "stem": "s",
            "representation": "set_model",
            "correct_answer": "r",
            "skill_code": "S001_a",
            "pool": "misconception",
        },
        *(
            {
                "id": f"i_tr_g_{n}",
                "stem": "s",
                "representation": "number_line" if n < 4 else "symbolic",
                "correct_answer": "r",
                "skill_code": "S001_a",
                "pool": "general",
            }
            for n in range(8)
        ),
    ]
    transfer_items = [TransferItem.model_validate(r) for r in transfer_raw]

    worked_example = WorkedExample.model_validate(
        {
            "skill": skill.model_dump(by_alias=True),
            "misconception": misconception.model_dump(by_alias=True),
            "sprout_scripts": [s.model_dump(by_alias=True) for s in sprout_scripts[:3]],
            "sprout_forbidden": ["forbidden_word"],
            "diagnostic_item": diagnostic_items[0].model_dump(by_alias=True),
            "learner_evidence": {
                "explanation": "the reasoning",
                "diagnosis": {
                    "labels": [
                        {"misconception_id": "M001", "state": "resolved", "confidence": 0.9}
                    ],
                    "asr_reliable": True,
                },
            },
            "intervention": interventions[0].model_dump(by_alias=True),
            "verification": {
                "unaided_items": ["i_prac_0", "i_prac_1", "i_prac_2"],
                "results": [True, True, True],
                "transfer_item": {
                    "id": "i_tr_m_1",
                    "representation": "number_line",
                    "result": True,
                },
            },
            "mastery_outcome": {
                "p_known_before": 0.2,
                "p_known_after": 0.9,
                "misconception_posteriors": {"M001": 0.05},
                "transfer_verified": True,
                "claim": "claim",
                "evidence_ids": ["e1"],
            },
        }
    )

    return ContentPack(
        root=Path("."),
        skills=[skill],
        prerequisites=[],
        misconceptions=[misconception],
        sprout_scripts=sprout_scripts,
        interventions=interventions,
        diagnostic_items=diagnostic_items,
        practice_items=practice_items,
        transfer_items=transfer_items,
        transfer_items_raw=transfer_raw,
        worked_examples={"M001": worked_example},
    )


def test_minimal_pack_is_valid() -> None:
    report = validate_content_pack(_minimal_valid_pack())
    assert set(report.errors_by_rule) <= {"required_counts"}


def test_duplicate_skill_code_detected() -> None:
    pack = _minimal_valid_pack()
    broken = dataclasses.replace(pack, skills=[pack.skills[0], pack.skills[0]])
    report = validate_content_pack(broken)
    assert "id_uniqueness" in report.errors_by_rule


def test_unknown_misconception_reference_detected() -> None:
    pack = _minimal_valid_pack()
    bad_script = SproutScript.model_validate(
        {"id": "SS_bad", "utterance": "x", "emotion": "confident", "misconception_code": "M999"}
    )
    broken = dataclasses.replace(pack, sprout_scripts=[*pack.sprout_scripts, bad_script])
    report = validate_content_pack(broken)
    assert "misconception_code_validity" in report.errors_by_rule


def test_diagnostic_item_missing_own_misconception_distractor_detected() -> None:
    pack = _minimal_valid_pack()
    bad_item = pack.diagnostic_items[0].model_copy(update={"skill_code": "S999_other"})
    broken = dataclasses.replace(pack, diagnostic_items=[bad_item, *pack.diagnostic_items[1:]])
    report = validate_content_pack(broken)
    assert "distractor_mapping" in report.errors_by_rule


def test_missing_complement_likelihood_detected() -> None:
    pack = _minimal_valid_pack()
    bad_misconception = pack.misconceptions[0].model_copy(
        update={"distractor_likelihood_if_not_misconception": None}
    )
    broken = dataclasses.replace(pack, misconceptions=[bad_misconception])
    report = validate_content_pack(broken)
    assert "complement_likelihood" in report.errors_by_rule


def test_complement_likelihood_key_mismatch_detected() -> None:
    pack = _minimal_valid_pack()
    bad_misconception = pack.misconceptions[0].model_copy(
        update={"distractor_likelihood_if_not_misconception": {"totally_different_key": 1.0}}
    )
    broken = dataclasses.replace(pack, misconceptions=[bad_misconception])
    report = validate_content_pack(broken)
    assert "complement_likelihood" in report.errors_by_rule


def test_complement_likelihood_bad_sum_detected() -> None:
    pack = _minimal_valid_pack()
    bad_misconception = pack.misconceptions[0].model_copy(
        update={"distractor_likelihood_if_not_misconception": {"bug": 0.1, "other": 0.1}}
    )
    broken = dataclasses.replace(pack, misconceptions=[bad_misconception])
    report = validate_content_pack(broken)
    assert "complement_likelihood" in report.errors_by_rule


def test_complement_likelihood_identical_copy_detected() -> None:
    pack = _minimal_valid_pack()
    primary = pack.misconceptions[0].distractor_likelihood
    bad_misconception = pack.misconceptions[0].model_copy(
        update={"distractor_likelihood_if_not_misconception": dict(primary)}
    )
    broken = dataclasses.replace(pack, misconceptions=[bad_misconception])
    report = validate_content_pack(broken)
    assert "complement_likelihood" in report.errors_by_rule


def test_complement_likelihood_reused_other_detected() -> None:
    pack = _minimal_valid_pack()
    primary = pack.misconceptions[0].distractor_likelihood
    bad_misconception = pack.misconceptions[0].model_copy(
        update={
            "distractor_likelihood_if_not_misconception": {
                "bug": 1.0 - primary["other"],
                "other": primary["other"],
            }
        }
    )
    broken = dataclasses.replace(pack, misconceptions=[bad_misconception])
    report = validate_content_pack(broken)
    assert "complement_likelihood" in report.errors_by_rule


def test_worked_example_embedded_complement_checked_independently() -> None:
    """The complement rule also inspects each worked example's embedded
    misconception copy, not just misconceptions.json — the two are authored
    together but loaded through separate paths."""
    pack = _minimal_valid_pack()
    example = pack.worked_examples["M001"]
    bad_misconception = example.misconception.model_copy(
        update={"distractor_likelihood_if_not_misconception": None}
    )
    bad_example = example.model_copy(update={"misconception": bad_misconception})
    broken = dataclasses.replace(pack, worked_examples={"M001": bad_example})
    report = validate_content_pack(broken)
    assert "complement_likelihood" in report.errors_by_rule


def test_prerequisite_cycle_detected() -> None:
    pack = _minimal_valid_pack()
    a = Skill.model_validate(
        {"code": "S001_a", "title": "A", "grade_band": "1-2", "prerequisites": ["S002_b"]}
    )
    b = Skill.model_validate(
        {"code": "S002_b", "title": "B", "grade_band": "1-2", "prerequisites": ["S001_a"]}
    )
    edges = [
        Prerequisite.model_validate({"skill_code": "S001_a", "prereq_code": "S002_b"}),
        Prerequisite.model_validate({"skill_code": "S002_b", "prereq_code": "S001_a"}),
    ]
    broken = dataclasses.replace(pack, skills=[a, b], prerequisites=edges)
    report = validate_content_pack(broken)
    assert "prerequisite_graph" in report.errors_by_rule


def test_prerequisite_json_must_match_skills_json() -> None:
    pack = _minimal_valid_pack()
    stray_edge = [
        Prerequisite.model_validate({"skill_code": "S001_a", "prereq_code": "S999_ghost"})
    ]
    broken = dataclasses.replace(pack, prerequisites=stray_edge)
    report = validate_content_pack(broken)
    assert "prerequisite_graph" in report.errors_by_rule


def test_answer_leakage_detected() -> None:
    pack = _minimal_valid_pack()
    leaking_script = SproutScript.model_validate(
        {
            "id": "SS_leak",
            "utterance": "The answer is right, for sure!",
            "emotion": "confident",
            "misconception_code": "M001",
        }
    )
    broken = dataclasses.replace(pack, sprout_scripts=[*pack.sprout_scripts, leaking_script])
    report = validate_content_pack(broken)
    assert "answer_leakage" in report.errors_by_rule


def test_sprout_forbidden_vocabulary_detected() -> None:
    pack = _minimal_valid_pack()
    bad_script = SproutScript.model_validate(
        {
            "id": "SS_forbidden",
            "utterance": "I will say the forbidden_word out loud",
            "emotion": "confident",
            "misconception_code": "M001",
        }
    )
    broken = dataclasses.replace(pack, sprout_scripts=[*pack.sprout_scripts, bad_script])
    report = validate_content_pack(broken)
    assert "sprout_constraints" in report.errors_by_rule


def test_wrong_intervention_count_detected() -> None:
    pack = _minimal_valid_pack()
    broken = dataclasses.replace(pack, interventions=pack.interventions[:2])
    report = validate_content_pack(broken)
    assert "intervention_linkage" in report.errors_by_rule


def test_transfer_item_reusing_diagnostic_representation_detected() -> None:
    pack = _minimal_valid_pack()
    raw = [dict(r) for r in pack.transfer_items_raw]
    raw[0]["representation"] = "area_model"  # same as the diagnostic items' representation
    items = [TransferItem.model_validate(r) for r in raw]
    broken = dataclasses.replace(pack, transfer_items_raw=raw, transfer_items=items)
    report = validate_content_pack(broken)
    assert "transfer_item_correctness" in report.errors_by_rule


def test_missing_worked_example_detected() -> None:
    pack = _minimal_valid_pack()
    broken = dataclasses.replace(pack, worked_examples={})
    report = validate_content_pack(broken)
    assert "worked_example_validation" in report.errors_by_rule


def test_worked_example_mastery_must_improve() -> None:
    pack = _minimal_valid_pack()
    example = pack.worked_examples["M001"]
    bad_outcome = example.mastery_outcome.model_copy(
        update={"p_known_before": 0.9, "p_known_after": 0.2}
    )
    bad_example = example.model_copy(update={"mastery_outcome": bad_outcome})
    broken = dataclasses.replace(pack, worked_examples={"M001": bad_example})
    report = validate_content_pack(broken)
    assert "worked_example_validation" in report.errors_by_rule
