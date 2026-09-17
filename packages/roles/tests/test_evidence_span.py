from __future__ import annotations

from protege.contracts import (
    CardExplanation,
    ManipulativeAction,
    ManipulativeExplanation,
    TextExplanation,
    VoiceExplanation,
)
from protege.roles.evidence_span import (
    describe_explanation,
    extract_evidence_span,
    is_free_text_modality,
)


def test_describe_voice_explanation_returns_its_text() -> None:
    explanation = VoiceExplanation(text="eight is more than four", asr_confidence=0.9)
    assert describe_explanation(explanation) == "eight is more than four"
    assert is_free_text_modality(explanation) is True


def test_describe_text_explanation_returns_its_text() -> None:
    explanation = TextExplanation(text="1/8 is bigger")
    assert describe_explanation(explanation) == "1/8 is bigger"
    assert is_free_text_modality(explanation) is True


def test_describe_manipulative_explanation_synthesizes_from_trace() -> None:
    explanation = ManipulativeExplanation(
        manipulative_trace=[
            ManipulativeAction(t=2.1, action="drag", target="bar_1_4"),
            ManipulativeAction(t=4.8, action="align", targets=["bar_1_4", "bar_1_8"]),
        ]
    )
    description = describe_explanation(explanation)
    assert "drag:bar_1_4" in description
    assert "align:bar_1_4,bar_1_8" in description
    assert is_free_text_modality(explanation) is False


def test_describe_card_explanation_synthesizes_from_card_ids() -> None:
    explanation = CardExplanation(card_ids=["card_a", "card_b"])
    assert describe_explanation(explanation) == "chose cards: card_a, card_b"
    assert is_free_text_modality(explanation) is False


def test_extract_evidence_span_exact_match() -> None:
    assert extract_evidence_span("eight is more than four", "eight is more than four") == (
        "eight is more than four"
    )


def test_extract_evidence_span_is_case_and_whitespace_insensitive() -> None:
    source = "Hmm,   EIGHT is more than   four right?"
    candidate = "eight is more than four"
    assert extract_evidence_span(source, candidate) == candidate


def test_extract_evidence_span_returns_none_when_not_present() -> None:
    assert extract_evidence_span("1/8 is bigger", "totally unrelated phrase") is None


def test_extract_evidence_span_returns_none_for_empty_inputs() -> None:
    assert extract_evidence_span(None, "x") is None
    assert extract_evidence_span("x", None) is None
    assert extract_evidence_span("x", "") is None
