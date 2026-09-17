"""The P7 session FSM (roadmap P7; addendum §3.9; docs/DECISIONS.md D1).

Plain Python. No XState, no LangGraph (addendum §3.9, §3.12; roadmap P7
Backend field: "Plain Python -- no XState, no LangGraph"). A finite set of
states, a finite set of events, an ordered transition table, and guard
functions over an in-memory context -- nothing here can be "predicted only
at runtime": every legal transition is enumerable ahead of time (addendum
§3.2).

**States.** ``S`` is *not* redefined here: the 21 canonical states already
exist at ``protege.contracts.SessionState`` (docs/DECISIONS.md D1) --
defining a second ``StrEnum`` with the same members would be exactly the
"second source of truth for state already represented elsewhere" AGENTS.md
forbids. ``S`` is kept as a module-level alias purely so this module reads
the way addendum §3.9's own illustrative code does.

**READINESS.** The architecture draws ``READINESS`` as a Harel *choice
pseudostate* (ARCHITECTURE.md §9: ``state READINESS <<choice>>``), not a
21st journaled state -- and D1's canonical 21-member list (matching
addendum §3.9's actual ``S`` enum) confirms this: ``READINESS`` is not one
of the 21 names. It is implemented here exactly as addendum §3.9 shows its
own ``EXPLANATION`` example: as the ordered guard list attached to
``(S.EXPLANATION, Event.EXPLANATION_CAPTURED)`` (see
``_READINESS_TRANSITIONS`` below). Evaluating it costs one guard pass, is
fully deterministic, and produces no separate dwell/timeout of its own --
consistent with the architecture's own row for it ("READINESS (choice) |
FSM guards | Fully | pure code").

**No LLM may choose the next state.** ``Event`` is a closed ``StrEnum``,
and ``TRANSITIONS`` only recognises the finite ``(state, event)`` pairs it
explicitly enumerates below. An orchestrator (``.orchestrator``) is the
only caller of :func:`step`, and it only ever constructs ``Event`` members
from its own typed, validated business logic -- never from raw model text.
Any string that does not correspond to a registered ``(state, event)``
pair -- including one a compromised or careless prompt caused a model to
emit -- fails to match any transition and raises :class:`IllegalTransition`
rather than moving the session anywhere (see
``test_every_event_is_rejected_from_states_that_never_registered_it`` in
``tests/test_machine.py`` for the property test).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from protege.contracts import SessionState as S

from .constants import (
    DIAGNOSTIC_HIGH_PRIOR_THRESHOLD,
    INDEPENDENT_VERIFY_MIN_CORRECT,
    MAX_READINESS_LOOPS,
    PRACTICE_MAX_CONSECUTIVE_ERRORS,
    PRACTICE_MIN_ITEMS_ATTEMPTED,
    READINESS_HIGH_THRESHOLD,
    READINESS_LOW_THRESHOLD,
    TEACH_BACK_MAX_TURNS,
    TEACH_BACK_STUCK_TURNS,
)
from .errors import IllegalTransition

__all__ = [
    "TERMINAL_STATES",
    "TRANSITIONS",
    "Event",
    "IllegalTransition",
    "Journal",
    "S",
    "SessionContext",
    "Transition",
    "TransitionRecord",
    "step",
]


# =============================================================================
# Events -- closed vocabulary of transition triggers
# =============================================================================


class Event(StrEnum):
    """Every legal trigger for a state transition (roadmap P7: the input
    alphabet of the FSM's 5-tuple, addendum §3.2).

    Three events -- :attr:`TIMEOUT`, :attr:`FAILURE`, :attr:`IDLE_TIMEOUT`
    -- are generic and reused across every state that registers them,
    rather than being spelled out per-state (``practice_timeout``,
    ``teach_back_timeout``, ...): the *destination* already varies by
    ``(state, event)`` through ``TRANSITIONS``, so a per-state event name
    would only duplicate information the dict key already carries. The
    remaining events are each specific to exactly one state's normal
    (non-degraded) exit, mirroring the edge labels in ARCHITECTURE.md §9's
    mermaid diagram.
    """

    # Normal per-state exits (ARCHITECTURE.md §9 mermaid edge labels).
    PROFILE_LOADED = "profile_loaded"
    TEASE_ELAPSED = "tease_elapsed"
    PRIORS_SET = "priors_set"
    EXPLORATION_DONE = "exploration_done"
    WORKED_EXAMPLE_COMPLETE = "worked_example_complete"
    ITEM_SCORED = "item_scored"
    EXPLANATION_CAPTURED = "explanation_captured"
    MISCONCEPTION_SELECTED = "misconception_selected"
    TURN_COMPLETED = "turn_completed"
    HINT_DELIVERED = "hint_delivered"
    REFLECTION_CAPTURED = "reflection_captured"
    VERIFY_ITEMS_SCORED = "verify_items_scored"
    TRANSFER_ATTEMPTED = "transfer_attempted"
    MASTERY_COMPUTED = "mastery_computed"
    REWARD_PROCESSED = "reward_processed"
    ARTIFACTS_PERSISTED = "artifacts_persisted"
    SCHEDULE_COMPUTED = "schedule_computed"
    ESCALATION_ACKNOWLEDGED = "escalation_acknowledged"

    # Generic, reused across every state that registers them.
    TIMEOUT = "timeout"
    FAILURE = "failure"
    IDLE_TIMEOUT = "idle_timeout"


TERMINAL_STATES: frozenset[S] = frozenset({S.COMPLETE, S.ABANDONED})
"""States with no outgoing transitions (ARCHITECTURE.md §9: both flow into
``[*]``). Deliberately excluded from ``TRANSITIONS`` and from the
"every state has a timeout/failure path" test, which is scoped to
non-terminal states -- there is nothing left to time out on after the
session has already ended."""


# =============================================================================
# Session context -- what guards read
# =============================================================================


@dataclass
class SessionContext:
    """In-memory session context (roadmap P7: "in-memory session context").

    Deliberately narrow: only the derived signals the FSM's own guards
    need to read, not the full P2 mastery state (BKT priors, per-skill
    ``BKTParameters``, authored misconception likelihood tables) -- that
    state is P2/content-owned and lives with whatever drives this
    orchestrator (P8's thin thread today; the session service from P10
    on). Keeping *those* full quantities off this dataclass avoids a
    second copy of state P2 already owns; this dataclass only ever holds
    the handful of scalars ``TRANSITIONS``'s guards are written against.

    Mutable (not frozen): counters here are incremented in place by
    ``Transition.effect`` as the session progresses, and a session's
    context is naturally a single mutable record for its lifetime --
    matching ``SproutState``'s own precedent in the P5 branch for "one
    mutable-by-convention record per session actor."
    """

    current: S = S.ARRIVAL
    p_known: float = 0.0
    resolution_belief: float = 0.0
    loops: int = 0
    consecutive_errors: int = 0
    items_attempted: int = 0
    teach_back_turns: int = 0
    misconception_resolved: bool = False
    stuck_turns: int = 0
    verify_items_attempted: int = 0
    verify_correct_count: int = 0
    transfer_attempted: bool = False
    mastery_delta: float = 0.0

    def __post_init__(self) -> None:
        probabilities = (("p_known", self.p_known), ("resolution_belief", self.resolution_belief))
        for name, prob in probabilities:
            if not 0.0 <= prob <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {prob!r}")
        for name, value in (
            ("loops", self.loops),
            ("consecutive_errors", self.consecutive_errors),
            ("items_attempted", self.items_attempted),
            ("teach_back_turns", self.teach_back_turns),
            ("stuck_turns", self.stuck_turns),
            ("verify_items_attempted", self.verify_items_attempted),
            ("verify_correct_count", self.verify_correct_count),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0, got {value!r}")


# =============================================================================
# Transitions
# =============================================================================

GuardFn = Callable[[SessionContext], bool]
EffectFn = Callable[[SessionContext], None]


def _always(context: SessionContext) -> bool:
    return True


def _no_effect(context: SessionContext) -> None:
    return None


@dataclass(frozen=True)
class Transition:
    """One candidate edge out of a ``(state, event)`` pair.

    ``guard`` is a pure predicate over :class:`SessionContext` -- never an
    LLM call, never I/O (roadmap P7: "explicit deterministic state
    authority"). ``effect`` is a small, deterministic, in-place mutation of
    the context applied only when this transition is the one actually
    taken -- used here for exactly the bookkeeping that is intrinsically
    tied to *which edge fired* rather than to dwelling in one state (the
    ``loops`` recovery counter, and resetting a freshly-(re)entered
    state's own dwell counters). It is not a general escape hatch: guards
    stay pure, and ``effect`` never decides *where* to go, only records
    that a specific, already-chosen edge was taken.
    """

    to: S
    guard: GuardFn = _always
    effect: EffectFn = _no_effect


def _increment_loops(context: SessionContext) -> None:
    context.loops += 1


def _reset_practice_dwell(context: SessionContext) -> None:
    context.items_attempted = 0
    context.consecutive_errors = 0


def _reset_teach_back_dwell(context: SessionContext) -> None:
    context.teach_back_turns = 0
    context.stuck_turns = 0
    context.misconception_resolved = False


def _reset_verify_dwell(context: SessionContext) -> None:
    context.verify_items_attempted = 0
    context.verify_correct_count = 0


def _mark_transfer_attempted(context: SessionContext) -> None:
    context.transfer_attempted = True


# --- READINESS (ARCHITECTURE.md §9 choice pseudostate) ----------------------
# Roadmap P7 exact spec: "p_known < 0.35 -> guided/recovery path; 0.35 <=
# p_known <= 0.80 -> teach-back; > 0.80 -> harder variant. escalation at 3
# loops." Order matches addendum §3.9's own example: the loop-exhaustion
# guard is checked first (an ordered guard list is a priority list -- the
# first guard that passes wins, so a learner who is BOTH below 0.35 AND out
# of loops must escalate, not loop a 4th time).
_READINESS_TRANSITIONS: list[Transition] = [
    Transition(S.ESCALATE_TO_HUMAN, guard=lambda c: c.loops >= MAX_READINESS_LOOPS),
    Transition(
        S.GUIDED_LEARNING,
        guard=lambda c: c.p_known < READINESS_LOW_THRESHOLD,
        effect=_increment_loops,
    ),
    Transition(S.SPROUT_SETUP, guard=lambda c: c.p_known <= READINESS_HIGH_THRESHOLD),
    Transition(S.SPROUT_SETUP_HARD),  # default: p_known > 0.80
]

TRANSITIONS: dict[tuple[S, Event], list[Transition]] = {
    # --- ARRIVAL -------------------------------------------------------
    (S.ARRIVAL, Event.PROFILE_LOADED): [Transition(S.SPROUT_TEASE)],
    (S.ARRIVAL, Event.TIMEOUT): [Transition(S.SPROUT_TEASE)],
    (S.ARRIVAL, Event.FAILURE): [Transition(S.SPROUT_TEASE)],
    (S.ARRIVAL, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- SPROUT_TEASE ----------------------------------------------------
    # §9 table: timeout 10s -> "skip; no learning cost".
    (S.SPROUT_TEASE, Event.TEASE_ELAPSED): [Transition(S.DIAGNOSTIC)],
    (S.SPROUT_TEASE, Event.TIMEOUT): [Transition(S.DIAGNOSTIC)],
    (S.SPROUT_TEASE, Event.FAILURE): [Transition(S.DIAGNOSTIC)],
    (S.SPROUT_TEASE, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- DIAGNOSTIC --------------------------------------------------------
    # §9 mermaid: "DIAGNOSTIC --> PRACTICE: prior mastery high" else
    # DISCOVERY. §9 table: timeout/failure 180s -> "default priors from
    # grade band" -- treated as the safe (non-skip) default path.
    (S.DIAGNOSTIC, Event.PRIORS_SET): [
        Transition(S.PRACTICE, guard=lambda c: c.p_known >= DIAGNOSTIC_HIGH_PRIOR_THRESHOLD),
        Transition(S.DISCOVERY),
    ],
    (S.DIAGNOSTIC, Event.TIMEOUT): [Transition(S.DISCOVERY)],
    (S.DIAGNOSTIC, Event.FAILURE): [Transition(S.DISCOVERY)],
    (S.DIAGNOSTIC, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- DISCOVERY -----------------------------------------------------
    (S.DISCOVERY, Event.EXPLORATION_DONE): [Transition(S.GUIDED_LEARNING)],
    (S.DISCOVERY, Event.TIMEOUT): [Transition(S.GUIDED_LEARNING)],
    (S.DISCOVERY, Event.FAILURE): [Transition(S.GUIDED_LEARNING)],
    (S.DISCOVERY, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- GUIDED_LEARNING -------------------------------------------------
    # §37 screen table failure column: "Authored fallback".
    (S.GUIDED_LEARNING, Event.WORKED_EXAMPLE_COMPLETE): [
        Transition(S.PRACTICE, effect=_reset_practice_dwell)
    ],
    (S.GUIDED_LEARNING, Event.TIMEOUT): [Transition(S.PRACTICE, effect=_reset_practice_dwell)],
    (S.GUIDED_LEARNING, Event.FAILURE): [Transition(S.PRACTICE, effect=_reset_practice_dwell)],
    (S.GUIDED_LEARNING, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- PRACTICE ------------------------------------------------------
    # §9 mermaid: two independent exits. The orchestrator only fires
    # ITEM_SCORED once one of these has actually become true (see
    # .orchestrator); ordered so a 3rd-consecutive-error exit is checked
    # before the 4-items exit, matching "3 consecutive errors" reading as
    # an early-exit condition.
    (S.PRACTICE, Event.ITEM_SCORED): [
        Transition(
            S.GUIDED_LEARNING,
            guard=lambda c: c.consecutive_errors >= PRACTICE_MAX_CONSECUTIVE_ERRORS,
        ),
        Transition(
            S.EXPLANATION, guard=lambda c: c.items_attempted >= PRACTICE_MIN_ITEMS_ATTEMPTED
        ),
    ],
    (S.PRACTICE, Event.TIMEOUT): [Transition(S.EXPLANATION)],
    (S.PRACTICE, Event.FAILURE): [Transition(S.EXPLANATION)],
    (S.PRACTICE, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- EXPLANATION / READINESS -----------------------------------------
    # All three events funnel through the same READINESS guard list: *how*
    # the explanation was captured (normally, via a timeout fallback to
    # cards per §9 table, or via a validator failure) never changes what
    # p_known/loops say to do next -- only evidence quality, which is the
    # orchestrator's concern before it fires the event, not the FSM's.
    (S.EXPLANATION, Event.EXPLANATION_CAPTURED): _READINESS_TRANSITIONS,
    (S.EXPLANATION, Event.TIMEOUT): _READINESS_TRANSITIONS,
    (S.EXPLANATION, Event.FAILURE): _READINESS_TRANSITIONS,
    (S.EXPLANATION, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- SPROUT_SETUP / SPROUT_SETUP_HARD --------------------------------
    # §9 table: timeout/failure 5s -> "pick highest-prior misconception"
    # (still proceeds to TEACH_BACK; which misconception was picked is the
    # orchestrator/policy's concern, not the FSM's).
    (S.SPROUT_SETUP, Event.MISCONCEPTION_SELECTED): [
        Transition(S.TEACH_BACK, effect=_reset_teach_back_dwell)
    ],
    (S.SPROUT_SETUP, Event.TIMEOUT): [Transition(S.TEACH_BACK, effect=_reset_teach_back_dwell)],
    (S.SPROUT_SETUP, Event.FAILURE): [Transition(S.TEACH_BACK, effect=_reset_teach_back_dwell)],
    (S.SPROUT_SETUP_HARD, Event.MISCONCEPTION_SELECTED): [
        Transition(S.TEACH_BACK, effect=_reset_teach_back_dwell)
    ],
    (S.SPROUT_SETUP_HARD, Event.TIMEOUT): [
        Transition(S.TEACH_BACK, effect=_reset_teach_back_dwell)
    ],
    (S.SPROUT_SETUP_HARD, Event.FAILURE): [
        Transition(S.TEACH_BACK, effect=_reset_teach_back_dwell)
    ],
    # --- TEACH_BACK ------------------------------------------------------
    # §9 mermaid draws an explicit self-loop here (unlike PRACTICE/
    # INDEPENDENT_VERIFY): every turn is individually diagnosed, so the
    # orchestrator calls step() once per turn, not just at exit. Ordered
    # so the hard 6-turn cap / resolution always outranks "stuck" -- a
    # learner who resolves it on turn 6 exits to REFLECTION, not
    # COACH_ASSIST, even if they were also flagged stuck that same turn.
    (S.TEACH_BACK, Event.TURN_COMPLETED): [
        Transition(
            S.REFLECTION,
            guard=lambda c: c.misconception_resolved or c.teach_back_turns >= TEACH_BACK_MAX_TURNS,
        ),
        Transition(S.COACH_ASSIST, guard=lambda c: c.stuck_turns >= TEACH_BACK_STUCK_TURNS),
        Transition(S.TEACH_BACK),  # still under the cap, unresolved, not (yet) stuck
    ],
    (S.TEACH_BACK, Event.TIMEOUT): [Transition(S.REFLECTION)],
    (S.TEACH_BACK, Event.FAILURE): [Transition(S.REFLECTION)],
    (S.TEACH_BACK, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- COACH_ASSIST ----------------------------------------------------
    (S.COACH_ASSIST, Event.HINT_DELIVERED): [
        Transition(S.TEACH_BACK, effect=lambda c: setattr(c, "stuck_turns", 0))
    ],
    (S.COACH_ASSIST, Event.TIMEOUT): [
        Transition(S.TEACH_BACK, effect=lambda c: setattr(c, "stuck_turns", 0))
    ],
    (S.COACH_ASSIST, Event.FAILURE): [
        Transition(S.TEACH_BACK, effect=lambda c: setattr(c, "stuck_turns", 0))
    ],
    (S.COACH_ASSIST, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- REFLECTION ------------------------------------------------------
    # §37 screen table: "Skippable" -- timeout/failure both just skip on.
    (S.REFLECTION, Event.REFLECTION_CAPTURED): [
        Transition(S.INDEPENDENT_VERIFY, effect=_reset_verify_dwell)
    ],
    (S.REFLECTION, Event.TIMEOUT): [Transition(S.INDEPENDENT_VERIFY, effect=_reset_verify_dwell)],
    (S.REFLECTION, Event.FAILURE): [Transition(S.INDEPENDENT_VERIFY, effect=_reset_verify_dwell)],
    (S.REFLECTION, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- INDEPENDENT_VERIFY ------------------------------------------------
    # §9 mermaid: "2 of 3 correct" -> TRANSFER, "under 2 of 3" -> back to
    # GUIDED_LEARNING (a readiness recovery loop, same counter as the
    # READINESS choice node -- see ``_increment_loops``). §9 table:
    # timeout/failure 240s -> "partial credit, mark low-confidence": moves
    # forward to TRANSFER rather than looping, since a stalled/failed
    # verification is not evidence the learner scored under 2 of 3.
    (S.INDEPENDENT_VERIFY, Event.VERIFY_ITEMS_SCORED): [
        Transition(
            S.TRANSFER,
            guard=lambda c: c.verify_correct_count >= INDEPENDENT_VERIFY_MIN_CORRECT,
        ),
        Transition(S.GUIDED_LEARNING, effect=_increment_loops),
    ],
    (S.INDEPENDENT_VERIFY, Event.TIMEOUT): [Transition(S.TRANSFER)],
    (S.INDEPENDENT_VERIFY, Event.FAILURE): [Transition(S.TRANSFER)],
    (S.INDEPENDENT_VERIFY, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- TRANSFER --------------------------------------------------------
    # §37 screen table failure column: "Records unverified" -- timeout and
    # failure proceed WITHOUT the transfer_attempted effect, so
    # MASTERY_DECISION correctly sees it as not attempted.
    (S.TRANSFER, Event.TRANSFER_ATTEMPTED): [
        Transition(S.MASTERY_DECISION, effect=_mark_transfer_attempted)
    ],
    (S.TRANSFER, Event.TIMEOUT): [Transition(S.MASTERY_DECISION)],
    (S.TRANSFER, Event.FAILURE): [Transition(S.MASTERY_DECISION)],
    (S.TRANSFER, Event.IDLE_TIMEOUT): [Transition(S.ABANDONED)],
    # --- MASTERY_DECISION --------------------------------------------------
    # §9 table: "never fails" / "—" for timeout. Deterministic thresholds
    # only (P2's threshold_service -- see .orchestrator); registered here
    # defensively so this state is not a special case in the "every state
    # has a timeout/failure path" test, on the conservative branch (no
    # reward on an unresolved computation).
    (S.MASTERY_DECISION, Event.MASTERY_COMPUTED): [
        Transition(S.REWARD, guard=lambda c: c.mastery_delta > 0.0),
        Transition(S.SUMMARY),
    ],
    (S.MASTERY_DECISION, Event.TIMEOUT): [Transition(S.SUMMARY)],
    (S.MASTERY_DECISION, Event.FAILURE): [Transition(S.SUMMARY)],
    # --- REWARD --------------------------------------------------------
    (S.REWARD, Event.REWARD_PROCESSED): [Transition(S.SUMMARY)],
    (S.REWARD, Event.TIMEOUT): [Transition(S.SUMMARY)],
    (S.REWARD, Event.FAILURE): [Transition(S.SUMMARY)],
    # --- SUMMARY -------------------------------------------------------
    (S.SUMMARY, Event.ARTIFACTS_PERSISTED): [Transition(S.RETRIEVAL_SCHEDULE)],
    (S.SUMMARY, Event.TIMEOUT): [Transition(S.RETRIEVAL_SCHEDULE)],
    (S.SUMMARY, Event.FAILURE): [Transition(S.RETRIEVAL_SCHEDULE)],
    # --- RETRIEVAL_SCHEDULE ----------------------------------------------
    (S.RETRIEVAL_SCHEDULE, Event.SCHEDULE_COMPUTED): [Transition(S.COMPLETE)],
    (S.RETRIEVAL_SCHEDULE, Event.TIMEOUT): [Transition(S.COMPLETE)],
    (S.RETRIEVAL_SCHEDULE, Event.FAILURE): [Transition(S.COMPLETE)],
    # --- ESCALATE_TO_HUMAN -------------------------------------------------
    (S.ESCALATE_TO_HUMAN, Event.ESCALATION_ACKNOWLEDGED): [Transition(S.SUMMARY)],
    (S.ESCALATE_TO_HUMAN, Event.TIMEOUT): [Transition(S.SUMMARY)],
    (S.ESCALATE_TO_HUMAN, Event.FAILURE): [Transition(S.SUMMARY)],
    # --- COMPLETE / ABANDONED ----------------------------------------------
    # Terminal (ARCHITECTURE.md §9: both flow into `[*]`); intentionally no
    # entries -- see TERMINAL_STATES.
}


# =============================================================================
# step()
# =============================================================================


def step(context: SessionContext, event: Event) -> S:
    """Advance ``context`` by one FSM step (roadmap P7: ``step()``).

    Ordered guard evaluation: the first :class:`Transition` in
    ``TRANSITIONS[(context.current, event)]`` whose guard passes is taken
    -- its ``effect`` runs, ``context.current`` is updated, and the new
    state is returned. If no transition is registered for
    ``(context.current, event)``, or every registered guard returns
    ``False``, raises :class:`IllegalTransition` -- exactly addendum
    §3.9's own ``step()``, with the addition of ``effect`` (see
    :class:`Transition`).

    Pure with respect to the module: the only mutation is to ``context``
    itself (its counters via ``effect``, and ``current``). No I/O, no
    randomness, no clock read -- callers needing wall-clock timeout
    behaviour drive that from outside (see ``.orchestrator``), then call
    this with :attr:`Event.TIMEOUT`/:attr:`Event.FAILURE` like any other
    event.
    """
    for transition in TRANSITIONS.get((context.current, event), []):
        if transition.guard(context):
            transition.effect(context)
            context.current = transition.to
            return context.current
    raise IllegalTransition(context.current, event)


# =============================================================================
# Transition journal
# =============================================================================


@dataclass(frozen=True)
class TransitionRecord:
    """One journaled transition (roadmap P7: "transition journal").

    Roadmap P7 Data field: "Journal in memory this phase; persisted in P9"
    -- ``from_state``/``to_state``/``event``/``occurred_at`` are exactly
    the columns a future ``session_states`` row needs (addendum §3.9: "Every
    transition is appended to `session_states`"), kept deliberately as
    plain scalars (no ``protege.contracts`` dependency beyond ``S``) so a
    later P9 mapping to that table is a straight field copy.
    """

    from_state: S
    to_state: S
    event: Event
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class Journal:
    """Append-only in-memory record of every transition taken this session
    (roadmap P7: "transition journal"). Never rewritten in place --
    matching the append-only evidence/state principle already used
    elsewhere in this codebase (``packages/learning-engine``'s ``Evidence``
    contract docstring)."""

    def __init__(self) -> None:
        self._records: list[TransitionRecord] = []

    def append(self, record: TransitionRecord) -> None:
        self._records.append(record)

    @property
    def records(self) -> tuple[TransitionRecord, ...]:
        return tuple(self._records)

    @property
    def state_sequence(self) -> tuple[S, ...]:
        """``(start_state, *every to_state in order)`` -- the sequence a
        golden-trace test compares against."""
        if not self._records:
            return ()
        return (self._records[0].from_state, *(r.to_state for r in self._records))

    def __len__(self) -> int:
        return len(self._records)
