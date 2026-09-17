"""Shared Sprout fidelity-evaluation logic (P5 evaluation harness).

Deliberately named with a leading underscore so pytest never collects this
as a test module -- it is imported by both the fast, FakeProvider-driven
tests (``test_sprout_fidelity_harness.py``, runs by default) and the real,
gated NVIDIA harness (``test_sprout_fidelity_nvidia.py``), so both exercise
IDENTICAL evaluation semantics. This module makes zero calls of its own; it
only orchestrates calls through a caller-supplied ``SproutGenerator``/
``ModelRouter``.

Design corrections from the first real-model run (see the conversation that
produced this module, summarized here so the "why" survives a re-read):

1. **Selection bias.** The first harness only ever scored fidelity for
   ACCEPTED (non-fallback) turns. Since acceptance already REQUIRES passing
   the four-stage gate, that number was structurally guaranteed to be near
   1.0 regardless of how good or bad the model actually is -- it measured
   "how good is content that already passed a filter," not "how good is the
   model." ``evaluate_misconception`` below scores EVERY real, parseable
   model output (accepted or validator-rejected); only a genuine schema
   failure (no parseable output at all) or a pure transport failure (no
   response at all) are excluded from -- or, for schema failures,
   score-floored in -- the fidelity computation, per the explicit rule in
   ``score_attempt_fidelity``.

2. **Circuit-breaker collapse.** The first harness called
   ``generator.generate_turn`` in a tight loop with no awareness of the
   ``ModelRouter``'s circuit breaker. Once the breaker opened for every
   real chain entry (after a burst of real failures), each subsequent call
   cost near-zero time (an instant deterministic-fallback skip), so a tight
   loop burned through hundreds of "samples" inside a single 30 s cooldown
   window before the breaker ever got a chance to close. ``evaluate_one``
   checks breaker status via ``wait_for_breaker_clear`` BEFORE every
   generation and waits (bounded, not infinite) rather than consuming a
   sample while every real option is closed.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from protege.authoring.loader import ContentPack
from protege.contracts import Misconception, MisconceptionCode, PedagogicalRole, SproutTurn
from protege.learning_engine.educational_validator import (
    answer_leaked,
    contains_forbidden_phrase,
    reading_level_ok,
)
from protege.llm.circuit_breaker import CircuitBreaker
from protege.llm.errors import FallbackReason
from protege.llm.router import ROLE_POLICY
from protege.llm.telemetry import InMemoryTelemetrySink
from protege.roles.sprout import (
    SproutAttemptRecord,
    SproutGenerator,
    SproutState,
    SproutValidationStage,
    score_fidelity,
)

BREAKER_COOLDOWN_S = 30.0
"""Matches ``CircuitBreaker``'s own documented default (addendum §2.4/§2.8:
"opens after 3 consecutive failures"), passed explicitly when this module
constructs its own ``CircuitBreaker`` so the evaluator's wait logic never
has to guess or duplicate a magic number it doesn't control."""

BREAKER_FAILURE_THRESHOLD = 3

_MAX_UTTERANCE_SAMPLE_CHARS = 160
_MAX_SAMPLES_PER_KIND = 3


class AttemptOutcomeKind(StrEnum):
    """Every distinguishable fate of one real generation attempt (P5
    evaluation-harness diagnostics). Purely additive/diagnostic -- does not
    change ``validate_generated_turn``'s accept/reject logic or order."""

    ACCEPTED = "accepted"
    MISCONCEPTION_CONSISTENCY_FAILURE = "misconception_consistency_failure"
    ANSWER_LEAKAGE_FAILURE = "answer_leakage_failure"
    FORBIDDEN_PHRASE_FAILURE = "forbidden_phrase_failure"
    READING_LEVEL_FAILURE = "reading_level_failure"
    SCHEMA_FAILURE = "schema_failure"
    """The router never produced a parseable ``SproutTurn`` for this
    attempt, but real network attempt(s) DID happen (telemetry shows a
    genuine response, just not schema-valid JSON even after repair)."""
    NETWORK_TIMEOUT = "network_timeout"
    """No usable response was ever obtained -- a transport-level failure
    (timeout/5xx/rate-limit) on every real attempt made for this record."""
    CIRCUIT_OPEN_WAIT = "circuit_open_wait"
    """Every real chain entry was breaker-open for the entirety of this
    attempt (should be rare given the pre-call wait; recorded, not
    silently absorbed, if it happens anyway)."""


_CONTENT_REJECTION_KINDS = frozenset(
    {
        AttemptOutcomeKind.MISCONCEPTION_CONSISTENCY_FAILURE,
        AttemptOutcomeKind.ANSWER_LEAKAGE_FAILURE,
        AttemptOutcomeKind.FORBIDDEN_PHRASE_FAILURE,
        AttemptOutcomeKind.READING_LEVEL_FAILURE,
    }
)
"""A real, parseable model output that the four-stage gate rejected for a
CONTENT reason -- distinct from a schema failure (no parseable output) or a
transport/circuit-breaker non-event (no output at all)."""


def classify_content_safety_reason(
    turn: SproutTurn, misconception: Misconception
) -> AttemptOutcomeKind:
    """Re-derive WHICH check inside ``SproutValidationStage.CONTENT_SAFETY``
    actually failed, for diagnostic labeling only.

    Calls the same free (no-network) P2 functions ``validate_generated_turn``
    itself calls, in the SAME order (forbidden-phrase before reading-level),
    so the label is always consistent with the validator's own decision.
    This does not change, re-implement, or duplicate the validator's actual
    accept/reject RULE -- it only re-runs the same deterministic checks a
    second time, for free, to attribute which one of the two produced the
    rejection the validator already made.
    """
    if contains_forbidden_phrase(turn.utterance, misconception.sprout_forbidden) is not None:
        return AttemptOutcomeKind.FORBIDDEN_PHRASE_FAILURE
    if not reading_level_ok(turn.utterance):
        return AttemptOutcomeKind.READING_LEVEL_FAILURE
    # Should not happen: CONTENT_SAFETY only fails for one of these two
    # reasons. Falling through to reading-level protects against silently
    # mis-labeling rather than crashing the evaluator over a labeling gap.
    return AttemptOutcomeKind.READING_LEVEL_FAILURE


def classify_schema_stage_attempt(
    attempt: SproutAttemptRecord, telemetry: InMemoryTelemetrySink
) -> AttemptOutcomeKind:
    """For an attempt whose ``validation.failed_stage`` is ``SCHEMA``
    (``attempt.value is None``), use telemetry to tell a genuine
    schema/parse failure apart from a pure transport failure or a
    circuit-breaker skip -- three fates ``StructuredCallOutcome`` alone
    cannot distinguish (roadmap task instruction D: these must be
    separately diagnosable).
    """
    records = [r for r in telemetry.runs if r.trace_id == attempt.trace_id]
    reasons = {r.fallback_reason for r in records if r.fallback_reason is not None}
    if FallbackReason.SCHEMA in reasons:
        return AttemptOutcomeKind.SCHEMA_FAILURE
    if reasons & {FallbackReason.TIMEOUT, FallbackReason.RATE_LIMIT, FallbackReason.SERVER_ERROR}:
        return AttemptOutcomeKind.NETWORK_TIMEOUT
    if reasons and reasons <= {FallbackReason.CIRCUIT_OPEN}:
        return AttemptOutcomeKind.CIRCUIT_OPEN_WAIT
    # No telemetry at all for this trace_id (e.g. the deterministic-fallback
    # sentinel reached with no registered provider ever tried) -- treat as
    # a network-layer non-event rather than fabricating a schema claim.
    return AttemptOutcomeKind.NETWORK_TIMEOUT


def classify_attempt(
    attempt: SproutAttemptRecord,
    *,
    misconception: Misconception,
    telemetry: InMemoryTelemetrySink,
) -> AttemptOutcomeKind:
    """The single entry point turning one ``SproutAttemptRecord`` into an
    ``AttemptOutcomeKind`` for reporting -- never changes what the
    validator accepted or rejected, only labels it more finely."""
    if attempt.validation.passed:
        return AttemptOutcomeKind.ACCEPTED
    stage = attempt.validation.failed_stage
    if stage == SproutValidationStage.MISCONCEPTION_CONSISTENCY:
        return AttemptOutcomeKind.MISCONCEPTION_CONSISTENCY_FAILURE
    if stage == SproutValidationStage.ANSWER_LEAK:
        return AttemptOutcomeKind.ANSWER_LEAKAGE_FAILURE
    if stage == SproutValidationStage.CONTENT_SAFETY:
        assert attempt.value is not None  # CONTENT_SAFETY implies a parsed value existed
        return classify_content_safety_reason(attempt.value, misconception)
    # SCHEMA stage: attempt.value is None; needs telemetry to disambiguate.
    return classify_schema_stage_attempt(attempt, telemetry)


def score_attempt_fidelity(
    kind: AttemptOutcomeKind,
    value: SproutTurn | None,
    *,
    misconception: Misconception,
    correct_answer: str,
) -> float | None:
    """The documented scoring rule (task instruction A):

    - A real, parseable output (accepted OR validator-rejected) is scored
      by the existing deterministic ``score_fidelity`` function, exactly as
      it would be scored if it had been accepted -- no special-casing by
      accept/reject outcome.
    - A genuine schema failure (model responded, output never parsed) is an
      explicit lowest score of 0.0 -- it must not vanish from the
      denominator, per the task instruction, but there is no structured
      value to run ``score_fidelity`` against.
    - A pure transport failure (network/timeout) or a circuit-breaker skip
      produced no model output at all -- there is nothing to score, and
      scoring it would fabricate a fidelity judgement about content that
      was never generated. Returns ``None``, and the caller must exclude
      ``None`` from the fidelity denominator (this is the ONLY excluded
      category, and it is excluded because no output exists, not because
      of what the output contained).
    """
    if kind == AttemptOutcomeKind.SCHEMA_FAILURE:
        return 0.0
    if kind in (AttemptOutcomeKind.NETWORK_TIMEOUT, AttemptOutcomeKind.CIRCUIT_OPEN_WAIT):
        return None
    assert value is not None
    return score_fidelity(value, misconception=misconception, correct_answer=correct_answer)


def _sanitize_utterance(utterance: str) -> str:
    """Truncate for sample retention. Utterances are model-generated prose
    about fractions -- not secrets -- but are capped to keep reports small
    and to guarantee no accidental inclusion of anything long/unexpected."""
    text = utterance.strip().replace("\n", " ")
    if len(text) <= _MAX_UTTERANCE_SAMPLE_CHARS:
        return text
    return text[:_MAX_UTTERANCE_SAMPLE_CHARS] + "…"


@dataclass
class MisconceptionFidelityReport:
    """Everything measured for one misconception (task instruction A's
    required separate fields, plus the diagnostics task instruction D
    requires)."""

    code: str
    generate_turn_calls: int = 0
    real_model_attempts: int = 0
    """Every attempt where the evaluator actually invoked
    ``generator.generate_turn``'s underlying ``router.call_structured`` --
    i.e. every ``SproutAttemptRecord`` produced. Counted only after the
    breaker pre-check cleared, so this reflects genuine attempts, not
    breaker-open artifacts."""
    real_model_outputs_scored: int = 0
    """The subset of ``real_model_attempts`` that contributed a fidelity
    score (accepted, validator-rejected, or schema-failure-at-0.0) --
    excludes network_timeout and circuit_open_wait attempts, which produced
    no output to judge at all."""
    validator_rejections: int = 0
    """Real, parseable outputs that failed the four-stage gate for a
    content reason (NOT a schema failure)."""
    fallback_count: int = 0
    """Count of ``generate_turn`` calls (not individual attempts) whose
    final emitted turn was the deterministic authored fallback."""
    circuit_open_wait_events: int = 0
    """How many times the evaluator detected every real chain entry was
    breaker-open and waited before calling ``generate_turn`` at all."""
    leak_count: int = 0
    """``emitted_answer_leaks``: over every FINAL EMITTED turn (generated
    or fallback) -- the end-to-end, zero-tolerance child-facing safety
    measurement. This being 0 does NOT mean the model never produced
    leaking text; it means the validator caught every one before emission.
    See ``raw_model_answer_leak_attempts`` for the pre-filter number."""
    raw_model_answer_leak_attempts: int = 0
    """Every REAL, parseable attempt (regardless of ``kind``/which stage
    the four-stage gate reported as the first failure) whose utterance
    independently triggers the P2 ``answer_leaked`` check. Computed
    separately from ``classify_attempt``'s stage-ordered classification,
    because ``validate_generated_turn`` short-circuits at the FIRST failing
    stage: an attempt that fails misconception-consistency AND also leaks
    is classified only as a consistency failure, which would silently
    undercount true leak attempts if this were derived from
    ``reason_counts`` alone. This is the number task instruction 5 means
    by "raw_model_answer_leak_attempts" -- never conflate it with
    ``leak_count``/``emitted_answer_leaks``, which measures a completely
    different, already-filtered thing."""
    fidelities: list[float] = field(default_factory=list)
    reason_counts: dict[str, int] = field(default_factory=dict)
    samples: dict[str, list[str]] = field(default_factory=dict)

    def record_attempt(self, kind: AttemptOutcomeKind, fidelity: float | None, sample: str) -> None:
        self.real_model_attempts += 1
        self.reason_counts[kind.value] = self.reason_counts.get(kind.value, 0) + 1
        if kind in _CONTENT_REJECTION_KINDS:
            self.validator_rejections += 1
        if fidelity is not None:
            self.real_model_outputs_scored += 1
            self.fidelities.append(fidelity)
        bucket = self.samples.setdefault(kind.value, [])
        if sample and len(bucket) < _MAX_SAMPLES_PER_KIND:
            bucket.append(sample)

    @property
    def fallback_rate(self) -> float:
        return self.fallback_count / self.generate_turn_calls if self.generate_turn_calls else 0.0

    @property
    def mean_fidelity(self) -> float | None:
        if not self.fidelities:
            return None
        return sum(self.fidelities) / len(self.fidelities)

    @property
    def answer_leak_rate(self) -> float:
        return self.leak_count / self.generate_turn_calls if self.generate_turn_calls else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "generate_turn_calls": self.generate_turn_calls,
            "real_model_attempts": self.real_model_attempts,
            "real_model_outputs_scored": self.real_model_outputs_scored,
            "validator_rejections": self.validator_rejections,
            "fallback_count": self.fallback_count,
            "fallback_outputs": self.fallback_count,
            "accepted_model_outputs": self.reason_counts.get(AttemptOutcomeKind.ACCEPTED.value, 0),
            "fallback_rate": self.fallback_rate,
            "circuit_open_wait_events": self.circuit_open_wait_events,
            "leak_count": self.leak_count,
            "emitted_answer_leaks": self.leak_count,
            "raw_model_answer_leak_attempts": self.raw_model_answer_leak_attempts,
            "answer_leak_rate": self.answer_leak_rate,
            "mean_fidelity": self.mean_fidelity,
            "reason_counts": dict(self.reason_counts),
            "samples": {k: list(v) for k, v in self.samples.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> MisconceptionFidelityReport:
        report = cls(code=str(data["code"]))
        report.generate_turn_calls = int(data["generate_turn_calls"])  # type: ignore[arg-type]
        report.real_model_attempts = int(data["real_model_attempts"])  # type: ignore[arg-type]
        report.real_model_outputs_scored = int(data["real_model_outputs_scored"])  # type: ignore[arg-type]
        report.validator_rejections = int(data["validator_rejections"])  # type: ignore[arg-type]
        report.fallback_count = int(data["fallback_count"])  # type: ignore[arg-type]
        report.circuit_open_wait_events = int(data["circuit_open_wait_events"])  # type: ignore[arg-type]
        report.leak_count = int(data["leak_count"])  # type: ignore[arg-type]
        report.raw_model_answer_leak_attempts = int(data.get("raw_model_answer_leak_attempts", 0))  # type: ignore[arg-type]
        mean_fidelity = data.get("mean_fidelity")
        n_scored = report.real_model_outputs_scored
        if isinstance(mean_fidelity, int | float) and n_scored:
            report.fidelities = [float(mean_fidelity)] * n_scored
        reason_counts = data.get("reason_counts")
        if isinstance(reason_counts, dict):
            report.reason_counts = {str(k): int(v) for k, v in reason_counts.items()}  # type: ignore[arg-type]
        samples = data.get("samples")
        if isinstance(samples, dict):
            report.samples = {str(k): [str(s) for s in v] for k, v in samples.items()}  # type: ignore[arg-type]
        return report


def checkpoint_path(checkpoint_dir: Path, code: str) -> Path:
    return checkpoint_dir / f"{code}.json"


def save_checkpoint(report: MisconceptionFidelityReport, checkpoint_dir: Path) -> None:
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path(checkpoint_dir, report.code).write_text(
        json.dumps(report.as_dict(), indent=2), encoding="utf-8"
    )


def load_checkpoint(checkpoint_dir: Path, code: str) -> MisconceptionFidelityReport | None:
    path = checkpoint_path(checkpoint_dir, code)
    if not path.is_file():
        return None
    return MisconceptionFidelityReport.from_dict(json.loads(path.read_text(encoding="utf-8")))


def real_chain_pairs(
    role_policy: dict[PedagogicalRole, tuple[str, ...]] = ROLE_POLICY,
) -> list[tuple[str, str]]:
    """Every provider-qualified ``(provider_name, model_id)`` entry in
    ``ROLE_POLICY[SPROUT]`` -- the set the circuit breaker actually tracks.
    Skips the deterministic-fallback sentinel (never network-reachable, so
    never breaker-tracked)."""
    pairs: list[tuple[str, str]] = []
    for entry in role_policy[PedagogicalRole.SPROUT]:
        if ":" not in entry:
            continue
        provider_name, model_id = entry.split(":", 1)
        if provider_name == "nvidia":  # the only registered provider name in this harness
            pairs.append((provider_name, model_id))
    return pairs


def wait_for_breaker_clear(
    breaker: CircuitBreaker,
    chain_pairs: Sequence[tuple[str, str]],
    *,
    max_wait_s: float = BREAKER_COOLDOWN_S + 10.0,
    poll_interval_s: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> bool:
    """Block (bounded) until at least one real chain entry is NOT
    breaker-open, per task instruction B: "never rapidly consume evaluation
    samples while the ModelRouter circuit breaker is open... wait for the
    existing breaker cooldown rather than resetting/recreating the router."

    Returns ``True`` if it had to wait at all (the caller uses this to
    increment ``circuit_open_wait_events``). Bounded by ``max_wait_s`` --
    never an unlimited retry loop (task instruction B) -- and returns
    (giving up on waiting further, letting the caller proceed and observe
    the real outcome) if still open after that bound.
    """
    if not chain_pairs:
        return False
    waited = False
    deadline = clock() + max_wait_s
    while all(breaker.is_open(provider, model_id) for provider, model_id in chain_pairs):
        waited = True
        if clock() >= deadline:
            break
        sleep(poll_interval_s)
    return waited


def evaluate_misconception(
    generator: SproutGenerator,
    content_pack: ContentPack,
    code: MisconceptionCode,
    *,
    n_generations: int,
    breaker: CircuitBreaker,
    telemetry: InMemoryTelemetrySink,
    checkpoint_dir: Path | None = None,
    force: bool = False,
    progress: Callable[[str], None] | None = None,
    breaker_max_wait_s: float = BREAKER_COOLDOWN_S + 10.0,
    breaker_poll_interval_s: float = 2.0,
) -> MisconceptionFidelityReport:
    """Run (or resume) the fidelity evaluation for exactly one misconception.

    Resumable (task instruction C): if ``checkpoint_dir`` is given and a
    checkpoint for ``code`` already exists, it is returned immediately with
    NO new calls, unless ``force`` is set. On completion (success or not),
    the result is checkpointed so a later run (of this or other
    misconceptions) never has to repeat this misconception's real calls.
    """
    if checkpoint_dir is not None and not force:
        existing = load_checkpoint(checkpoint_dir, code)
        if existing is not None:
            if progress:
                progress(f"[{code}] resumed from checkpoint, skipping real calls")
            return existing

    example = content_pack.worked_examples[code]
    item_stem = example.diagnostic_item.stem
    correct_answer = example.diagnostic_item.correct_answer
    misconception = next(m for m in content_pack.misconceptions if m.code == code)
    chain_pairs = real_chain_pairs()

    report = MisconceptionFidelityReport(code=code)
    for turn_index in range(n_generations):
        if wait_for_breaker_clear(
            breaker,
            chain_pairs,
            max_wait_s=breaker_max_wait_s,
            poll_interval_s=breaker_poll_interval_s,
        ):
            report.circuit_open_wait_events += 1
            if progress:
                progress(f"[{code}] waited for circuit breaker to clear before turn {turn_index}")

        result = generator.generate_turn(
            state=SproutState(misconception_id=code, turn_index=turn_index),
            item_stem=item_stem,
            correct_answer=correct_answer,
            trace_id=f"{code}-{turn_index}-{uuid.uuid4()}",
        )
        report.generate_turn_calls += 1
        if result.used_fallback:
            report.fallback_count += 1

        for attempt in result.attempts:
            kind = classify_attempt(attempt, misconception=misconception, telemetry=telemetry)
            fidelity = score_attempt_fidelity(
                kind, attempt.value, misconception=misconception, correct_answer=correct_answer
            )
            sample = _sanitize_utterance(attempt.value.utterance) if attempt.value else ""
            report.record_attempt(kind, fidelity, sample)
            # Independent of `kind` (which reports only the FIRST stage that
            # failed): count every real, parseable attempt whose own text
            # leaks, even one that was already rejected for a different,
            # earlier-checked reason (e.g. misconception inconsistency).
            # Task instruction 5: never let emitted_answer_leak_rate==0
            # stand in for "the model never produced leaking text."
            if attempt.value is not None and answer_leaked(attempt.value.utterance, correct_answer):
                report.raw_model_answer_leak_attempts += 1

        if answer_leaked(result.turn.utterance, correct_answer):
            report.leak_count += 1

        if progress:
            progress(
                f"[{code}] {turn_index + 1}/{n_generations} "
                f"fallback={result.used_fallback} attempts={len(result.attempts)}"
            )

    if checkpoint_dir is not None:
        save_checkpoint(report, checkpoint_dir)
    return report


def aggregate_reports(reports: Sequence[MisconceptionFidelityReport]) -> dict[str, object]:
    """Overall stats across every misconception's report -- the formal gate
    is computed here, NOT redefined: mean fidelity >= 0.90 over
    ``real_model_outputs_scored`` (accepted + validator-rejected +
    schema-failures-at-0.0, never fallback), leak rate == 0.000 over every
    emitted turn.

    ``overall_raw_model_answer_leak_attempts`` and
    ``overall_emitted_answer_leaks`` are reported side by side and must
    never be conflated (task instruction 5): a 0 for the latter is a
    statement about the validator's effectiveness, not about whether the
    raw model ever produced leaking text.
    """
    total_calls = sum(r.generate_turn_calls for r in reports)
    total_leaks = sum(r.leak_count for r in reports)
    total_raw_leak_attempts = sum(r.raw_model_answer_leak_attempts for r in reports)
    total_accepted = sum(r.reason_counts.get(AttemptOutcomeKind.ACCEPTED.value, 0) for r in reports)
    total_fallback = sum(r.fallback_count for r in reports)
    total_attempts = sum(r.real_model_attempts for r in reports)
    total_scored = sum(r.real_model_outputs_scored for r in reports)
    all_fidelities = [f for r in reports for f in r.fidelities]
    mean_fidelity = sum(all_fidelities) / len(all_fidelities) if all_fidelities else None
    return {
        "per_misconception": [r.as_dict() for r in reports],
        "overall": {
            "total_generate_turn_calls": total_calls,
            "total_real_model_attempts": total_attempts,
            "total_real_model_outputs_scored": total_scored,
            "total_validator_rejections": sum(r.validator_rejections for r in reports),
            "accepted_model_outputs": total_accepted,
            "fallback_outputs": total_fallback,
            "total_fallback_count": total_fallback,
            "overall_fallback_rate": total_fallback / total_calls if total_calls else 0.0,
            "total_circuit_open_wait_events": sum(r.circuit_open_wait_events for r in reports),
            "total_leak_count": total_leaks,
            "emitted_answer_leaks": total_leaks,
            "raw_model_answer_leak_attempts": total_raw_leak_attempts,
            "overall_answer_leak_rate": total_leaks / total_calls if total_calls else 1.0,
            "overall_mean_fidelity": mean_fidelity,
        },
    }
