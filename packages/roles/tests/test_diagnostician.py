from __future__ import annotations

from collections.abc import Sequence

import pytest

from protege.contracts import Distractor, Misconception, TextExplanation, VoiceExplanation
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.router import ModelRouter
from protege.roles.diagnostician import DiagnosticContext, diagnose
from protege.roles.errors import NoClosedSetProvidedError


def _router(provider: FakeProvider | None = None) -> ModelRouter:
    return ModelRouter({"nvidia": provider if provider is not None else FakeProvider()})


# --- Abstention (ASR gate) ---------------------------------------------------


def test_low_asr_confidence_abstains_without_calling_the_model(
    misconception_set: Sequence[Misconception],
) -> None:
    provider = FakeProvider()
    router = _router(provider)
    explanation = VoiceExplanation(text="mumble mumble", asr_confidence=0.4)
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=misconception_set)
    )
    assert result.abstained is True
    assert result.asr_reliable is False
    assert result.labels == []
    assert provider.calls == []  # no rate-limiter budget spent


def test_asr_confidence_at_threshold_is_reliable(
    misconception_set: Sequence[Misconception],
) -> None:
    provider = FakeProvider()
    router = _router(provider)
    explanation = VoiceExplanation(text="eight is more than four", asr_confidence=0.65)
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=misconception_set)
    )
    assert result.asr_reliable is True
    assert provider.calls  # the model was actually called


def test_text_modality_has_no_asr_gate(misconception_set: Sequence[Misconception]) -> None:
    provider = FakeProvider()
    router = _router(provider)
    explanation = TextExplanation(text="eight is more than four so 1/8 is bigger")
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=misconception_set)
    )
    assert result.asr_reliable is True
    assert provider.calls


# --- Closed-set classification ----------------------------------------------


def test_returns_a_closed_set_label_from_the_canned_response(
    misconception_set: Sequence[Misconception],
) -> None:
    router = _router()
    explanation = TextExplanation(text="Well, eight is more than four so I think 1/8 wins.")
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=misconception_set)
    )
    assert result.abstained is False
    assert len(result.labels) == 1
    assert result.labels[0].misconception_code == "M003"
    assert result.labels[0].evidence_span == "eight is more than four"


def test_labels_outside_the_closed_set_are_dropped(
    misconception_set: Sequence[Misconception],
) -> None:
    provider = FakeProvider(
        responses={
            "DiagnosisResult": (
                '{"labels": ['
                '{"misconception_id": "M003", "state": "unresolved", "confidence": 0.6, '
                '"evidence_span": "eight is more than four"}, '
                '{"misconception_id": "M999", "state": "unresolved", "confidence": 0.9, '
                '"evidence_span": "irrelevant"}'
                '], "understanding_signals": [], "asr_reliable": true, "abstained": false}'
            )
        }
    )
    router = _router(provider)
    # M999 has valid MisconceptionCode *shape* but is not one of the 8
    # authored codes -- the closed set is only ever what the caller supplies.
    closed_set = [m for m in misconception_set if m.code != "M999"]
    explanation = TextExplanation(text="eight is more than four")
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=closed_set)
    )
    codes = {label.misconception_code for label in result.labels}
    assert codes == {"M003"}


def test_unverifiable_evidence_span_is_dropped_for_free_text(
    misconception_set: Sequence[Misconception],
) -> None:
    provider = FakeProvider(
        responses={
            "DiagnosisResult": (
                '{"labels": [{"misconception_id": "M003", "state": "unresolved", '
                '"confidence": 0.6, "evidence_span": "a phrase never spoken by the child"}], '
                '"understanding_signals": [], "asr_reliable": true, "abstained": false}'
            )
        }
    )
    router = _router(provider)
    explanation = TextExplanation(text="1/8 is bigger because eight beats four")
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=misconception_set)
    )
    assert result.labels[0].evidence_span is None


def test_manipulative_modality_span_is_not_substring_checked(
    misconception_set: Sequence[Misconception],
) -> None:
    from protege.contracts import ManipulativeAction, ManipulativeExplanation

    provider = FakeProvider(
        responses={
            "DiagnosisResult": (
                '{"labels": [{"misconception_id": "M003", "state": "unresolved", '
                '"confidence": 0.6, "evidence_span": "dragged the 1/8 bar next to the 1/4 bar"}], '
                '"understanding_signals": [], "asr_reliable": true, "abstained": false}'
            )
        }
    )
    router = _router(provider)
    explanation = ManipulativeExplanation(
        manipulative_trace=[ManipulativeAction(t=1.0, action="drag", target="bar_1_8")]
    )
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=misconception_set)
    )
    # A non-free-text modality's span is passed through as the model gave
    # it -- there is no child prose for a substring check to run against.
    assert result.labels[0].evidence_span == "dragged the 1/8 bar next to the 1/4 bar"


# --- Confidence calibration ---------------------------------------------------


def test_calibration_is_applied_to_model_confidences(
    misconception_set: Sequence[Misconception],
) -> None:
    from protege.roles.calibration import CalibrationParams

    router = _router()
    explanation = TextExplanation(text="eight is more than four")
    calibration = CalibrationParams(scale=0.5, bias=0.1)
    result = diagnose(
        router,
        DiagnosticContext(explanation=explanation, misconception_set=misconception_set),
        calibration=calibration,
    )
    # canned raw confidence is 0.62 -> 0.5*0.62 + 0.1 = 0.41
    assert result.labels[0].confidence == pytest.approx(0.41)


def test_calibration_is_not_applied_to_the_rule_based_fallback(
    misconception_set: Sequence[Misconception],
) -> None:
    from protege.roles.calibration import CalibrationParams

    provider = FakeProvider(script=[FakeOutcome.malformed() for _ in range(4)])
    router = _router(provider)
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    explanation = TextExplanation(text="1/8 is bigger")
    uncalibrated = diagnose(
        router,
        DiagnosticContext(
            explanation=explanation,
            misconception_set=misconception_set,
            selected_distractor=distractor,
        ),
    )
    provider2 = FakeProvider(script=[FakeOutcome.malformed() for _ in range(4)])
    router2 = _router(provider2)
    calibrated = diagnose(
        router2,
        DiagnosticContext(
            explanation=explanation,
            misconception_set=misconception_set,
            selected_distractor=distractor,
        ),
        calibration=CalibrationParams(scale=0.1, bias=0.0),
    )
    # The rule-based fallback's confidence is untouched by `calibration` --
    # calibration only ever applies to a model-produced confidence.
    assert calibrated.labels[0].confidence == uncalibrated.labels[0].confidence


# --- Deterministic degradation -----------------------------------------------


def test_invalid_model_output_degrades_to_the_rule_based_fallback(
    misconception_set: Sequence[Misconception],
) -> None:
    # DIAGNOSTICIAN's chain has 2 real entries; each gets max_repairs+1=2
    # attempts, so 4 malformed responses exhaust the chain to the terminal
    # `rule_based_distractor_map` sentinel.
    provider = FakeProvider(script=[FakeOutcome.malformed() for _ in range(4)])
    router = _router(provider)
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    explanation = TextExplanation(text="1/8 is bigger")
    result = diagnose(
        router,
        DiagnosticContext(
            explanation=explanation,
            misconception_set=misconception_set,
            selected_distractor=distractor,
        ),
    )
    assert result.abstained is False
    assert result.labels[0].misconception_code == "M003"
    assert 0.0 <= result.labels[0].confidence <= 1.0


def test_invalid_model_output_with_no_distractor_abstains(
    misconception_set: Sequence[Misconception],
) -> None:
    provider = FakeProvider(script=[FakeOutcome.malformed() for _ in range(4)])
    router = _router(provider)
    explanation = TextExplanation(text="1/8 is bigger")
    result = diagnose(
        router, DiagnosticContext(explanation=explanation, misconception_set=misconception_set)
    )
    assert result.abstained is True
    assert result.labels == []


def test_unexpected_router_exception_degrades_deterministically(
    misconception_set: Sequence[Misconception], monkeypatch: pytest.MonkeyPatch
) -> None:
    router = _router()

    def _boom(*args: object, **kwargs: object) -> object:
        raise RuntimeError("unexpected transport error")

    monkeypatch.setattr(router, "call_structured", _boom)
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    explanation = TextExplanation(text="1/8 is bigger")
    result = diagnose(
        router,
        DiagnosticContext(
            explanation=explanation,
            misconception_set=misconception_set,
            selected_distractor=distractor,
        ),
    )
    assert result.labels[0].misconception_code == "M003"


def test_repeated_deterministic_fallback_calls_are_identical(
    misconception_set: Sequence[Misconception],
) -> None:
    provider = FakeProvider(script=[FakeOutcome.malformed() for _ in range(8)])
    router = _router(provider)
    distractor = Distractor(value="1/8", maps_to="M003", likelihood=0.82)
    explanation = TextExplanation(text="1/8 is bigger")
    context = DiagnosticContext(
        explanation=explanation, misconception_set=misconception_set, selected_distractor=distractor
    )
    first = diagnose(router, context)
    second = diagnose(router, context)
    assert first == second


# --- Misuse -------------------------------------------------------------------


def test_diagnose_raises_on_empty_closed_set() -> None:
    router = _router()
    explanation = TextExplanation(text="1/8 is bigger")
    with pytest.raises(NoClosedSetProvidedError):
        diagnose(router, DiagnosticContext(explanation=explanation, misconception_set=[]))
