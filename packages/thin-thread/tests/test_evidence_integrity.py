"""P8 testing requirement #5: the final claim contains only real evidence
IDs -- every id cited in ``MasteryOutcome.evidence_ids`` must correspond to
an :class:`~protege.contracts.Evidence` record this run actually produced,
and there must be exactly five of them (roadmap P8 exit criterion).
"""

from __future__ import annotations

from _helpers import get_content, run_with_fake

from protege.thin_thread.scenario import happy_path_scenario, recovery_scenario


def _assert_claim_evidence_is_real(result) -> None:
    assert result.mastery_outcome is not None
    produced_ids = {e.evidence_id for e in result.evidence}
    claimed_ids = set(result.mastery_outcome.evidence_ids)
    assert len(result.mastery_outcome.evidence_ids) == 5
    assert claimed_ids.issubset(produced_ids), (
        f"claim cites evidence never produced: {claimed_ids - produced_ids}"
    )
    # Every produced evidence id is unique -- no accidental id reuse across
    # the run (the IdAllocator's whole job).
    assert len(produced_ids) == len(result.evidence)


def test_happy_path_claim_evidence_is_real() -> None:
    content = get_content()
    _assert_claim_evidence_is_real(run_with_fake(happy_path_scenario(), content))


def test_recovery_claim_evidence_is_real() -> None:
    content = get_content()
    _assert_claim_evidence_is_real(run_with_fake(recovery_scenario(), content))


def test_claim_evidence_covers_teaching_verification_and_transfer() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)
    kinds = {e.kind for e in result.evidence if e.evidence_id in result.claim_evidence_ids}
    assert kinds == {"teaching_episode", "response", "transfer"}
