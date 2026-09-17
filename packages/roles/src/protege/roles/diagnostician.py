"""The P6 Diagnostician role (roadmap P6; ARCHITECTURE.md §7.3).

Infers which of the 8 authored misconceptions a child's teach-back evidence
reveals. This is the one role ARCHITECTURE.md §7.1 calls "the closest thing
in this system to an agent" -- and even so, it never orchestrates: it
answers "what does this evidence show," nothing about what should happen
next (that is the FSM's job, out of P6's scope).

Non-negotiables enforced here, not merely documented:

- **Closed set only.** The model may not invent a misconception ID outside
  the caller's supplied set (:func:`_enforce_closed_set_and_spans`) --
  ``MisconceptionCode`` only constrains shape (``M\\d{3}``), not membership.
- **Abstain below the ASR threshold.** §7.3: "if mean_asr_confidence < 0.65,
  must return asr_reliable:false and abstain rather than guess" -- enforced
  *before* any model call, so an unreliable ASR turn never spends
  rate-limiter budget or a network round trip.
- **Deterministic degradation.** ``ROLE_POLICY[DIAGNOSTICIAN]``'s terminal
  chain entry is ``rule_based_distractor_map`` (P4); this module supplies
  that content (:mod:`protege.roles.rule_based`), and any *unexpected*
  router exception is also caught here and degraded the same way, rather
  than propagating (roadmap P6: "Model failure must degrade
  deterministically").
- **Never writes mastery.** :func:`diagnose` returns a value; nothing here
  persists, and :mod:`protege.roles.beliefs` (the P2 integration point)
  only returns an updated mapping for a future orchestrator to apply.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from protege.contracts import (
    DiagnosisLabel,
    DiagnosisResult,
    Distractor,
    Explanation,
    Misconception,
    PedagogicalRole,
    VoiceExplanation,
)
from protege.llm import ModelRouter

from .calibration import DEFAULT_CALIBRATION, CalibrationParams, calibrate_confidence
from .constants import ASR_CONFIDENCE_THRESHOLD
from .errors import NoClosedSetProvidedError
from .evidence_span import describe_explanation, extract_evidence_span, is_free_text_modality
from .prompt import build_diagnostician_messages
from .rule_based import rule_based_diagnosis


@dataclass(frozen=True)
class DiagnosticContext:
    """Everything one :func:`diagnose` call needs (§7.3 inputs).

    Narrower than §7.3's full input list ("...retrieved 3 prior
    explanations (pgvector)") -- retrieval is P22's scope, not P6's;
    ``prior_beliefs`` covers §7.3's retrieval-free "prior beliefs" input.
    """

    explanation: Explanation
    misconception_set: Sequence[Misconception]
    selected_distractor: Distractor | None = None
    prior_beliefs: Mapping[str, float] | None = None


def _mean_asr_confidence(explanation: Explanation) -> float:
    """1.0 for any non-voice modality (no ASR signal to be unreliable
    about); the voice modality's own reported confidence otherwise.
    """
    if isinstance(explanation, VoiceExplanation):
        # `float(...)`: protege.contracts has no py.typed marker (see this
        # workspace's mypy overrides), so `explanation.asr_confidence` is
        # seen as `Any` here even though it is a genuine `float` at runtime.
        return float(explanation.asr_confidence)
    return 1.0


def _abstention(*, asr_reliable: bool) -> DiagnosisResult:
    return DiagnosisResult(
        abstained=True, asr_reliable=asr_reliable, labels=[], understanding_signals=[]
    )


def _enforce_closed_set_and_spans(
    result: DiagnosisResult,
    *,
    closed_set_codes: set[str],
    source_text: str,
    verify_span: bool,
) -> DiagnosisResult:
    """Post-process one model-produced result: drop any label outside the
    closed set, and (for free-text modalities) drop any evidence_span that
    is not a real substring of ``source_text``.

    An abstaining result (empty labels by contract) passes through
    unchanged -- there is nothing to filter.
    """
    if not result.labels:
        return result

    kept: list[DiagnosisLabel] = []
    for label in result.labels:
        if label.misconception_code not in closed_set_codes:
            continue
        evidence_span = (
            extract_evidence_span(source_text, label.evidence_span)
            if verify_span
            else label.evidence_span
        )
        kept.append(
            DiagnosisLabel(
                misconception_id=label.misconception_code,
                state=label.state,
                confidence=label.confidence,
                evidence_span=evidence_span,
            )
        )
    return DiagnosisResult(
        labels=kept,
        understanding_signals=result.understanding_signals,
        asr_reliable=result.asr_reliable,
        abstained=result.abstained,
    )


def _apply_calibration(result: DiagnosisResult, calibration: CalibrationParams) -> DiagnosisResult:
    if not result.labels:
        return result
    calibrated = [
        DiagnosisLabel(
            misconception_id=label.misconception_code,
            state=label.state,
            confidence=calibrate_confidence(label.confidence, calibration),
            evidence_span=label.evidence_span,
        )
        for label in result.labels
    ]
    return DiagnosisResult(
        labels=calibrated,
        understanding_signals=result.understanding_signals,
        asr_reliable=result.asr_reliable,
        abstained=result.abstained,
    )


def diagnose(
    router: ModelRouter,
    context: DiagnosticContext,
    *,
    calibration: CalibrationParams = DEFAULT_CALIBRATION,
    trace_id: str | None = None,
) -> DiagnosisResult:
    """Diagnose one piece of teach-back evidence (roadmap P6; §7.3).

    1. ASR gate (mandatory, pre-model-call): below
       :data:`~protege.roles.constants.ASR_CONFIDENCE_THRESHOLD`, abstain
       immediately without spending a model call.
    2. ``router.call_structured(DIAGNOSTICIAN, ...)`` (P4): walks the two
       real NVIDIA chain entries, then the terminal
       ``rule_based_distractor_map`` sentinel. Any unexpected exception
       from the router is treated identically to that sentinel (defense in
       depth: P4 already catches every documented provider failure mode
       internally, so this only ever fires on something P4 did not
       anticipate) -- it degrades to the rule-based path rather than
       propagating.
    3. Deterministic-fallback outcome ->
       :func:`~protege.roles.rule_based.rule_based_diagnosis`.
    4. Model outcome -> closed-set enforcement, evidence-span verification,
       then confidence calibration, in that order.
    """
    if not context.misconception_set:
        raise NoClosedSetProvidedError

    asr_reliable = _mean_asr_confidence(context.explanation) >= ASR_CONFIDENCE_THRESHOLD
    if not asr_reliable:
        return _abstention(asr_reliable=False)

    evidence_text = describe_explanation(context.explanation)
    closed_set_codes = {m.code for m in context.misconception_set}
    messages = build_diagnostician_messages(
        misconception_set=context.misconception_set,
        evidence_text=evidence_text,
        modality=context.explanation.modality,
        prior_beliefs=context.prior_beliefs,
    )

    def _fallback() -> DiagnosisResult:
        return rule_based_diagnosis(
            misconception_set=context.misconception_set,
            selected_distractor=context.selected_distractor,
            source_text=evidence_text,
        )

    try:
        outcome = router.call_structured(PedagogicalRole.DIAGNOSTICIAN, messages, trace_id=trace_id)
    except Exception:
        return _fallback()

    if outcome.used_deterministic_fallback or outcome.value is None:
        return _fallback()

    assert isinstance(outcome.value, DiagnosisResult)  # ROLE_RESPONSE_MODEL[DIAGNOSTICIAN]
    result = _enforce_closed_set_and_spans(
        outcome.value,
        closed_set_codes=closed_set_codes,
        source_text=evidence_text,
        verify_span=is_free_text_modality(context.explanation),
    )
    return _apply_calibration(result, calibration)
