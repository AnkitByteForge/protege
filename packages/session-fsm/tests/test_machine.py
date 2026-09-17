"""Core FSM mechanics (roadmap P7): ``step()``, ordered guard evaluation,
``IllegalTransition``, and the closed event vocabulary that keeps model
output from ever choosing a transition.
"""

from __future__ import annotations

import pytest

from protege.session.machine import (
    Event,
    IllegalTransition,
    S,
    SessionContext,
    Transition,
    step,
)


def test_step_returns_new_state_and_mutates_context_in_place() -> None:
    context = SessionContext()
    result = step(context, Event.PROFILE_LOADED)
    assert result == S.SPROUT_TEASE
    assert context.current == S.SPROUT_TEASE


def test_step_raises_illegal_transition_for_unregistered_event() -> None:
    context = SessionContext(current=S.ARRIVAL)
    with pytest.raises(IllegalTransition) as excinfo:
        step(context, Event.HINT_DELIVERED)
    assert excinfo.value.state == S.ARRIVAL
    assert excinfo.value.event == Event.HINT_DELIVERED
    # A rejected event must never move the session.
    assert context.current == S.ARRIVAL


def test_step_raises_illegal_transition_when_every_guard_fails() -> None:
    """(PRACTICE, ITEM_SCORED) is registered, but both of its guards
    require either 3 consecutive errors or 4 items attempted -- neither
    holds on a freshly-entered PRACTICE context."""
    context = SessionContext(current=S.PRACTICE)
    with pytest.raises(IllegalTransition):
        step(context, Event.ITEM_SCORED)


def test_ordered_guards_first_match_wins() -> None:
    """DIAGNOSTIC's PRIORS_SET has an ordered [high-prior -> PRACTICE,
    default -> DISCOVERY] list; both a context that matches the first
    guard and one that doesn't must resolve correctly."""
    high_prior = SessionContext(current=S.DIAGNOSTIC, p_known=0.9)
    assert step(high_prior, Event.PRIORS_SET) == S.PRACTICE

    low_prior = SessionContext(current=S.DIAGNOSTIC, p_known=0.2)
    assert step(low_prior, Event.PRIORS_SET) == S.DISCOVERY


def test_transition_default_guard_always_passes() -> None:
    assert Transition(S.COMPLETE).guard(SessionContext()) is True


def test_session_context_rejects_out_of_range_probabilities() -> None:
    with pytest.raises(ValueError):
        SessionContext(p_known=1.5)
    with pytest.raises(ValueError):
        SessionContext(resolution_belief=-0.1)


def test_session_context_rejects_negative_counters() -> None:
    with pytest.raises(ValueError):
        SessionContext(loops=-1)


# --- "No LLM may choose the next state" / routing-instruction immunity -----


def test_unrecognised_event_string_cannot_be_constructed_as_an_event() -> None:
    """Event is a closed StrEnum: a string that doesn't name one of its
    members (e.g. something a model's own output might contain, like
    "complete" or "skip_to_reward") cannot even be turned into an `Event`
    to pass to `step()` in the first place."""
    with pytest.raises(ValueError):
        Event("go_directly_to_complete")


@pytest.mark.parametrize("event", list(Event))
def test_every_event_is_rejected_from_states_that_never_registered_it(event: Event) -> None:
    """For every (state, event) pair NOT present in TRANSITIONS, step()
    must raise -- proving there is no back door: a model cannot cause a
    transition merely by an orchestrator naively forwarding some event
    name for the wrong state."""
    from protege.session.machine import TRANSITIONS

    for state in S:
        if (state, event) in TRANSITIONS:
            continue
        context = SessionContext(current=state)
        with pytest.raises(IllegalTransition):
            step(context, event)
