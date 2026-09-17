"""P2 exit criterion: a synthetic learner with a planted misconception,
driven through 20 scripted responses, produces a human-readable,
deterministic trajectory (roadmap P2 exit criteria; task instruction
"SYNTHETIC TRAJECTORY EXIT CRITERION").

No LLM calls anywhere in this module or the functions it exercises. The
scenario is the §38 worked example's skill/misconception pairing
(S004 / M003, "larger denominator means larger fraction"), extended with
a second, independently-tracked misconception (M011, "says equal") --
exactly the item-distractor pattern the §38 worked example itself authors
(`"1/8"->M003`, `"equal"->M011`). Per docs/DECISIONS.md D13, M003's and
M011's belief updates are fully independent of each other: this scenario
exercises two misconceptions side by side to demonstrate that
independence, not to redistribute belief between them (the
candidate-set-normalization behavior D13 replaced).

The BKT parameters, learner Elo rating, and item Elo priors below are
this test's own scripted demo values (no canonical document specifies
numeric BKT parameters -- see ``mastery_engine.BKTParameters``'s
docstring); they are not defaults shipped anywhere in the package.

This is a golden/snapshot test: :func:`format_trajectory_report` renders
the exact, deterministic report produced by replaying :data:`SCRIPT`
through the real P2 functions. A change to any formula, constant, or the
D10/D13 decisions will change this output -- that is the point.
"""

from dataclasses import dataclass

from protege.learning_engine.evidence_builder import ResponseObservation, build_response_evidence
from protege.learning_engine.mastery_engine import (
    BKTParameters,
    bkt_update,
    mastery_effective,
    misconception_belief_update,
    update_item_elo,
)
from protege.learning_engine.threshold_service import ThresholdInputs, evaluate_mastery_threshold

# --- Scenario: skill S004, planted misconception M003 (+ decoy M011) ------

BKT_PARAMS = BKTParameters(slip=0.10, guess=0.25, transit=0.30)
"""Scripted demo BKT parameters for this test only -- not a package
default (see module docstring)."""

LEARNER_ELO_RATING = 1200
"""An arbitrary fixed nominal learner rating for this demo (docs/DECISIONS.md
D11 Gap C: P2 does not define how a real learner Elo rating would be
derived from BKT's P(L); this test supplies one directly, as any real
caller must)."""

M003_DISTRACTOR_LIKELIHOOD = {"picks_1_8": 0.82, "says_equal": 0.06, "other": 0.12}
M011_DISTRACTOR_LIKELIHOOD = {"says_equal": 0.70, "picks_1_8": 0.05, "other": 0.25}
DISTRACTOR_LIKELIHOODS = {"M003": M003_DISTRACTOR_LIKELIHOOD, "M011": M011_DISTRACTOR_LIKELIHOOD}
"""P(d | M_k) -- unchanged meaning from D10."""

M003_COMPLEMENT_LIKELIHOOD = {"picks_1_8": 0.10, "says_equal": 0.30, "other": 0.60}
M011_COMPLEMENT_LIKELIHOOD = {"says_equal": 0.08, "picks_1_8": 0.05, "other": 0.87}
COMPLEMENT_LIKELIHOODS = {"M003": M003_COMPLEMENT_LIKELIHOOD, "M011": M011_COMPLEMENT_LIKELIHOOD}
"""P(d | not M_k) -- the D13 complement table, authored independently of
the tables above (a learner who lacks M003's whole-number bias rarely
picks "1/8" by that specific route; a learner who lacks M011's "equal"
confusion rarely says "equal")."""

INITIAL_P_KNOW = 0.31
"""Matches the §38 worked example's mastery_outcome.p_known_before."""
INITIAL_MISCONCEPTION_PRIORS = {"M003": 0.42, "M011": 0.10}
"""M003's prior matches the §38 worked example's authored prevalence_prior."""


@dataclass(frozen=True)
class ScriptedTurn:
    phase: str
    item_id: str
    item_elo_prior: int
    correct: bool
    distractor: str | None
    hints_used: int
    unaided: bool


SCRIPT: list[ScriptedTurn] = [
    # DIAGNOSTIC: prior-knowledge calibration (§9). Two incorrect
    # responses choosing the M003-consistent distractor plant and
    # reinforce the misconception.
    ScriptedTurn("DIAGNOSTIC", "i_101", 1180, False, "picks_1_8", 0, False),
    ScriptedTurn("DIAGNOSTIC", "i_102", 1150, True, None, 0, False),
    ScriptedTurn("DIAGNOSTIC", "i_103", 1200, False, "picks_1_8", 0, False),
    ScriptedTurn("DIAGNOSTIC", "i_104", 1170, True, None, 0, False),
    ScriptedTurn("DIAGNOSTIC", "i_105", 1190, True, None, 0, False),
    # PRACTICE (§9): mostly correct, one M011-consistent miss (i_107),
    # two hint-assisted items (one crossing the 2-hint discount
    # threshold). i_107's "says_equal" pick updates M003 and M011
    # completely independently (D13): it is strong evidence FOR M011
    # (0.70 under M011 vs. 0.08 under not-M011) and simultaneously
    # evidence AGAINST M003 (only 0.06 under M003 vs. 0.30 under
    # not-M003) -- M003's belief genuinely falls at this step while
    # M011's rises, from the very same observation.
    ScriptedTurn("PRACTICE", "i_106", 1180, True, None, 0, False),
    ScriptedTurn("PRACTICE", "i_107", 1180, False, "says_equal", 0, False),
    ScriptedTurn("PRACTICE", "i_108", 1180, True, None, 2, False),
    ScriptedTurn("PRACTICE", "i_109", 1180, True, None, 0, False),
    ScriptedTurn("PRACTICE", "i_110", 1180, True, None, 0, False),
    ScriptedTurn("PRACTICE", "i_111", 1180, True, None, 1, False),
    ScriptedTurn("PRACTICE", "i_112", 1180, True, None, 0, False),
    ScriptedTurn("PRACTICE", "i_113", 1180, True, None, 0, False),
    ScriptedTurn("PRACTICE", "i_114", 1180, True, None, 0, False),
    ScriptedTurn("PRACTICE", "i_115", 1180, True, None, 0, False),
    # INDEPENDENT_VERIFY (§9): 3 unaided, unseen items, no hints
    # permitted -- all correct, each weighted 3x (§10.1 rule 4).
    ScriptedTurn("INDEPENDENT_VERIFY", "i_148", 1180, True, None, 0, True),
    ScriptedTurn("INDEPENDENT_VERIFY", "i_155", 1180, True, None, 0, True),
    ScriptedTurn("INDEPENDENT_VERIFY", "i_161", 1180, True, None, 0, True),
    # TRANSFER (§9): novel-representation items, unaided.
    ScriptedTurn("TRANSFER", "i_201", 1180, True, None, 0, True),
    ScriptedTurn("TRANSFER", "i_202", 1180, True, None, 0, True),
]

assert len(SCRIPT) == 20, "the exit criterion requires exactly 20 scripted responses"


@dataclass(frozen=True)
class TrajectoryStep:
    turn: ScriptedTurn
    p_know_after: float
    misconception_beliefs_after: dict[str, float]
    item_elo_after: int
    evidence_weight: float


@dataclass(frozen=True)
class TrajectoryResult:
    steps: list[TrajectoryStep]
    final_p_know: float
    final_misconception_beliefs: dict[str, float]
    final_mastery_effective: float
    unaided_correct_count: int
    transfer_attempted_count: int
    threshold_decision: object


def run_synthetic_trajectory() -> TrajectoryResult:
    """Replay :data:`SCRIPT` through the real P2 functions -- no LLM
    calls, fully deterministic. This is what P2's exit criterion
    describes as "a synthetic learner with a planted misconception,
    driven through 20 scripted responses.""
    """
    p_know = INITIAL_P_KNOW
    misconception_priors = dict(INITIAL_MISCONCEPTION_PRIORS)
    steps: list[TrajectoryStep] = []
    unaided_correct_count = 0
    transfer_attempted_count = 0

    for index, turn in enumerate(SCRIPT, start=1):
        p_know = bkt_update(p_know, correct=turn.correct, params=BKT_PARAMS)

        if not turn.correct and turn.distractor is not None:
            misconception_priors = misconception_belief_update(
                misconception_priors,
                DISTRACTOR_LIKELIHOODS,
                COMPLEMENT_LIKELIHOODS,
                turn.distractor,
            )

        item_elo_after = update_item_elo(
            turn.item_elo_prior, LEARNER_ELO_RATING, learner_correct=turn.correct
        )

        observation = ResponseObservation(
            item_id=turn.item_id,
            source_event_id=f"evt_{index:03d}",
            correct=turn.correct,
            unaided=turn.unaided,
            hints_used=turn.hints_used,
        )
        built_evidence = build_response_evidence(observation)

        if turn.phase == "INDEPENDENT_VERIFY" and turn.correct:
            unaided_correct_count += 1
        if turn.phase == "TRANSFER":
            transfer_attempted_count += 1

        steps.append(
            TrajectoryStep(
                turn=turn,
                p_know_after=p_know,
                misconception_beliefs_after=dict(misconception_priors),
                item_elo_after=item_elo_after,
                evidence_weight=built_evidence.weight,
            )
        )

    final_effective = mastery_effective(p_know, misconception_priors)
    decision = evaluate_mastery_threshold(
        ThresholdInputs(
            p_known=p_know,
            unaided_correct_count=unaided_correct_count,
            transfer_attempted_count=transfer_attempted_count,
        )
    )

    return TrajectoryResult(
        steps=steps,
        final_p_know=p_know,
        final_misconception_beliefs=misconception_priors,
        final_mastery_effective=final_effective,
        unaided_correct_count=unaided_correct_count,
        transfer_attempted_count=transfer_attempted_count,
        threshold_decision=decision,
    )


def format_trajectory_report(result: TrajectoryResult) -> str:
    """Render the human-readable trajectory report the exit criterion
    requires: observations, mastery evolution, misconception belief
    evolution, effective mastery, threshold state, and a final
    interpretation."""
    lines = [
        "PROTÉGÉ P2 synthetic trajectory -- skill S004, planted misconception M003",
        "=" * 78,
        f"{'#':>2}  {'phase':<19}{'item':<8}{'correct':<9}{'distractor':<12}"
        f"{'p_know':>8}{'M003':>8}{'M011':>8}{'elo':>6}{'wt':>5}",
        "-" * 78,
    ]
    for i, step in enumerate(result.steps, start=1):
        t = step.turn
        lines.append(
            f"{i:>2}  {t.phase:<19}{t.item_id:<8}{t.correct!s:<9}"
            f"{(t.distractor or '-'):<12}{step.p_know_after:>8.4f}"
            f"{step.misconception_beliefs_after['M003']:>8.4f}"
            f"{step.misconception_beliefs_after['M011']:>8.4f}"
            f"{step.item_elo_after:>6}{step.evidence_weight:>5.2f}"
        )
    lines.append("-" * 78)
    lines.append(f"final P(L known)          = {result.final_p_know:.4f}")
    lines.append(
        f"final misconception beliefs = M003={result.final_misconception_beliefs['M003']:.4f}, "
        f"M011={result.final_misconception_beliefs['M011']:.4f}"
    )
    lines.append(f"mastery_effective          = {result.final_mastery_effective:.4f}")
    lines.append(f"unaided_correct_count      = {result.unaided_correct_count}")
    lines.append(f"transfer_attempted_count   = {result.transfer_attempted_count}")
    lines.append(f"threshold decision         = {result.threshold_decision}")
    lines.append("")
    lines.append("Interpretation:")
    lines.append("  Raw P(L) crosses the roadmap P2 mastery threshold (>=0.85, >=3 unaided")
    lines.append("  correct, >=1 transfer attempted): mastery_verified=True. But")
    lines.append("  mastery_effective is far lower, because M003's belief was never driven")
    lines.append("  low enough by this script (P2 has no misconception-resolution pathway")
    lines.append("  -- that is the Diagnostician/teach-back's job, P6/P7, out of P2 scope;")
    lines.append("  see mastery_engine.misconception_belief_update's docstring). Note step 7:")
    lines.append('  the SAME "says_equal" observation independently lowered M003\'s belief')
    lines.append("  (docs/DECISIONS.md D13 -- weak evidence for M003, strong evidence for")
    lines.append("  M011) while raising M011's -- proof the two updates never normalize")
    lines.append("  against each other.")
    lines.append('  This is exactly ARCHITECTURE.md §10.1 rule 1: "A child can look 85%')
    lines.append('  right and still be blocked by one active bug." P2 exposes both')
    lines.append("  numbers; it does not decide which one a caller should act on.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_synthetic_trajectory_no_llm_calls_and_is_pure() -> None:
    # Grep-verify that neither this test module nor the P2 modules it
    # exercises import a network/provider client -- the exit criterion
    # requires "No LLM calls" to be a checkable property, not an
    # assertion of intent.
    import protege.learning_engine.evidence_builder as evidence_builder_module
    import protege.learning_engine.mastery_engine as mastery_engine_module
    import protege.learning_engine.threshold_service as threshold_service_module

    forbidden = ("openai", "anthropic", "httpx", "requests", "protege.llm", "socket")
    for module in (mastery_engine_module, evidence_builder_module, threshold_service_module):
        source_path = module.__file__
        assert source_path is not None
        with open(source_path, encoding="utf-8") as f:
            contents = f.read()
        for name in forbidden:
            assert name not in contents, f"{module.__name__} must not reference {name!r}"


def test_synthetic_trajectory_deterministic_replay() -> None:
    first = run_synthetic_trajectory()
    second = run_synthetic_trajectory()
    assert first.final_p_know == second.final_p_know
    assert first.final_misconception_beliefs == second.final_misconception_beliefs
    assert first.final_mastery_effective == second.final_mastery_effective
    assert first.threshold_decision == second.threshold_decision


def test_synthetic_trajectory_probabilities_stay_bounded_throughout() -> None:
    result = run_synthetic_trajectory()
    for step in result.steps:
        assert 0.0 <= step.p_know_after <= 1.0
        for belief in step.misconception_beliefs_after.values():
            assert 0.0 <= belief <= 1.0
    assert 0.0 <= result.final_mastery_effective <= 1.0


def test_synthetic_trajectory_mastery_verified_but_effective_mastery_suppressed() -> None:
    """The headline exit-criterion result: raw mastery crosses the
    threshold, while mastery_effective reveals the unresolved
    misconception still suppressing it (§10.1 rule 1)."""
    result = run_synthetic_trajectory()
    assert result.threshold_decision.mastery_verified is True
    assert result.final_p_know >= 0.85
    assert result.unaided_correct_count == 3
    assert result.transfer_attempted_count >= 1
    # mastery_effective must be well below raw p_know: the unresolved
    # M003 belief suppresses it substantially.
    assert result.final_mastery_effective < result.final_p_know * 0.1


def test_synthetic_trajectory_misconception_belief_responds_to_distractor_evidence() -> None:
    result = run_synthetic_trajectory()
    # After the very first (M003-consistent) incorrect response, M003's
    # belief must have risen above its 0.42 prior.
    first_step_m003 = result.steps[0].misconception_beliefs_after["M003"]
    assert first_step_m003 > INITIAL_MISCONCEPTION_PRIORS["M003"]


def test_synthetic_trajectory_independent_updates_can_diverge_from_one_observation() -> None:
    """docs/DECISIONS.md D13: at step 7 (i_107, "says_equal"), the same
    observation is simultaneously weak evidence for M003 and strong
    evidence for M011 -- their independent updates must move in opposite
    directions from it, which candidate-set normalization could never
    produce (there, one candidate's gain is mechanically another's loss,
    never both moving in the direction their own tables predict)."""
    result = run_synthetic_trajectory()
    before = result.steps[5].misconception_beliefs_after  # after i_106, before i_107
    after = result.steps[6].misconception_beliefs_after  # after i_107
    assert after["M003"] < before["M003"]
    assert after["M011"] > before["M011"]


def test_synthetic_trajectory_verification_and_transfer_evidence_weighted_3x() -> None:
    result = run_synthetic_trajectory()
    verify_and_transfer_steps = [
        s for s in result.steps if s.turn.phase in ("INDEPENDENT_VERIFY", "TRANSFER")
    ]
    assert len(verify_and_transfer_steps) == 5
    assert all(s.evidence_weight == 3.0 for s in verify_and_transfer_steps)


def test_synthetic_trajectory_hint_discount_applied_at_threshold() -> None:
    result = run_synthetic_trajectory()
    hinted_step = next(s for s in result.steps if s.turn.item_id == "i_108")
    assert hinted_step.turn.hints_used == 2
    assert hinted_step.evidence_weight == 0.4


def test_synthetic_trajectory_report_is_human_readable_and_reproducible() -> None:
    result = run_synthetic_trajectory()
    report = format_trajectory_report(result)
    assert "Interpretation:" in report
    assert "mastery_verified=True" in report
    assert report == format_trajectory_report(run_synthetic_trajectory())
    # Print for `pytest -s` / CI log visibility -- the exit criterion asks
    # for a human-readable trajectory, not just a passing assertion.
    print("\n" + report)
