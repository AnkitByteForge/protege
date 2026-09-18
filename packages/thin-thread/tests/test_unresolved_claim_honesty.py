"""P8 exit-gate audit 3 finding (real NVIDIA smoke): when the real
Diagnostician call falls back to abstention and the misconception is
never resolved during teach-back, the mastery claim must say so --
never silently proceed as if resolution happened. Discovered live: a
real NVIDIA smoke run degraded both the Sprout and Diagnostician calls
to their deterministic fallbacks, leaving M003 unresolved, and the
resulting claim originally carried no caveat about it.
"""

from __future__ import annotations

from _helpers import get_content, run_with_fake

from protege.contracts import SessionState as S
from protege.thin_thread.scenario import never_resolves_scenario


def test_unresolved_teach_back_still_proves_mastery_independently() -> None:
    """P2's threshold (p_known >= 0.85, >= 3 unaided correct, >= 1
    transfer attempted) does not require misconception resolution -- the
    claim can and should still be made."""
    content = get_content()
    result = run_with_fake(never_resolves_scenario(), content)

    assert result.context.misconception_resolved is False
    assert result.final_state == S.COMPLETE
    assert result.mastery_outcome is not None
    assert result.threshold_decision is not None
    assert result.threshold_decision.mastery_verified is True


def test_unresolved_teach_back_claim_discloses_it_honestly() -> None:
    content = get_content()
    result = run_with_fake(never_resolves_scenario(), content)

    assert result.mastery_outcome is not None
    assert any("NOT resolved during" in caveat for caveat in result.mastery_outcome.caveats), (
        result.mastery_outcome.caveats
    )


def test_unresolved_teach_back_exits_via_the_real_timeout_path() -> None:
    """The one scripted (unresolved, no-progress) turn self-loops back
    into TEACH_BACK via the real ``(S.TEACH_BACK, Event.TURN_COMPLETED)
    -> S.TEACH_BACK`` default transition (stuck_turns=1, below the
    COACH_ASSIST threshold of 2) -- so TEACH_BACK legitimately appears
    twice in the journal -- and only then, once the scenario's scripted
    turns are exhausted, falls through via the real, already-tested
    ``(S.TEACH_BACK, Event.TIMEOUT) -> S.REFLECTION`` transition. Neither
    hop is a P8-invented shortcut."""
    content = get_content()
    result = run_with_fake(never_resolves_scenario(), content)

    assert result.state_sequence.count(S.TEACH_BACK) == 2
    assert S.REFLECTION in result.state_sequence
    assert any("exhausted without resolving" in line for line in result.trace)
