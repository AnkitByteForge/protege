"""The P8 thin-thread runner (roadmap P8).

Wires the real FSM/orchestrator (P7), Sprout (P5), Diagnostician (P6), and
the deterministic learning engine (P2) into one executable run:

    FSM -> Sprout -> Diagnostician -> mastery -> verification -> claim

Every deterministic decision (BKT, misconception Bayes, the mastery
threshold, evidence construction, FSM transitions) is made by calling the
existing packages named above -- nothing here recomputes their math.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from protege.authoring.loader import ContentPack, load_content_pack
from protege.contracts import (
    DiagnosisResult,
    Evidence,
    EvidenceKind,
    Explanation,
    JSONValue,
    LearningItem,
    MasteryOutcome,
    Misconception,
    MisconceptionBelief,
    MisconceptionCode,
    MisconceptionState,
    SproutTurn,
    TextExplanation,
    TransferItem,
)
from protege.learning_engine import (
    ResponseObservation,
    TeachingEpisodeObservation,
    ThresholdDecision,
    TransferObservationInput,
    bkt_update,
    build_response_evidence,
    build_teaching_episode_evidence,
    build_transfer_evidence,
    validate_answer,
)
from protege.llm.router import ModelRouter
from protege.roles.beliefs import apply_diagnosis_to_beliefs
from protege.roles.diagnostician import DiagnosticContext, diagnose
from protege.roles.sprout import (
    SproutDialogueTurn,
    SproutGenerationResult,
    SproutGenerator,
    SproutState,
)
from protege.session.machine import Event, S, SessionContext
from protege.session.orchestrator import SessionOrchestrator

from .ids import IdAllocator
from .scenario import (
    BKT_PARAMETERS,
    INITIAL_P_KNOWN,
    TEACHING_EXPLANATION_TEXT,
    Scenario,
    ThinThreadItems,
    numeric_answer_text,
    resolve_items,
    resolve_misconception,
    resolve_skill,
)

TraceSink = Callable[[str], None]


@dataclass
class ThinThreadResult:
    """Everything a caller (the CLI, or a test) needs from one run."""

    scenario_name: str
    context: SessionContext
    final_state: S
    state_sequence: tuple[S, ...]
    evidence: list[Evidence] = field(default_factory=list)
    claim_evidence_ids: list[str] = field(default_factory=list)
    mastery_outcome: MasteryOutcome | None = None
    threshold_decision: ThresholdDecision | None = None
    misconception_belief: MisconceptionBelief | None = None
    sprout_attempts: list[SproutGenerationResult] = field(default_factory=list)
    diagnoses: list[DiagnosisResult] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)


class _SproutPortAdapter:
    """Adapts :class:`~protege.roles.sprout.SproutGenerator` to the
    orchestrator's narrow ``SproutPort`` protocol, while keeping every
    ``SproutGenerationResult`` (fallback/validator detail) around for the
    trace -- the protocol itself only returns a ``SproutTurn``."""

    def __init__(
        self, generator: SproutGenerator, *, item_stem: str, correct_answer: str, ids: IdAllocator
    ) -> None:
        self._generator = generator
        self._item_stem = item_stem
        self._correct_answer = correct_answer
        self._ids = ids
        self.prior_turns: list[SproutDialogueTurn] = []
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


class _DiagnosticianPortAdapter:
    """Adapts :func:`~protege.roles.diagnostician.diagnose` to the
    orchestrator's ``DiagnosticianPort`` protocol, keeping every result."""

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


def _update_belief(
    diagnosis: DiagnosisResult, misconception: Misconception, belief: dict[str, float]
) -> dict[str, float]:
    """Deterministic misconception-belief update from one teach-back
    diagnosis (roadmap P8 flow step 10).

    A thin wrapper over the real, already-shipped
    :func:`~protege.roles.beliefs.apply_diagnosis_to_beliefs` (P6) --
    P8 invents no formula of its own here. That function's own documented
    behaviour is authoritative and is used exactly as written: it
    Bayes-updates a belief from UNRESOLVED evidence (via the real P2
    :func:`~protege.learning_engine.misconception_belief_update`), and
    deliberately leaves a RESOLVED label's belief **unchanged** ("only
    genuinely new UNRESOLVED evidence... moves a belief" -- its own
    docstring). No canonical document specifies a numeric formula for
    "what a teach-back resolution does to p_holds", so none is invented
    here; the resolution itself is recorded categorically, via
    ``MisconceptionBelief.state`` (see ``run_thin_thread``), not by moving
    this number. ``test_resolution_does_not_move_the_numeric_belief`` in
    ``packages/thin-thread/tests/test_belief_convention.py`` locks this in
    so it cannot silently regress into a P8-local alternative formula.
    """
    updated: dict[str, float] = apply_diagnosis_to_beliefs(
        diagnosis, misconception_set=[misconception], priors=belief
    )
    return updated


class _Trace:
    def __init__(self, sink: TraceSink) -> None:
        self._sink = sink
        self.lines: list[str] = []

    def __call__(self, text: str) -> None:
        self.lines.append(text)
        self._sink(text)

    def blank(self) -> None:
        self("")

    def header(self, title: str) -> None:
        self.blank()
        self(f"=== {title} ===")

    def transition(self, orchestrator: SessionOrchestrator, event: Event, from_state: S) -> S:
        new_state = orchestrator.advance(event)
        self(f"FSM  {from_state} --[{event}]--> {new_state}")
        return new_state


def _result_line(correct: bool, before: float, after: float) -> str:
    status = "correct" if correct else "incorrect"
    return f"{status}  P(knows) {before:.2f} -> {after:.2f}"


def _json_value(value: object) -> JSONValue:
    """Narrow one payload value to :data:`~protege.contracts.JSONValue`,
    recursively. Raises ``TypeError`` on a genuinely non-JSON value rather
    than silently asserting it safe -- see :func:`_json_payload`."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    raise TypeError(
        f"evidence payload value {value!r} ({type(value).__name__}) is not JSON-compatible"
    )


def _json_payload(payload: Mapping[str, object]) -> dict[str, JSONValue]:
    """Narrow a P2 :class:`~protege.learning_engine.BuiltEvidence.payload`
    -- typed ``dict[str, object]`` because ``packages/learning-engine`` has
    no dependency on ``packages/contracts`` (docs/DECISIONS.md D6, D8) --
    into the ``dict[str, JSONValue]``
    :class:`~protege.contracts.Evidence.payload` requires.

    Every value ``evidence_builder`` actually constructs is a JSON
    primitive (see ``build_response_evidence``,
    ``build_transfer_evidence``, ``build_teaching_episode_evidence``), so
    this is a real per-value type check, not a cast -- it performs no data
    conversion and changes no evidence content; it only proves, value by
    value, what was already true.
    """
    return {key: _json_value(value) for key, value in payload.items()}


def _score_learning_item(
    item: LearningItem, *, correct: bool, ids: IdAllocator, unaided: bool
) -> tuple[bool, Evidence, str]:
    correct_text = numeric_answer_text(item.correct_answer)
    child_text = (
        correct_text if correct else (item.distractors[0].value if item.distractors else "0/99")
    )
    result = validate_answer(child_text, correct_text)
    observation = ResponseObservation(
        item_id=item.item_id,
        source_event_id=ids.next("evt"),
        correct=result.is_correct,
        unaided=unaided,
    )
    built = build_response_evidence(observation)
    evidence = Evidence(
        id=ids.next("e"),
        kind=EvidenceKind.RESPONSE,
        source_event_id=built.source_event_id,
        weight=built.weight,
        payload=_json_payload(built.payload),
    )
    return result.is_correct, evidence, child_text


def _score_transfer_item(
    item: TransferItem, *, correct: bool, ids: IdAllocator
) -> tuple[bool, Evidence, str]:
    correct_text = numeric_answer_text(item.correct_answer)
    child_text = correct_text if correct else "0/99"
    result = validate_answer(child_text, correct_text)
    observation = TransferObservationInput(
        item_id=item.item_id,
        source_event_id=ids.next("evt"),
        representation=str(item.representation),
        result=result.is_correct,
    )
    built = build_transfer_evidence(observation)
    evidence = Evidence(
        id=ids.next("e"),
        kind=EvidenceKind.TRANSFER,
        source_event_id=built.source_event_id,
        weight=built.weight,
        payload=_json_payload(built.payload),
    )
    return result.is_correct, evidence, child_text


def run_thin_thread(
    scenario: Scenario,
    router: ModelRouter,
    *,
    content: ContentPack | None = None,
    trace_sink: TraceSink | None = None,
) -> ThinThreadResult:
    """Run one complete P8 thin-thread session end to end.

    Returns a :class:`ThinThreadResult`. ``mastery_outcome`` is ``None``
    whenever the session does not reach a verified-mastery decision in
    this run (e.g. INDEPENDENT_VERIFY looping back to GUIDED_LEARNING) --
    the claim is never fabricated to paper over that (P8 testing
    requirement #4: "verification failure does not falsely produce
    verified mastery").
    """
    trace = _Trace(trace_sink if trace_sink is not None else (lambda _line: None))
    content = content if content is not None else load_content_pack()
    items: ThinThreadItems = resolve_items(content)
    misconception = resolve_misconception(content)
    skill = resolve_skill(content)
    ids = IdAllocator()
    evidence: list[Evidence] = []
    belief: dict[str, float] = {misconception.code: misconception.prevalence_prior}

    trace.header(f"P8 THIN THREAD -- scenario={scenario.name!r}")
    trace(f"skill={skill.code} misconception={misconception.code} ({misconception.title})")
    trace(
        f"initial P(knows)={INITIAL_P_KNOWN:.2f}  "
        f"initial P({misconception.code})={belief[misconception.code]:.2f}"
    )

    context = SessionContext(p_known=INITIAL_P_KNOWN)
    sprout_generator = SproutGenerator(router, content=content)
    sprout_adapter = _SproutPortAdapter(
        sprout_generator,
        item_stem=items.diagnostic.stem,
        correct_answer=items.diagnostic.correct_answer,
        ids=ids,
    )
    diagnostician_adapter = _DiagnosticianPortAdapter(router, ids)
    orchestrator = SessionOrchestrator(
        sprout=sprout_adapter, diagnostician=diagnostician_adapter, context=context
    )

    # --- ARRIVAL -> SPROUT_TEASE -> DIAGNOSTIC ------------------------------
    trace.header("SESSION INITIALIZATION / ARRIVAL")
    trace.transition(orchestrator, Event.PROFILE_LOADED, S.ARRIVAL)
    trace.transition(orchestrator, Event.TEASE_ELAPSED, S.SPROUT_TEASE)

    # --- DIAGNOSTIC ----------------------------------------------------------
    trace.header("DIAGNOSTIC")
    trace(f"> {items.diagnostic.stem}")
    correct, item_evidence, child_text = _score_learning_item(
        items.diagnostic, correct=scenario.diagnostic_correct, ids=ids, unaided=False
    )
    evidence.append(item_evidence)
    before = context.p_known
    context.p_known = bkt_update(context.p_known, correct=correct, params=BKT_PARAMETERS)
    trace(f"  {child_text}")
    trace(_result_line(correct, before, context.p_known))
    trace(f"evidence: {item_evidence.evidence_id} (response, weight={item_evidence.weight})")
    from_state = context.current
    new_state = trace.transition(orchestrator, Event.PRIORS_SET, from_state)

    # --- DISCOVERY / GUIDED_LEARNING -----------------------------------------
    # P8's scope is "no UI" and six hardcoded items -- none of which is
    # DISCOVERY/GUIDED_LEARNING content (roadmap P8 Components; matches
    # ARCHITECTURE.md §42's own thin-thread transcript, which likewise
    # shows no discovery/guided-learning step). The TIMEOUT events fired
    # below are real, unconditional entries already in
    # `protege.session.machine.TRANSITIONS` --
    # `(S.DISCOVERY, Event.TIMEOUT) -> S.GUIDED_LEARNING` and
    # `(S.GUIDED_LEARNING, Event.TIMEOUT) -> S.PRACTICE` -- exercised by
    # `packages/session-fsm`'s own golden traces #17/#18, not a P8-invented
    # shortcut. Neither state performs a P2 learning-engine operation in
    # this or any other flow (mastery only moves on a *scored* item --
    # DIAGNOSTIC/PRACTICE/INDEPENDENT_VERIFY/TRANSFER -- never on dwelling
    # in DISCOVERY/GUIDED_LEARNING itself), so skipping them conceals no
    # required learning update; see
    # `test_discovery_guided_learning_skip.py` for the regression lock.
    if new_state == S.DISCOVERY:
        trace.header("DISCOVERY (no discovery content authored for P8's thin slice)")
        new_state = trace.transition(orchestrator, Event.TIMEOUT, S.DISCOVERY)
    if new_state == S.GUIDED_LEARNING:
        trace.header("GUIDED_LEARNING (no guided-learning content authored for P8's thin slice)")
        new_state = trace.transition(orchestrator, Event.TIMEOUT, S.GUIDED_LEARNING)

    # --- PRACTICE --------------------------------------------------------
    trace.header("PRACTICE")
    trace(f"> {items.practice.stem}")
    correct, item_evidence, child_text = _score_learning_item(
        items.practice, correct=scenario.practice_correct, ids=ids, unaided=False
    )
    evidence.append(item_evidence)
    before = context.p_known
    exit_state = orchestrator.score_practice_item(correct=correct)
    context.p_known = bkt_update(before, correct=correct, params=BKT_PARAMETERS)
    trace(f"  {child_text}")
    trace(_result_line(correct, before, context.p_known))
    trace(f"evidence: {item_evidence.evidence_id} (response, weight={item_evidence.weight})")
    if exit_state is None:
        trace(f"PRACTICE  1/{4} items attempted -- P8 exits early via the real")
        trace("          'timeout: move on with partial evidence' path (no further")
        trace("          practice items authored in the 6-item thin-thread budget).")
        new_state = trace.transition(orchestrator, Event.TIMEOUT, S.PRACTICE)
    else:
        new_state = exit_state
        trace(f"FSM  PRACTICE --[item_scored]--> {new_state}")

    # --- EXPLANATION / READINESS ------------------------------------------
    trace.header("EXPLANATION")
    trace("> Explain why.")
    trace(f"  {TEACHING_EXPLANATION_TEXT}")
    from_state = context.current
    new_state = trace.transition(orchestrator, Event.EXPLANATION_CAPTURED, from_state)
    trace(f"READINESS: P(knows)={context.p_known:.2f} -> {new_state}")

    if new_state == S.ESCALATE_TO_HUMAN:
        trace.header("ESCALATE_TO_HUMAN")
        trace("Three below-threshold encounters -- warm human handoff, no claim this session.")
        return _finish(scenario, context, orchestrator, evidence, ids, trace, None, None)
    if new_state == S.GUIDED_LEARNING:
        trace.header("GUIDED_LEARNING (readiness recovery loop)")
        trace("P(knows) below 0.35 -- would loop back through PRACTICE; out of the")
        trace("6-item thin-thread budget, so P8 stops here for this run.")
        return _finish(scenario, context, orchestrator, evidence, ids, trace, None, None)

    # --- SPROUT_SETUP / SPROUT_SETUP_HARD -----------------------------------
    trace.header("SPROUT SETUP")
    trace(
        f"deterministic policy selects misconception_id={misconception.code!r} "
        f"(authored prevalence_prior={misconception.prevalence_prior:.2f} for {skill.code})"
    )
    from_state = context.current
    new_state = trace.transition(orchestrator, Event.MISCONCEPTION_SELECTED, from_state)

    # --- TEACH_BACK ----------------------------------------------------------
    trace.header("TEACH_BACK")
    turn_iter = iter(scenario.teach_back_turns)
    while context.current == S.TEACH_BACK:
        turn_script = next(turn_iter, None)
        if turn_script is None:
            trace("(scenario's scripted turns exhausted without resolving)")
            context.current = orchestrator.handle_timeout()
            break
        explanation = TextExplanation(text=turn_script.child_text)
        sprout_turn, diagnosis, new_state = orchestrator.run_teach_back_turn(
            misconception_code=misconception.code,
            explanation=explanation,
            misconception_set=[misconception],
        )
        sprout_adapter.record_child_turn(turn_script.child_text)
        attempt = sprout_adapter.results[-1]
        last_call = attempt.attempts[-1] if attempt.attempts else None
        if attempt.used_fallback:
            status = f"fallback ({attempt.fallback_reason})"
        else:
            status = "model-generated"
        trace(
            f"SPROUT turn {context.teach_back_turns - 1}: {status} "
            f"provider={last_call.provider if last_call else None} "
            f"model={last_call.model_id if last_call else None}"
        )
        trace(f'  SPROUT: "{sprout_turn.utterance}"')
        trace(f"  > {turn_script.child_text}")
        label_summary = [
            (label.misconception_code, str(label.state), round(label.confidence, 2))
            for label in diagnosis.labels
        ]
        trace(f"DIAGNOSIS: abstained={diagnosis.abstained} labels={label_summary}")
        belief = _update_belief(diagnosis, misconception, belief)
        belief_value = belief[misconception.code]
        trace(f"BELIEF UPDATE (deterministic Bayes): P({misconception.code}) -> {belief_value:.4f}")
        if new_state == S.COACH_ASSIST:
            hint = next(
                (i for i in content.interventions if i.misconception_code == misconception.code),
                None,
            )
            trace.header("COACH_ASSIST (guided recovery)")
            if hint is not None:
                trace(f"authored intervention {hint.intervention_id}: {hint.script}")
            context.current = orchestrator.advance(Event.HINT_DELIVERED)
            trace(f"FSM  COACH_ASSIST --[hint_delivered]--> {context.current}")

    final_teach_back_state = context.current
    trace(
        f"TEACH_BACK exit: resolved={context.misconception_resolved} state={final_teach_back_state}"
    )

    teaching_episode_built = build_teaching_episode_evidence(
        TeachingEpisodeObservation(
            episode_id=ids.next("te"),
            source_event_id=ids.next("evt"),
            resolved=context.misconception_resolved,
            resolution_turn=context.teach_back_turns if context.misconception_resolved else None,
        )
    )
    teaching_evidence = Evidence(
        id=ids.next("e"),
        kind=EvidenceKind.TEACHING_EPISODE,
        source_event_id=teaching_episode_built.source_event_id,
        weight=teaching_episode_built.weight,
        payload=_json_payload(teaching_episode_built.payload),
    )
    evidence.append(teaching_evidence)
    trace(
        f"evidence: {teaching_evidence.evidence_id} "
        f"(teaching_episode, weight={teaching_evidence.weight})"
    )

    misconception_belief = MisconceptionBelief(
        learner_id="lrn_thin_thread",
        misconception_code=misconception.code,
        p_holds=belief[misconception.code],
        state=(
            MisconceptionState.RESOLVED
            if context.misconception_resolved
            else MisconceptionState.UNRESOLVED
        ),
        resolution_evidence_id=(
            teaching_evidence.evidence_id if context.misconception_resolved else None
        ),
    )

    # --- REFLECTION ----------------------------------------------------------
    trace.header("REFLECTION")
    trace("> What did Sprout get wrong at first?")
    trace('  "He thought more pieces meant a bigger fraction."')
    from_state = context.current
    new_state = trace.transition(orchestrator, Event.REFLECTION_CAPTURED, from_state)

    # --- INDEPENDENT_VERIFY --------------------------------------------------
    trace.header("INDEPENDENT VERIFY (no hints, no Sprout)")
    verify_exit: S | None = None
    for index, item in enumerate(items.verify):
        trace(f"> {item.stem}")
        correct, item_evidence, child_text = _score_learning_item(
            item, correct=scenario.verify_correct[index], ids=ids, unaided=True
        )
        evidence.append(item_evidence)
        before = context.p_known
        verify_exit = orchestrator.score_verify_item(correct=correct)
        context.p_known = bkt_update(before, correct=correct, params=BKT_PARAMETERS)
        trace(f"  {child_text}")
        trace(_result_line(correct, before, context.p_known))
        trace(
            f"evidence: {item_evidence.evidence_id} "
            f"(response, unaided, weight={item_evidence.weight})"
        )
    trace(f"VERIFY: {context.verify_correct_count}/{len(items.verify)} correct")
    assert verify_exit is not None
    trace(f"FSM  INDEPENDENT_VERIFY --[verify_items_scored]--> {verify_exit}")

    if verify_exit == S.GUIDED_LEARNING:
        trace.header("GUIDED_LEARNING (verification recovery loop)")
        trace("Fewer than 2/3 correct -- would loop back through PRACTICE; out of the")
        trace("6-item thin-thread budget, so P8 stops here. NO mastery claim is made.")
        return _finish(
            scenario, context, orchestrator, evidence, ids, trace, None, misconception_belief
        )

    # --- TRANSFER --------------------------------------------------------
    trace.header("TRANSFER")
    trace(f"> {items.transfer.stem}")
    correct, transfer_evidence, child_text = _score_transfer_item(
        items.transfer, correct=scenario.transfer_correct, ids=ids
    )
    evidence.append(transfer_evidence)
    before = context.p_known
    context.p_known = bkt_update(before, correct=correct, params=BKT_PARAMETERS)
    trace(f"  {child_text}")
    trace(_result_line(correct, before, context.p_known))
    trace(
        f"evidence: {transfer_evidence.evidence_id} (transfer, weight={transfer_evidence.weight})"
    )
    from_state = context.current
    new_state = trace.transition(orchestrator, Event.TRANSFER_ATTEMPTED, from_state)

    # --- MASTERY_DECISION --------------------------------------------------
    trace.header("MASTERY_DECISION (deterministic thresholds only)")
    decision, new_state = orchestrator.compute_mastery_decision(p_known_before=INITIAL_P_KNOWN)
    trace(
        f"p_known_met={decision.p_known_met} "
        f"unaided_correct_met={decision.unaided_correct_met} "
        f"transfer_attempted_met={decision.transfer_attempted_met} "
        f"-> mastery_verified={decision.mastery_verified}"
    )
    trace(f"mastery_delta={context.mastery_delta:.4f}")
    trace(f"FSM  MASTERY_DECISION --[mastery_computed]--> {new_state}")

    # --- REWARD --------------------------------------------------------
    if new_state == S.REWARD:
        all_verified = context.verify_correct_count == len(items.verify)
        reward_eligible = context.mastery_delta > 0.0 and all_verified
        trace.header("REWARD")
        trace(
            f"reward_eligible = mastery_delta>0 AND unaided_verification_passed = {reward_eligible}"
        )
        new_state = trace.transition(orchestrator, Event.REWARD_PROCESSED, S.REWARD)

    # --- SUMMARY / claim -----------------------------------------------------
    trace.header("SUMMARY / PROOF")
    mastery_outcome: MasteryOutcome | None = None
    claim_evidence_ids: list[str] = []
    if decision.mastery_verified:
        verify_evidence_ids = (
            e.evidence_id for e in evidence if e.kind == EvidenceKind.RESPONSE and e.weight == 3.0
        )
        claim_evidence_ids = [
            teaching_evidence.evidence_id,
            *verify_evidence_ids,
            transfer_evidence.evidence_id,
        ]
        caveats = [
            "transfer confirmed on number line only"
            if correct
            else "transfer attempted but not yet verified"
        ]
        if context.misconception_resolved:
            caveats.append(
                f"{misconception.code} posterior reflects only Bayesian updates from "
                "unresolved teach-back evidence, if any; resolution itself is recorded "
                "as a state, not a further belief update (no canonical formula exists "
                "for one -- see MisconceptionBelief.state)"
            )
        else:
            caveats.append(
                f"Sprout's {misconception.code} misconception was NOT resolved during "
                "teach-back this session (diagnosis abstained, or the evidence was "
                "inconclusive within the turn cap) -- this claim is proven independently, "
                "via unaided verification and transfer, per ARCHITECTURE.md's separation "
                "of the mastery claim from misconception resolution; the teach-back "
                "episode itself is not."
            )
        mastery_outcome = MasteryOutcome(
            p_known_before=INITIAL_P_KNOWN,
            p_known_after=context.p_known,
            misconception_posteriors={misconception.code: belief[misconception.code]},
            transfer_verified=correct,
            claim="Compares unit fractions",
            evidence_ids=claim_evidence_ids,
            caveats=caveats,
        )
        trace(f"CLAIM: {mastery_outcome.claim!r}  evidence: {claim_evidence_ids}")
        for caveat in mastery_outcome.caveats:
            trace(f"CAVEAT: {caveat}")
    else:
        trace("No verified-mastery claim this session (thresholds not met).")
    from_state = context.current
    new_state = trace.transition(orchestrator, Event.ARTIFACTS_PERSISTED, from_state)

    # --- RETRIEVAL_SCHEDULE / COMPLETE --------------------------------------
    trace.header("RETRIEVAL_SCHEDULE")
    from_state = context.current
    new_state = trace.transition(orchestrator, Event.SCHEDULE_COMPUTED, from_state)

    trace.header("COMPLETE")
    return ThinThreadResult(
        scenario_name=scenario.name,
        context=context,
        final_state=context.current,
        state_sequence=orchestrator.journal.state_sequence,
        evidence=evidence,
        claim_evidence_ids=claim_evidence_ids,
        mastery_outcome=mastery_outcome,
        threshold_decision=decision,
        misconception_belief=misconception_belief,
        sprout_attempts=sprout_adapter.results,
        diagnoses=diagnostician_adapter.results,
        trace=trace.lines,
    )


def _finish(
    scenario: Scenario,
    context: SessionContext,
    orchestrator: SessionOrchestrator,
    evidence: list[Evidence],
    ids: IdAllocator,
    trace: _Trace,
    mastery_outcome: MasteryOutcome | None,
    misconception_belief: MisconceptionBelief | None,
) -> ThinThreadResult:
    """Early-exit result builder (escalation, or an out-of-budget recovery
    loop) -- never fabricates a claim."""
    return ThinThreadResult(
        scenario_name=scenario.name,
        context=context,
        final_state=context.current,
        state_sequence=orchestrator.journal.state_sequence,
        evidence=evidence,
        claim_evidence_ids=[],
        mastery_outcome=mastery_outcome,
        threshold_decision=None,
        misconception_belief=misconception_belief,
        sprout_attempts=[],
        diagnoses=[],
        trace=trace.lines,
    )
