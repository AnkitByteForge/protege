"""P8 exit-gate audit 2: DISCOVERY/GUIDED_LEARNING skip.

Confirms the thin thread's DISCOVERY -> GUIDED_LEARNING -> PRACTICE path
uses real, unconditional, already-tested P7 transitions -- not a
P8-invented shortcut -- and that no mastery change happens while passing
through them (i.e. skipping them conceals no required learning update).
"""

from __future__ import annotations

from _helpers import get_content, run_with_fake

from protege.session.machine import TRANSITIONS as P7_TRANSITIONS
from protege.session.machine import Event, S
from protege.thin_thread.scenario import happy_path_scenario


def test_discovery_and_guided_learning_timeouts_are_real_unconditional_p7_transitions() -> None:
    """These are exactly the entries ``packages/session-fsm``'s own golden
    traces #17/#18 exercise -- fetched directly from the canonical
    ``TRANSITIONS`` table, not re-declared here, so this test fails if P7
    ever changes them without this assertion being revisited."""
    discovery_timeout = P7_TRANSITIONS[(S.DISCOVERY, Event.TIMEOUT)]
    assert len(discovery_timeout) == 1
    assert discovery_timeout[0].to == S.GUIDED_LEARNING
    assert discovery_timeout[0].guard.__name__ == "_always"

    guided_learning_timeout = P7_TRANSITIONS[(S.GUIDED_LEARNING, Event.TIMEOUT)]
    assert len(guided_learning_timeout) == 1
    assert guided_learning_timeout[0].to == S.PRACTICE
    assert guided_learning_timeout[0].guard.__name__ == "_always"


def test_discovery_and_guided_learning_states_appear_but_move_no_mastery() -> None:
    content = get_content()
    result = run_with_fake(happy_path_scenario(), content)

    assert S.DISCOVERY in result.state_sequence
    assert S.GUIDED_LEARNING in result.state_sequence

    # Only two responses are scored before EXPLANATION: the diagnostic item
    # and the practice item. If DISCOVERY/GUIDED_LEARNING silently produced
    # evidence or a mastery update of their own, this count would be wrong.
    pre_teach_back_evidence = [
        e for e in result.evidence if e.kind == "response" and e.weight == 1.0
    ]
    assert len(pre_teach_back_evidence) == 2
