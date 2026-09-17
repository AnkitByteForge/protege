"""Golden-set evaluation harness for the P6 Diagnostician (roadmap P6, P24
placeholder: the full multi-role harness lands in P24 per ``evals/README.md``
-- this module implements only what P6's own exit criteria require: macro-F1,
ECE, Brier on the 120-item golden set, the rule-based-fallback ablation, a
leakage-safe calibration protocol, and the real-model evaluation driver).

**Every :class:`EvalReport` this module produces carries
``dataset_status``** (copied from
:data:`protege.roles.golden_set.DATASET_STATUS`) so a report can never be
silently presented as more than it is: the checked-in 120-item set is
machine-derived from already-authored P3 content, not independently
hand-labelled, and not human-ratified (``packages/roles/golden_set/PROVENANCE.md``).
**Numbers from this module are development/provisional measurements, not
the roadmap's formal ship-gate result, until that file says otherwise.**

**The rule-based ablation on ``distractor_template`` examples is circular,
not diagnostic, evidence.** Those 64 examples' ground truth
(``misconception_code``) is copied from ``Distractor.maps_to`` -- the exact
field :func:`~protege.roles.rule_based.rule_based_diagnosis` reads to
answer. A perfect score there proves only that the lookup echoes its own
input; it says nothing about diagnostic quality on evidence the rule-based
path was not designed for (free text). :func:`evaluate_rule_based_only`
still exists because roadmap P6 explicitly asks to "measure the rule-based
fallback alone" -- but no test or report in this codebase may cite that
number as if it were an F1 score in the ordinary sense.

Entry points:

- :func:`evaluate_rule_based_only` -- the deterministic, network-free
  ablation (see the circularity warning above). Safe to run in every CI
  job; no ``ModelRouter`` involved.
- :func:`evaluate_with_router` -- runs the full :func:`~protege.roles.diagnostician.diagnose`
  path through any ``ModelRouter``. With ``FakeProvider`` this is a
  *plumbing* check only (the canned response is identical for every
  example, so it is not a quality signal).
- :func:`evaluate_with_router_calibrated_held_out` -- fits
  :func:`~protege.roles.calibration.fit_calibration` on one deterministic
  half of the set (:func:`~protege.roles.golden_set.split_golden_set`) and
  reports ECE/Brier on the *other* half only, with the fitted calibration
  applied -- never on the cases used to fit it.
- :func:`run_nvidia_diagnostician_evaluation` -- the real-model evaluation
  driver (docs/DECISIONS.md D3/D9): reports macro-F1/ECE/Brier/confusion
  *and*, via the router's own telemetry, how many examples were actually
  answered by the ``ROLE_POLICY[DIAGNOSTICIAN]`` *primary* model versus a
  secondary-chain or rule-based fallback -- never conflating the two. Only
  makes real network calls when handed a router with a real provider; this
  module never constructs one itself and never runs unprompted (see
  ``packages/roles/tests/test_nvidia_diagnostician_eval.py`` for the
  gated, manually-invoked test that does).
- :func:`evaluate` -- the shared metrics core the above all call.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Literal

from protege.contracts import DiagnosisResult, Distractor, Misconception, PedagogicalRole
from protege.llm import ROLE_POLICY, ModelRouter, ModelRunRecord

from .calibration import (
    DEFAULT_CALIBRATION,
    CalibrationParams,
    calibrate_confidence,
    fit_calibration,
)
from .diagnostician import DiagnosticContext, diagnose
from .golden_set import DATASET_STATUS, GoldenExample, split_golden_set
from .rule_based import rule_based_diagnosis


@dataclass(frozen=True)
class PredictionRecord:
    """One golden-example's prediction, reduced to what the metrics need:
    the top (highest-confidence) label only, matching how a downstream
    consumer would act on a diagnosis."""

    example_id: str
    true_code: str
    predicted_code: str | None
    predicted_confidence: float
    abstained: bool


@dataclass(frozen=True)
class EvalReport:
    records: tuple[PredictionRecord, ...]
    macro_f1: float
    ece: float
    brier: float
    abstention_rate: float
    confusion: dict[tuple[str, str], int]
    dataset_status: str = DATASET_STATUS

    @property
    def n(self) -> int:
        return len(self.records)


def _top_label(result: DiagnosisResult) -> tuple[str | None, float]:
    if not result.labels:
        return None, 0.0
    top = max(result.labels, key=lambda label: label.confidence)
    return top.misconception_code, top.confidence


def predict(
    example: GoldenExample, diagnose_fn: Callable[[GoldenExample], DiagnosisResult]
) -> PredictionRecord:
    result = diagnose_fn(example)
    predicted_code, confidence = _top_label(result)
    return PredictionRecord(
        example_id=example.id,
        true_code=example.misconception_code,
        predicted_code=predicted_code,
        predicted_confidence=confidence,
        abstained=result.abstained,
    )


def macro_f1(records: Sequence[PredictionRecord]) -> float:
    """Unweighted mean of per-class F1 over every code that appears as
    ground truth or as a prediction (docs/DECISIONS.md D3; ARCHITECTURE.md
    §26: ``macro-F1``). An abstention (``predicted_code=None``) can never
    match any ground-truth code, so it always counts as a false negative
    for that example's true class -- abstaining on a genuinely diagnosable
    golden item is scored as a miss, not excused.
    """
    codes = sorted(
        {r.true_code for r in records} | {r.predicted_code for r in records if r.predicted_code}
    )
    if not codes:
        return 0.0
    per_class_f1: list[float] = []
    for code in codes:
        tp = sum(1 for r in records if r.true_code == code and r.predicted_code == code)
        fp = sum(1 for r in records if r.predicted_code == code and r.true_code != code)
        fn = sum(1 for r in records if r.true_code == code and r.predicted_code != code)
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_class_f1.append(f1)
    return sum(per_class_f1) / len(per_class_f1)


def brier_score(records: Sequence[PredictionRecord]) -> float:
    """Mean squared error of the top label's confidence against binary
    correctness (ARCHITECTURE.md §26: ``(1/N)Σ(p_i - y_i)²``). Abstentions
    carry no confidence to score and are excluded, matching how ECE is
    computed here too -- both are calibration measures over the
    confidences the system actually reported, not over its abstention
    decisions (those are scored by ``macro_f1`` and ``abstention_rate``
    instead).
    """
    scored = [r for r in records if not r.abstained]
    if not scored:
        return 0.0
    total = sum(
        (r.predicted_confidence - (1.0 if r.predicted_code == r.true_code else 0.0)) ** 2
        for r in scored
    )
    return total / len(scored)


def expected_calibration_error(records: Sequence[PredictionRecord], *, n_bins: int = 10) -> float:
    """``Σ(n_b/N)·abs(acc_b - conf_b)`` over ``n_bins`` equal-width
    confidence buckets (ARCHITECTURE.md §26). Abstentions excluded, as in
    :func:`brier_score`.
    """
    scored = [r for r in records if not r.abstained]
    if not scored:
        return 0.0
    bins: list[list[PredictionRecord]] = [[] for _ in range(n_bins)]
    for r in scored:
        index = min(int(r.predicted_confidence * n_bins), n_bins - 1)
        bins[index].append(r)
    total = len(scored)
    ece = 0.0
    for bucket in bins:
        if not bucket:
            continue
        accuracy = sum(1 for r in bucket if r.predicted_code == r.true_code) / len(bucket)
        confidence = sum(r.predicted_confidence for r in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(accuracy - confidence)
    return ece


def confusion_matrix(records: Sequence[PredictionRecord]) -> dict[tuple[str, str], int]:
    """``(true_code, predicted_code)`` counts; an abstention's predicted
    side is the literal string ``"ABSTAIN"`` so it is visible in the
    matrix rather than silently absorbed into a real code's column."""
    counts: Counter[tuple[str, str]] = Counter()
    for r in records:
        predicted = r.predicted_code if r.predicted_code is not None else "ABSTAIN"
        counts[r.true_code, predicted] += 1
    return dict(counts)


def _report_from_records(records: Sequence[PredictionRecord]) -> EvalReport:
    records = tuple(records)
    abstention_rate = sum(1 for r in records if r.abstained) / len(records) if records else 0.0
    return EvalReport(
        records=records,
        macro_f1=macro_f1(records),
        ece=expected_calibration_error(records),
        brier=brier_score(records),
        abstention_rate=abstention_rate,
        confusion=confusion_matrix(records),
    )


def evaluate(
    examples: Sequence[GoldenExample], diagnose_fn: Callable[[GoldenExample], DiagnosisResult]
) -> EvalReport:
    return _report_from_records([predict(example, diagnose_fn) for example in examples])


def evaluate_rule_based_only(
    examples: Sequence[GoldenExample], *, misconception_set: Sequence[Misconception]
) -> EvalReport:
    """The roadmap P6 ablation: the rule-based distractor->misconception
    fallback alone, with no model in the loop.

    **Read this module's docstring first.** A ``distractor_template``-sourced
    example's ground truth *is* the field the rule-based path reads
    (``Distractor.maps_to``) -- a perfect score on that subset is circular,
    not a quality measurement. A ``sprout_script``/``worked_example``-sourced
    example carries no distractor -- the rule-based path correctly abstains
    on these (it has no free-text signal by design); that abstention gap
    *is* the real, non-circular measurement roadmap P6 asks for ("so you
    know exactly what the LLM is buying you").
    """

    def _diagnose(example: GoldenExample) -> DiagnosisResult:
        distractor = (
            Distractor(
                value=example.distractor.value,
                maps_to=example.distractor.maps_to,
                likelihood=example.distractor.likelihood,
            )
            if example.distractor is not None
            else None
        )
        return rule_based_diagnosis(
            misconception_set=misconception_set,
            selected_distractor=distractor,
            source_text=example.text,
        )

    return evaluate(examples, _diagnose)


def evaluate_with_router(
    examples: Sequence[GoldenExample],
    router: ModelRouter,
    *,
    misconception_set: Sequence[Misconception],
    calibration: CalibrationParams = DEFAULT_CALIBRATION,
) -> EvalReport:
    """Run the full :func:`~protege.roles.diagnostician.diagnose` path
    through ``router``, one call per example, ``trace_id=example.id`` (so a
    caller can later correlate ``router.telemetry`` records back to a
    specific golden example -- see :func:`run_nvidia_diagnostician_evaluation`).

    With ``FakeProvider`` this exercises the harness's wiring only -- the
    canned response is identical for every example, so the resulting
    metrics are not a quality signal (see this module's docstring).
    """

    def _diagnose(example: GoldenExample) -> DiagnosisResult:
        context = DiagnosticContext(
            explanation=example.to_explanation(), misconception_set=misconception_set
        )
        return diagnose(router, context, calibration=calibration, trace_id=example.id)

    return evaluate(examples, _diagnose)


@dataclass(frozen=True)
class HeldOutCalibrationReport:
    """Result of a leakage-safe calibration protocol: ``fitted_calibration``
    was fit **only** on ``calibration_split_n`` examples; every metric on
    ``held_out_report`` is computed **only** on the disjoint
    ``held_out_split_n`` examples, with that calibration applied.
    ``held_out_report_uncalibrated`` is the same held-out examples scored
    with raw (identity-calibration) confidence, included so calibration's
    actual effect is visible rather than asserted.
    """

    calibration_split_n: int
    held_out_split_n: int
    fitted_calibration: CalibrationParams
    held_out_report: EvalReport
    held_out_report_uncalibrated: EvalReport


def evaluate_with_router_calibrated_held_out(
    examples: Sequence[GoldenExample],
    router: ModelRouter,
    *,
    misconception_set: Sequence[Misconception],
    calibration_fraction: float = 0.5,
) -> HeldOutCalibrationReport:
    """The leakage-safe calibration protocol this module's docstring and
    :mod:`protege.roles.calibration` require: :func:`~protege.roles.calibration.fit_calibration`
    is fit on one deterministic half of ``examples``
    (:func:`~protege.roles.golden_set.split_golden_set`) and every reported
    metric comes from the *other*, disjoint half.

    Calls the router exactly once per example (identity calibration, i.e.
    raw confidences) -- calibration is then fit and applied *post hoc* to
    already-collected raw records, never by re-querying the model. This
    matters when ``router`` is real: it halves the NVIDIA credit cost of
    this protocol versus querying twice (docs/DECISIONS.md D9's "eval
    results cached ... essential given finite NVIDIA credits" concern,
    applied to a second axis).
    """
    raw = evaluate_with_router(
        examples, router, misconception_set=misconception_set, calibration=DEFAULT_CALIBRATION
    )
    calibration_examples, held_out_examples = split_golden_set(
        examples, calibration_fraction=calibration_fraction
    )
    calibration_ids = {e.id for e in calibration_examples}
    held_out_ids = {e.id for e in held_out_examples}

    calibration_pairs = [
        (r.predicted_confidence, r.predicted_code == r.true_code)
        for r in raw.records
        if r.example_id in calibration_ids and not r.abstained
    ]
    fitted = fit_calibration(calibration_pairs)

    held_out_raw = [r for r in raw.records if r.example_id in held_out_ids]
    held_out_calibrated = [
        r
        if r.abstained
        else replace(r, predicted_confidence=calibrate_confidence(r.predicted_confidence, fitted))
        for r in held_out_raw
    ]

    return HeldOutCalibrationReport(
        calibration_split_n=len(calibration_examples),
        held_out_split_n=len(held_out_examples),
        fitted_calibration=fitted,
        held_out_report=_report_from_records(held_out_calibrated),
        held_out_report_uncalibrated=_report_from_records(held_out_raw),
    )


# --- Real-model evaluation (docs/DECISIONS.md D3, D9) ------------------------

AttemptResolution = Literal["primary", "secondary_fallback", "rule_based_fallback", "no_telemetry"]


@dataclass(frozen=True)
class AttemptOutcome:
    """How one example's :func:`~protege.roles.diagnostician.diagnose` call
    was actually resolved, read from ``router.telemetry`` -- never assumed
    from the ``EvalReport`` alone, which cannot distinguish "the primary
    model answered" from "a fallback silently answered instead"."""

    example_id: str
    resolution: AttemptResolution
    model_id: str | None
    structured_mode: str | None


def _diagnostician_chain_model_ids() -> tuple[str, str]:
    """``(primary_model_id, secondary_model_id)`` read live from
    ``protege.llm.ROLE_POLICY[DIAGNOSTICIAN]`` -- never hardcoded here, so
    this module cannot silently drift from whatever P4 actually configures
    (``packages/llm`` is not modified by this package)."""
    chain = ROLE_POLICY[PedagogicalRole.DIAGNOSTICIAN]
    provider_qualified = [entry for entry in chain if ":" in entry]
    if len(provider_qualified) < 2:
        raise ValueError(
            f"expected at least 2 provider-qualified chain entries for DIAGNOSTICIAN, got {chain!r}"
        )
    primary = provider_qualified[0].split(":", 1)[1]
    secondary = provider_qualified[1].split(":", 1)[1]
    return primary, secondary


def _classify_attempt(
    telemetry_runs: Sequence[ModelRunRecord], example_id: str, primary_model_id: str
) -> AttemptOutcome:
    runs = [r for r in telemetry_runs if r.trace_id == example_id]
    if not runs:
        return AttemptOutcome(example_id, "no_telemetry", None, None)

    # A genuine parsed success always has `fallback_reason=None` (P4's
    # `ModelRouter._attempt_chain_entry`). `structured_mode` alone is NOT a
    # safe success signal: a schema/parse failure is recorded with
    # `structured_mode=NATIVE` (or `PROMPT` on the repair attempt) too --
    # only `StructuredMode.FAILED` marks a network-level failure, so
    # filtering on that alone would misclassify a schema failure as a
    # success.
    successes = [r for r in runs if r.fallback_reason is None and r.provider != "deterministic"]
    if successes:
        last = successes[-1]
        resolution: AttemptResolution = (
            "primary" if last.model_id == primary_model_id else "secondary_fallback"
        )
        return AttemptOutcome(example_id, resolution, last.model_id, str(last.structured_mode))

    return AttemptOutcome(example_id, "rule_based_fallback", None, None)


@dataclass(frozen=True)
class NvidiaEvalReport:
    """The real-model evaluation roadmap P6 / docs/DECISIONS.md D3 actually
    requires: macro-F1/ECE/Brier/confusion **and** a per-example accounting
    of which ``ROLE_POLICY[DIAGNOSTICIAN]`` chain entry answered, so a
    secondary-model or rule-based fallback result is never silently
    reported as the primary model's result.

    ``dataset_status`` is always :data:`protege.roles.golden_set.DATASET_STATUS`
    -- these are development/provisional metrics until the golden set
    carries independent human ratification (``golden_set/PROVENANCE.md``).
    """

    n: int
    primary_model_id: str
    secondary_model_id: str
    primary_success_count: int
    secondary_fallback_count: int
    rule_based_fallback_count: int
    no_telemetry_count: int
    primary_rate: float
    fallback_rate: float
    report: EvalReport
    attempts: tuple[AttemptOutcome, ...]
    dataset_status: str = DATASET_STATUS


def run_nvidia_diagnostician_evaluation(
    examples: Sequence[GoldenExample],
    router: ModelRouter,
    *,
    misconception_set: Sequence[Misconception],
) -> NvidiaEvalReport:
    """Evaluate ``ROLE_POLICY[DIAGNOSTICIAN]`` through ``router`` and report
    the primary-model/secondary-fallback/rule-based-fallback split
    separately, alongside the usual macro-F1/ECE/Brier/confusion metrics.

    Does not itself decide whether ``router`` is real or fake -- callers
    that want the actual roadmap P6 measurement must construct a
    ``ModelRouter`` with a real ``NvidiaProvider``
    (``packages/roles/tests/test_nvidia_diagnostician_eval.py`` does this,
    gated behind an explicit env flag, never in default CI --
    docs/DECISIONS.md D9).
    """
    primary_model_id, secondary_model_id = _diagnostician_chain_model_ids()

    records: list[PredictionRecord] = []
    attempts: list[AttemptOutcome] = []
    for example in examples:
        context = DiagnosticContext(
            explanation=example.to_explanation(), misconception_set=misconception_set
        )
        result = diagnose(router, context, trace_id=example.id)
        predicted_code, confidence = _top_label(result)
        records.append(
            PredictionRecord(
                example_id=example.id,
                true_code=example.misconception_code,
                predicted_code=predicted_code,
                predicted_confidence=confidence,
                abstained=result.abstained,
            )
        )
        attempts.append(_classify_attempt(router.telemetry.runs, example.id, primary_model_id))

    n = len(examples)
    primary_count = sum(1 for a in attempts if a.resolution == "primary")
    secondary_count = sum(1 for a in attempts if a.resolution == "secondary_fallback")
    rule_based_count = sum(1 for a in attempts if a.resolution == "rule_based_fallback")
    no_telemetry_count = sum(1 for a in attempts if a.resolution == "no_telemetry")

    return NvidiaEvalReport(
        n=n,
        primary_model_id=primary_model_id,
        secondary_model_id=secondary_model_id,
        primary_success_count=primary_count,
        secondary_fallback_count=secondary_count,
        rule_based_fallback_count=rule_based_count,
        no_telemetry_count=no_telemetry_count,
        primary_rate=primary_count / n if n else 0.0,
        fallback_rate=(secondary_count + rule_based_count) / n if n else 0.0,
        report=_report_from_records(records),
        attempts=tuple(attempts),
    )
