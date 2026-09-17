"""PROTÉGÉ session FSM & orchestrator (roadmap P7).

Plain Python transition table + guard functions, persisted to
``session_states`` from P9 on (addendum §3.9, §1.1 #1). No XState, no
LangGraph. "Give the system a spine that no model can move" (roadmap P7
Purpose).

See ``docs/DECISIONS.md`` D1 for the canonical 21-state set (already
defined at ``protege.contracts.SessionState``, aliased here as ``S``) and
``.machine``'s module docstring for how ``READINESS`` -- a choice
pseudostate, not a 22nd journaled state -- is implemented.
"""

from .constants import (
    DIAGNOSTIC_HIGH_PRIOR_THRESHOLD,
    IDLE_ELIGIBLE_STATES,
    IDLE_TIMEOUT_SECONDS,
    INDEPENDENT_VERIFY_ITEMS,
    INDEPENDENT_VERIFY_MIN_CORRECT,
    MAX_READINESS_LOOPS,
    PRACTICE_MAX_CONSECUTIVE_ERRORS,
    PRACTICE_MIN_ITEMS_ATTEMPTED,
    READINESS_HIGH_THRESHOLD,
    READINESS_LOW_THRESHOLD,
    SESSION_HARD_CAP_SECONDS,
    STATE_TIMEOUT_SECONDS,
    TEACH_BACK_MAX_TURNS,
    TEACH_BACK_STUCK_TURNS,
)
from .errors import IllegalTransition, SessionFSMError
from .machine import (
    TERMINAL_STATES,
    TRANSITIONS,
    Event,
    Journal,
    S,
    SessionContext,
    Transition,
    TransitionRecord,
    step,
)
from .orchestrator import DiagnosticianPort, SessionOrchestrator, SproutPort

__version__ = "0.1.0"

__all__ = [  # noqa: RUF022
    # Core FSM
    "S",
    "Event",
    "SessionContext",
    "Transition",
    "TRANSITIONS",
    "TERMINAL_STATES",
    "step",
    # Journal
    "TransitionRecord",
    "Journal",
    # Orchestrator
    "SessionOrchestrator",
    "SproutPort",
    "DiagnosticianPort",
    # Errors
    "SessionFSMError",
    "IllegalTransition",
    # Constants
    "READINESS_LOW_THRESHOLD",
    "READINESS_HIGH_THRESHOLD",
    "MAX_READINESS_LOOPS",
    "DIAGNOSTIC_HIGH_PRIOR_THRESHOLD",
    "PRACTICE_MAX_CONSECUTIVE_ERRORS",
    "PRACTICE_MIN_ITEMS_ATTEMPTED",
    "TEACH_BACK_MAX_TURNS",
    "TEACH_BACK_STUCK_TURNS",
    "INDEPENDENT_VERIFY_ITEMS",
    "INDEPENDENT_VERIFY_MIN_CORRECT",
    "IDLE_TIMEOUT_SECONDS",
    "SESSION_HARD_CAP_SECONDS",
    "STATE_TIMEOUT_SECONDS",
    "IDLE_ELIGIBLE_STATES",
]
