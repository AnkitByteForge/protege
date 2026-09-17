"""P8 testing requirements #3 and #4: independent verification, and that a
verification failure never falsely produces a verified-mastery claim.
"""

from __future__ import annotations

from dataclasses import replace

from _helpers import get_content, run_with_fake

from protege.contracts import SessionState as S
from protege.thin_thread.scenario import happy_path_scenario


def test_independent_verification_path_scores_three_unaided_items() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)
    verify_evidence = [e for e in result.evidence if e.payload.get("unaided") is True]
    assert len(verify_evidence) == 3
    assert all(e.weight == 3.0 for e in verify_evidence)
    assert result.context.verify_correct_count == 3


def test_verification_failure_routes_to_guided_learning_not_mastery() -> None:
    content = get_content()
    failing = replace(happy_path_scenario(), verify_correct=(True, False, False))
    result = run_with_fake(failing, content)

    assert result.final_state == S.GUIDED_LEARNING
    assert S.TRANSFER not in result.state_sequence
    assert S.MASTERY_DECISION not in result.state_sequence
    assert result.mastery_outcome is None
    assert result.threshold_decision is None
    assert result.claim_evidence_ids == []
