"""P8 testing requirement #1: happy-path thin-thread execution.

Reproduces ARCHITECTURE.md §42's "Thin Thread" transcript through the
real FSM -> Sprout -> Diagnostician -> learning-engine pipeline.
"""

from __future__ import annotations

from _helpers import get_content, run_with_fake

from protege.contracts import SessionState as S
from protege.thin_thread.scenario import happy_path_scenario

EXPECTED_SEQUENCE = (
    S.ARRIVAL,
    S.SPROUT_TEASE,
    S.DIAGNOSTIC,
    S.DISCOVERY,
    S.GUIDED_LEARNING,
    S.PRACTICE,
    S.EXPLANATION,
    S.SPROUT_SETUP,
    S.TEACH_BACK,
    S.REFLECTION,
    S.INDEPENDENT_VERIFY,
    S.TRANSFER,
    S.MASTERY_DECISION,
    S.REWARD,
    S.SUMMARY,
    S.RETRIEVAL_SCHEDULE,
    S.COMPLETE,
)


def test_happy_path_reaches_complete_via_the_exact_expected_fsm_sequence() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)
    assert result.state_sequence == EXPECTED_SEQUENCE
    assert result.final_state == S.COMPLETE


def test_happy_path_resolves_m003_on_the_first_teach_back_turn() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)
    assert result.context.misconception_resolved is True
    assert result.context.teach_back_turns == 1
    assert result.misconception_belief is not None
    assert result.misconception_belief.state == "resolved"


def test_happy_path_produces_a_verified_mastery_claim() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)
    assert result.mastery_outcome is not None
    assert result.threshold_decision is not None
    assert result.threshold_decision.mastery_verified is True
    assert result.mastery_outcome.claim == "Compares unit fractions"
    assert result.mastery_outcome.p_known_after > result.mastery_outcome.p_known_before
    assert result.mastery_outcome.transfer_verified is True


def test_happy_path_bkt_reproduces_architecture_section_42s_first_update() -> None:
    content = get_content()
    """ARCHITECTURE.md §42: "P(knows) 0.20 -> 0.44" on the first (correct)
    diagnostic response."""
    result = run_with_fake(happy_path_scenario(), content)
    diagnostic_evidence = result.evidence[0]
    assert diagnostic_evidence.payload["correct"] is True
    assert any("0.20 -> 0.44" in line for line in result.trace)
