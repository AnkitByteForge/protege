"""The P7 session orchestrator (roadmap P7; addendum §3.9, §3.10).

Wraps :mod:`.machine` with the pieces a real session needs around the bare
FSM: a journal that records every transition automatically, wall-clock
timeout/idle handling, and the call sites where P5 (Sprout) and P6
(Diagnostician) plug in -- through structural :class:`typing.Protocol`
ports rather than a concrete import, because ``feature/p5-sprout`` and
``feature/p6-diagnostician`` are not yet merged to ``main`` (see this
package's own dependency note below). Wiring the *content*-driven,
end-to-end session (which item, which misconception, what BKT parameters)
is explicitly roadmap P8's job ("A single
``python -m protege.thin_thread`` entry point wiring FSM -> Sprout ->
Diagnostician -> mastery -> verification"); this module provides the
mechanism P8 wires, not the wiring itself.

**Why ports, not imports.** ``SproutPort``/``DiagnosticianPort`` below are
typed to match the real call shapes in
``packages/roles/src/protege/roles/{sprout,diagnostician}.py`` on those
branches exactly (``SproutGenerator.generate_turn`` and ``diagnose``,
verified by reading both files) -- but return/accept only types that
already live in ``protege.contracts`` (``SproutTurn``, ``DiagnosisResult``,
``Explanation``, ``Misconception``), which P1 merged to ``main`` already.
Once P5/P6 merge, adapting their real callables to these two Protocols is
a drop-in (a thin lambda/partial at the call site), with zero changes
needed here.

**"The orchestrator calls roles; roles never call the orchestrator."**
Enforced by construction: ``sprout``/``diagnostician`` are plain callables
injected into :class:`SessionOrchestrator`, with no reference back to it
or to :class:`~protege.session.machine.SessionContext`. There is no path
by which a role implementation could request a transition.

**"Any model output resembling a routing instruction is ignored."**
:meth:`SessionOrchestrator.run_teach_back_turn` reads exactly three typed
fields off ``DiagnosisResult`` (``labels[].misconception_code``,
``labels[].state``, ``understanding_signals``, ``abstained``) to decide
``resolved``/``stuck`` -- never ``SproutTurn.utterance`` or any other free
text, and never anything that could name a state or event. Combined with
:class:`~protege.session.machine.Event` being a closed ``StrEnum`` (see
``.machine``'s module docstring), there is no field on either role's
output this module would even attempt to interpret as a transition
request.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from protege.contracts import (
    DiagnosisResult,
    Explanation,
    Misconception,
    MisconceptionCode,
    MisconceptionState,
    SproutTurn,
)
from protege.learning_engine import ThresholdDecision, ThresholdInputs, evaluate_mastery_threshold

from .constants import (
    INDEPENDENT_VERIFY_ITEMS,
    PRACTICE_MAX_CONSECUTIVE_ERRORS,
    PRACTICE_MIN_ITEMS_ATTEMPTED,
)
from .machine import Event, Journal, S, SessionContext, TransitionRecord, step

__all__ = ["DiagnosticianPort", "SessionOrchestrator", "SproutPort"]


class SproutPort(Protocol):
    """Structural match for ``SproutGenerator.generate_turn`` (roadmap P5,
    ``feature/p5-sprout``, not yet merged). One in-character turn for the
    misconception this teach-back dwell is about; the correct answer is
    never a parameter here, matching P5's own rule that Sprout's context
    cannot contain it by construction.
    """

    def __call__(
        self,
        *,
        misconception_code: MisconceptionCode,
        turn_index: int,
        resolution_belief: float,
    ) -> SproutTurn: ...


class DiagnosticianPort(Protocol):
    """Structural match for ``diagnose`` (roadmap P6,
    ``feature/p6-diagnostician``, not yet merged). One piece of teach-back
    evidence in, one closed-set :class:`~protege.contracts.DiagnosisResult`
    out -- abstention included, never a guess.
    """

    def __call__(
        self, explanation: Explanation, misconception_set: Sequence[Misconception]
    ) -> DiagnosisResult: ...


class SessionOrchestrator:
    """Drives one session's FSM + journal + role calls (roadmap P7:
    "``protege/session/machine.py`` + ``orchestrator.py``").

    Every state-changing method here ultimately calls :func:`~.machine.step`
    exactly once and records the result to :attr:`journal` -- this class
    adds no transition logic of its own beyond the small, explicitly
    documented dwell-counter bookkeeping each method performs before
    calling :meth:`advance` (e.g. counting practice items, teach-back
    turns). Deterministic state authority stays entirely in
    :data:`~.machine.TRANSITIONS`.
    """

    def __init__(
        self,
        *,
        sprout: SproutPort,
        diagnostician: DiagnosticianPort,
        context: SessionContext | None = None,
    ) -> None:
        self.context = context if context is not None else SessionContext()
        self.journal = Journal()
        self._sprout = sprout
        self._diagnostician = diagnostician

    # -- Generic step/journal/timeout/failure --------------------------------

    def advance(self, event: Event) -> S:
        """Fire ``event`` for the current state and journal the result.
        Raises :class:`~.errors.IllegalTransition` exactly as
        :func:`~.machine.step` does -- this method adds journaling, not
        forgiveness."""
        from_state = self.context.current
        new_state = step(self.context, event)
        record = TransitionRecord(from_state=from_state, to_state=new_state, event=event)
        self.journal.append(record)
        return new_state

    def handle_timeout(self) -> S:
        """Fire :attr:`~.machine.Event.TIMEOUT` for the current state
        (roadmap P7: "timeout handler"). The wall-clock deadline itself is
        the caller's concern (``constants.STATE_TIMEOUT_SECONDS`` gives
        each state's budget); this method only fires the resulting event
        once the caller has decided the deadline passed."""
        return self.advance(Event.TIMEOUT)

    def handle_failure(self) -> S:
        """Fire :attr:`~.machine.Event.FAILURE` for the current state
        (roadmap P7: "failure handling")."""
        return self.advance(Event.FAILURE)

    def handle_idle_timeout(self) -> S:
        """Fire :attr:`~.machine.Event.IDLE_TIMEOUT`. Only registered for
        states in ``constants.IDLE_ELIGIBLE_STATES``; calling this from any
        other state raises :class:`~.errors.IllegalTransition`, which is
        the intended guard -- there is nothing to be "idle" about during a
        synchronous, no-child-input state."""
        return self.advance(Event.IDLE_TIMEOUT)

    # -- PRACTICE --------------------------------------------------------

    def score_practice_item(self, *, correct: bool) -> S | None:
        """Record one PRACTICE response. Returns the new state once an
        exit condition is reached (roadmap: 4 items attempted, or 3
        consecutive errors); returns ``None`` while still dwelling in
        PRACTICE, matching that ARCHITECTURE.md §9's mermaid diagram draws
        no self-loop for PRACTICE -- the FSM itself is only consulted once
        an exit is actually reached, not once per item."""
        self.context.items_attempted += 1
        self.context.consecutive_errors = 0 if correct else self.context.consecutive_errors + 1
        if (
            self.context.consecutive_errors >= PRACTICE_MAX_CONSECUTIVE_ERRORS
            or self.context.items_attempted >= PRACTICE_MIN_ITEMS_ATTEMPTED
        ):
            return self.advance(Event.ITEM_SCORED)
        return None

    # -- TEACH_BACK (calls both P5 and P6 ports) --------------------------

    def run_teach_back_turn(
        self,
        *,
        misconception_code: MisconceptionCode,
        explanation: Explanation,
        misconception_set: Sequence[Misconception],
    ) -> tuple[SproutTurn, DiagnosisResult, S]:
        """One teach-back turn: Sprout speaks, the child's explanation is
        diagnosed, then :attr:`~.machine.Event.TURN_COMPLETED` fires
        (roadmap P7 AI field: "the orchestrator *calls* roles").

        ``resolved``/``stuck`` are derived from ``DiagnosisResult`` here
        using an orchestrator-level interpretation that is **informational,
        not canonical** (in the docs/DECISIONS.md D11 sense: no PROTÉGÉ
        document specifies what "stuck" means over a `DiagnosisResult`
        sequence) -- resolved iff any label for this turn's misconception
        reports :attr:`~protege.contracts.MisconceptionState.RESOLVED`;
        "no forward progress" (no resolution and no positive
        ``understanding_signals``, or an outright abstention) increments
        ``stuck_turns``, any progress resets it. Whoever next owns P6/P11
        should review this heuristic before depending on it.
        """
        sprout_turn = self._sprout(
            misconception_code=misconception_code,
            turn_index=self.context.teach_back_turns,
            resolution_belief=self.context.resolution_belief,
        )
        diagnosis = self._diagnostician(explanation, misconception_set)

        resolved_now = any(
            label.misconception_code == misconception_code
            and label.state == MisconceptionState.RESOLVED
            for label in diagnosis.labels
        )
        made_progress = resolved_now or bool(diagnosis.understanding_signals)
        self.context.stuck_turns = 0 if made_progress else self.context.stuck_turns + 1
        if resolved_now:
            self.context.misconception_resolved = True
            self.context.resolution_belief = 1.0
        self.context.teach_back_turns += 1

        new_state = self.advance(Event.TURN_COMPLETED)
        return sprout_turn, diagnosis, new_state

    # -- INDEPENDENT_VERIFY ------------------------------------------------

    def score_verify_item(self, *, correct: bool) -> S | None:
        """Record one INDEPENDENT_VERIFY response (no hints, no Sprout --
        enforced by this method simply never calling either port). Returns
        the new state once all 3 items are attempted; ``None`` while still
        dwelling."""
        self.context.verify_items_attempted += 1
        if correct:
            self.context.verify_correct_count += 1
        if self.context.verify_items_attempted >= INDEPENDENT_VERIFY_ITEMS:
            return self.advance(Event.VERIFY_ITEMS_SCORED)
        return None

    # -- MASTERY_DECISION (real P2 consumption) -----------------------------

    def compute_mastery_decision(self, *, p_known_before: float) -> tuple[ThresholdDecision, S]:
        """MASTERY_DECISION: deterministic thresholds only (roadmap P7 /
        ARCHITECTURE.md §9 table: "deterministic thresholds only, not
        LLM"). Calls P2's real
        :func:`protege.learning_engine.evaluate_mastery_threshold` --
        never reimplemented here (roadmap P7: "Do not duplicate mastery
        logic").

        ``context.mastery_delta`` (which gates the REWARD-vs-SUMMARY
        guard, ARCHITECTURE.md §9 mermaid: "any mastery delta") is the
        continuous ``p_known`` change and is deliberately **not** the same
        boolean as ``ThresholdDecision.mastery_verified``: a learner can
        make real, reward-worthy progress (``mastery_delta > 0``) without
        yet clearing P2's full mastery bar. Both are returned so the
        caller can build the proof-artifact claim from the stricter
        ``ThresholdDecision`` while the FSM branches on the simpler delta.
        """
        self.context.mastery_delta = self.context.p_known - p_known_before
        decision = evaluate_mastery_threshold(
            ThresholdInputs(
                p_known=self.context.p_known,
                unaided_correct_count=self.context.verify_correct_count,
                transfer_attempted_count=1 if self.context.transfer_attempted else 0,
            )
        )
        new_state = self.advance(Event.MASTERY_COMPUTED)
        return decision, new_state
