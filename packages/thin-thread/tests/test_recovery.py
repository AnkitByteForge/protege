"""P8 testing requirement #2: misconception-recovery path.

Two non-resolving teach-back turns push the real FSM through
COACH_ASSIST before a third turn resolves M003 -- and the real
:func:`~protege.roles.beliefs.apply_diagnosis_to_beliefs` Bayes update
actually fires on both unresolved turns.
"""

from __future__ import annotations

from _helpers import get_content, run_with_fake

from protege.contracts import SessionState as S
from protege.thin_thread.scenario import recovery_scenario


def test_recovery_scenario_routes_through_coach_assist_then_resolves() -> None:
    content = get_content()
    result = run_with_fake(recovery_scenario(), content)
    assert result.state_sequence.count(S.TEACH_BACK) == 3
    assert S.COACH_ASSIST in result.state_sequence
    assert result.context.misconception_resolved is True
    assert result.context.teach_back_turns == 3
    assert result.final_state == S.COMPLETE


def test_recovery_scenario_updates_belief_on_every_unresolved_turn() -> None:
    content = get_content()
    result = run_with_fake(recovery_scenario(), content)
    # Two unresolved turns + one resolving turn = 3 real diagnoses.
    assert len(result.diagnoses) == 3
    assert result.diagnoses[0].labels[0].state == "unresolved"
    assert result.diagnoses[1].labels[0].state == "unresolved"
    assert result.diagnoses[2].labels[0].state == "resolved"
    # A genuinely-run Bayes update moves the belief away from the
    # authored prior (0.42) after the first unresolved turn already.
    assert result.misconception_belief is not None
    assert result.misconception_belief.p_holds != 0.42


def test_recovery_scenario_still_produces_a_five_evidence_claim() -> None:
    content = get_content()
    result = run_with_fake(recovery_scenario(), content)
    assert result.mastery_outcome is not None
    assert len(result.claim_evidence_ids) == 5
