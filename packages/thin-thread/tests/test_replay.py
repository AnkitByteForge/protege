"""P8 testing requirement #6: deterministic replay produces the same
state/event sequence (and, since the ``IdAllocator`` never uses
randomness, the same evidence/claim ids too)."""

from __future__ import annotations

from _helpers import get_content, run_with_fake

from protege.thin_thread.scenario import happy_path_scenario, recovery_scenario


def _run_twice(scenario_factory, content):
    return run_with_fake(scenario_factory(), content), run_with_fake(scenario_factory(), content)


def test_happy_path_replay_is_byte_identical() -> None:
    content = get_content()
    first, second = _run_twice(happy_path_scenario, content)
    assert first.state_sequence == second.state_sequence
    assert [e.evidence_id for e in first.evidence] == [e.evidence_id for e in second.evidence]
    assert first.claim_evidence_ids == second.claim_evidence_ids
    assert first.mastery_outcome == second.mastery_outcome
    assert first.trace == second.trace


def test_recovery_replay_is_byte_identical() -> None:
    content = get_content()
    first, second = _run_twice(recovery_scenario, content)
    assert first.state_sequence == second.state_sequence
    assert [e.evidence_id for e in first.evidence] == [e.evidence_id for e in second.evidence]
    assert first.mastery_outcome == second.mastery_outcome
