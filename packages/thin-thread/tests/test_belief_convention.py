"""Locks in the P8 exit-gate audit's fix: the misconception-belief update
is a pure pass-through to the real, already-shipped
:func:`~protege.roles.beliefs.apply_diagnosis_to_beliefs` (P6) -- P8 must
never reintroduce a local formula that moves ``p_holds`` on a RESOLVED
label, since no canonical document specifies one and
``apply_diagnosis_to_beliefs`` itself deliberately leaves it unchanged.
"""

from __future__ import annotations

from _helpers import get_content, run_with_fake

from protege.thin_thread.scenario import happy_path_scenario, resolve_misconception


def test_resolution_does_not_move_the_numeric_belief() -> None:
    """The happy-path scenario resolves M003 on its very first teach-back
    turn, with no prior unresolved evidence. If resolution moved the
    belief, ``p_holds`` would differ from the authored prevalence prior;
    per P6's own documented convention, it must not."""
    content = get_content()
    misconception = resolve_misconception(content)
    result = run_with_fake(happy_path_scenario(), content)

    assert result.misconception_belief is not None
    assert result.misconception_belief.state == "resolved"
    assert result.misconception_belief.p_holds == misconception.prevalence_prior


def test_claim_caveats_disclose_the_posterior_limitation() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)

    assert result.mastery_outcome is not None
    assert any("posterior reflects only" in caveat for caveat in result.mastery_outcome.caveats)
