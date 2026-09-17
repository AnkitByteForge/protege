"""Golden-set evaluation harness for the P6 Diagnostician (roadmap P6, P24
placeholder: the full multi-role harness lands in P24 per ``evals/README.md``
-- this module implements only what P6's own exit criteria require: macro-F1,
ECE, Brier on the 120-item golden set, and the rule-based-fallback ablation).

Three entry points:

- :func:`evaluate_rule_based_only` -- the deterministic, network-free
  ablation roadmap P6 explicitly requires ("measure the rule-based fallback
  alone, so you know exactly what the LLM is buying you"). Safe to run in
  every CI job; no ``ModelRouter`` involved.
- :func:`evaluate_with_router` -- runs the full :func:`~protege.roles.diagnostician.diagnose`
  path (ASR gate, model call, closed-set + evidence-span enforcement,
  calibration) through any ``ModelRouter``. With a ``FakeProvider`` this is
  a *plumbing* check only (the canned response is identical for every
  example, so it is not a quality signal) -- with a real ``NvidiaProvider``
  it is the actual roadmap P6 / docs/DECISIONS.md D3 ship-gate measurement,
  which this package does not run automatically (docs/DECISIONS.md D9: no
  real NVIDIA calls in default CI).
- :func:`evaluate` -- the shared metrics core both of the above call.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from protege.contracts import DiagnosisResult, Distractor, Misconception
from protege.llm import ModelRouter

from .calibration import DEFAULT_CALIBRATION, CalibrationParams
from .diagnostician import DiagnosticContext, diagnose
from .golden_set import GoldenExample
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


def evaluate(
    examples: Sequence[GoldenExample], diagnose_fn: Callable[[GoldenExample], DiagnosisResult]
) -> EvalReport:
    records = tuple(predict(example, diagnose_fn) for example in examples)
    abstention_rate = sum(1 for r in records if r.abstained) / len(records) if records else 0.0
    return EvalReport(
        records=records,
        macro_f1=macro_f1(records),
        ece=expected_calibration_error(records),
        brier=brier_score(records),
        abstention_rate=abstention_rate,
        confusion=confusion_matrix(records),
    )


def evaluate_rule_based_only(
    examples: Sequence[GoldenExample], *, misconception_set: Sequence[Misconception]
) -> EvalReport:
    """The roadmap P6 ablation: the rule-based distractor->misconception
    fallback alone, with no model in the loop.

    A ``distractor_template``-sourced example carries the real authored
    ``Distractor`` it was generated from, so the rule-based path can
    classify it exactly as it would a real scored response. A
    ``sprout_script``/``worked_example``-sourced example carries no
    distractor -- the rule-based path correctly abstains on these (it has
    no free-text signal by design); that is the measurement, not a defect
    in it.
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
    through ``router``. With ``FakeProvider`` this exercises the harness's
    wiring only -- the canned response is identical for every example, so
    the resulting metrics are not a quality signal (see this module's
    docstring)."""

    def _diagnose(example: GoldenExample) -> DiagnosisResult:
        context = DiagnosticContext(
            explanation=example.to_explanation(), misconception_set=misconception_set
        )
        return diagnose(router, context, calibration=calibration)

    return evaluate(examples, _diagnose)
