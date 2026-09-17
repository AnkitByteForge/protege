from __future__ import annotations

from collections import Counter

from protege.roles.golden_set import generate_golden_set, load_golden_set


def test_checked_in_snapshot_has_120_examples_balanced_across_8_codes() -> None:
    examples = load_golden_set()
    assert len(examples) == 120
    counts = Counter(e.misconception_code for e in examples)
    assert counts == {f"M{n:03d}": 15 for n in range(1, 9)}


def test_checked_in_snapshot_has_the_documented_source_mix() -> None:
    examples = load_golden_set()
    counts = Counter(e.source for e in examples)
    assert counts == {"sprout_script": 48, "worked_example": 8, "distractor_template": 64}


def test_only_distractor_template_examples_carry_a_distractor() -> None:
    examples = load_golden_set()
    for example in examples:
        if example.source == "distractor_template":
            assert example.distractor is not None
            assert example.distractor.maps_to == example.misconception_code
        else:
            assert example.distractor is None


def test_worked_example_records_are_resolved_state() -> None:
    examples = load_golden_set()
    for example in examples:
        if example.source == "worked_example":
            assert example.state == "resolved"
        else:
            assert example.state == "unresolved"


def test_example_ids_are_unique() -> None:
    examples = load_golden_set()
    ids = [e.id for e in examples]
    assert len(ids) == len(set(ids))


def test_generate_golden_set_is_deterministic_against_the_live_content_pack() -> None:
    first = generate_golden_set()
    second = generate_golden_set()
    assert first == second


def test_generate_golden_set_matches_the_checked_in_snapshot() -> None:
    # If this fails, content/math/fractions/v1/ changed since the snapshot
    # was generated -- regenerate per packages/roles/golden_set/PROVENANCE.md.
    assert generate_golden_set() == load_golden_set()
