"""Structural coverage of the transition table (roadmap P7 exit criteria:
"All 21 states reachable in tests"; Testing: "Every state has a timeout
path and a failure path").
"""

from __future__ import annotations

from protege.contracts import SessionState
from protege.session.machine import TERMINAL_STATES, TRANSITIONS, Event, S, SessionContext


def test_canonical_state_enum_has_exactly_twenty_one_members() -> None:
    """docs/DECISIONS.md D1: 21 canonical states. `S` is
    `protege.contracts.SessionState` -- not redefined here."""
    assert S is SessionState
    assert len(list(S)) == 21


def test_all_twenty_one_states_are_reachable() -> None:
    """Static graph-reachability check: every `to` referenced anywhere in
    TRANSITIONS, plus the implicit start state ARRIVAL, must cover all 21
    states. (`test_golden_traces.py` additionally proves many of these
    are reachable *dynamically*, by actually walking `step()` through a
    real scripted session -- this test only proves the edge exists.)"""
    reachable: set[S] = {S.ARRIVAL}
    for (_state, _event), transitions in TRANSITIONS.items():
        for transition in transitions:
            reachable.add(transition.to)
    assert reachable == set(S)


def test_every_non_terminal_state_has_a_timeout_and_failure_path() -> None:
    non_terminal = set(S) - TERMINAL_STATES
    missing_timeout = {s for s in non_terminal if (s, Event.TIMEOUT) not in TRANSITIONS}
    missing_failure = {s for s in non_terminal if (s, Event.FAILURE) not in TRANSITIONS}
    assert not missing_timeout, f"states missing a timeout path: {missing_timeout}"
    assert not missing_failure, f"states missing a failure path: {missing_failure}"


def test_terminal_states_have_no_outgoing_transitions() -> None:
    for state in TERMINAL_STATES:
        outgoing = [key for key in TRANSITIONS if key[0] == state]
        assert outgoing == [], f"{state} is terminal but has transitions: {outgoing}"


def test_terminal_states_are_exactly_complete_and_abandoned() -> None:
    assert frozenset({S.COMPLETE, S.ABANDONED}) == TERMINAL_STATES


def test_every_registered_transition_list_is_non_empty() -> None:
    for key, transitions in TRANSITIONS.items():
        assert transitions, f"{key} is registered with an empty transition list"


def test_every_transition_guard_eventually_has_a_default_or_covers_all_cases() -> None:
    """Every registered (state, event) list must end in an unconditional
    (default-guard) transition OR be a pattern this test explicitly
    allow-lists as intentionally partial. Only PRACTICE's ITEM_SCORED is
    such a case: both its transitions are guarded (3 consecutive errors /
    4 items attempted), by design -- the orchestrator's contract is to
    only fire ITEM_SCORED once one of those is already known to hold (see
    `.orchestrator.SessionOrchestrator.score_practice_item`). This guards
    against a future edit accidentally adding another guarded-only list
    with no catch-all elsewhere.
    """
    partial_by_design = {(S.PRACTICE, Event.ITEM_SCORED)}
    for key, transitions in TRANSITIONS.items():
        if key in partial_by_design:
            continue
        last = transitions[-1]
        # The default guard is the module-level `_always` function; every
        # other guard here is a lambda. This checks the *effective*
        # property (always passes on a fresh context) rather than
        # reaching into the private `_always` name.
        assert last.guard(_blank_context_for(key[0])), (
            f"{key}'s last transition ({last.to}) is not an unconditional "
            "fallback, and this pair isn't allow-listed as partial"
        )


def _blank_context_for(state: S) -> SessionContext:
    return SessionContext(current=state)
