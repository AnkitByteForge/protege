"""Domain-specific exceptions for the P7 session FSM & orchestrator.

Mirrors the ``LearningEngineError`` convention in
``packages/learning-engine/src/protege/learning_engine/errors.py``: one base
class per package, one concrete class per distinct failure mode, never a
bare ``ValueError``/``RuntimeError`` for something a caller needs to branch
on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .machine import Event, S


class SessionFSMError(Exception):
    """Base class for every P7 domain error."""


class IllegalTransition(SessionFSMError):
    """Raised by :func:`protege.session.machine.step` when no transition is
    registered for ``(state, event)``, or one is registered but every guard
    in its ordered list returns ``False``.

    This is also what protects the "no LLM may choose the next state" /
    "model output containing routing instructions must be ignored" rules
    (roadmap P7): :class:`~protege.session.machine.Event` is a closed
    ``StrEnum`` and :data:`~protege.session.machine.TRANSITIONS` only
    recognises the finite set of ``(state, event)`` pairs it explicitly
    enumerates. Anything else -- including a string an LLM's output
    happened to contain that looks like a routing instruction -- simply
    fails to match any transition and lands here instead of moving the
    session anywhere.
    """

    def __init__(self, state: S, event: Event) -> None:
        self.state = state
        self.event = event
        super().__init__(f"illegal transition: no guard passed for state={state!r} event={event!r}")
