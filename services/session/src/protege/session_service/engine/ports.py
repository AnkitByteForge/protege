"""Adapts the real P5 (Sprout) / P6 (Diagnostician) roles to the P7
orchestrator's narrow ``SproutPort``/``DiagnosticianPort`` protocols.

Structurally identical to ``protege.thin_thread.engine``'s own private
``_SproutPortAdapter``/``_DiagnosticianPortAdapter`` (that module's own
docstring: those two classes are exactly this adaptation) -- reimplemented
here, not imported, because they are module-private to ``thin_thread`` and
this service constructs a fresh adapter per HTTP request (not once per
in-process run), needing its own lifecycle: one adapter pair is built per
``POST /events`` call, seeded with whatever prior-turn dialogue the runtime
has (there is no cross-request dialogue history to carry beyond what
``run_teach_back_turn`` itself needs per call).
"""

from __future__ import annotations

from collections.abc import Sequence

from protege.contracts import (
    DiagnosisResult,
    Explanation,
    Misconception,
    MisconceptionCode,
    SproutTurn,
)
from protege.llm.router import ModelRouter
from protege.roles.diagnostician import DiagnosticContext, diagnose
from protege.roles.sprout import (
    SproutDialogueTurn,
    SproutGenerationResult,
    SproutGenerator,
    SproutState,
)
from protege.thin_thread.ids import IdAllocator


class SproutPortAdapter:
    """One teach-back turn's worth of ``SproutPort`` -- construct fresh per
    ``POST /events`` request; ``prior_turns`` seeds whatever dialogue
    history the caller already has (this service does not persist a
    running Sprout dialogue transcript beyond ``turns`` rows, so a fresh
    adapter's ``prior_turns`` starts empty each call, matching what a
    single teach-back turn's generation actually needs -- Sprout speaks
    once per call, not a whole conversation at once)."""

    def __init__(
        self,
        generator: SproutGenerator,
        *,
        item_stem: str,
        correct_answer: str,
        ids: IdAllocator,
        prior_turns: Sequence[SproutDialogueTurn] = (),
    ) -> None:
        self._generator = generator
        self._item_stem = item_stem
        self._correct_answer = correct_answer
        self._ids = ids
        self.prior_turns: list[SproutDialogueTurn] = list(prior_turns)
        self.results: list[SproutGenerationResult] = []

    def __call__(
        self, *, misconception_code: MisconceptionCode, turn_index: int, resolution_belief: float
    ) -> SproutTurn:
        state = SproutState(
            misconception_id=misconception_code,
            resolution_belief=resolution_belief,
            turn_index=turn_index,
        )
        result = self._generator.generate_turn(
            state=state,
            item_stem=self._item_stem,
            correct_answer=self._correct_answer,
            prior_turns=tuple(self.prior_turns),
            trace_id=self._ids.next("trace_sprout"),
        )
        self.results.append(result)
        self.prior_turns.append(SproutDialogueTurn(speaker="sprout", text=result.turn.utterance))
        return result.turn

    def record_child_turn(self, text: str) -> None:
        self.prior_turns.append(SproutDialogueTurn(speaker="child", text=text))


class DiagnosticianPortAdapter:
    def __init__(self, router: ModelRouter, ids: IdAllocator) -> None:
        self._router = router
        self._ids = ids
        self.results: list[DiagnosisResult] = []

    def __call__(
        self, explanation: Explanation, misconception_set: Sequence[Misconception]
    ) -> DiagnosisResult:
        result = diagnose(
            self._router,
            DiagnosticContext(explanation=explanation, misconception_set=misconception_set),
            trace_id=self._ids.next("trace_diag"),
        )
        self.results.append(result)
        return result
