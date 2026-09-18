"""P20 Reporter role tests (roadmap P20 testing requirements:
``ungrounded_sentence_rate`` = 0, ``overclaim_rate`` = 0, the uncertainty
block is never empty, claim selection is deterministic, no-evidence
generation fails closed)."""

from __future__ import annotations

import pytest

from protege.contracts import Intervention, InterventionType
from protege.llm.providers.fake import FakeProvider
from protege.llm.router import ModelRouter
from protege.roles.errors import NoEvidenceForProofError
from protege.roles.reporter import (
    ClaimTemplateKind,
    EvidenceBundle,
    ResponseFact,
    TeachingEpisodeFact,
    TransferFact,
    build_claim_text,
    build_deterministic_sentences,
    build_uncertainty_caveats,
    generate_report,
    select_claim_template,
    select_tonight_action,
)


def _full_bundle() -> EvidenceBundle:
    return EvidenceBundle(
        learner_label="Ava",
        skill_title="Compare unit fractions",
        responses=(
            ResponseFact(evidence_id="e_901", item_id="i_0148", correct=True, unaided=True),
            ResponseFact(evidence_id="e_902", item_id="i_0155", correct=True, unaided=True),
            ResponseFact(evidence_id="e_903", item_id="i_0161", correct=True, unaided=True),
        ),
        teaching_episodes=(
            TeachingEpisodeFact(
                evidence_id="e_904",
                misconception_code="M003",
                misconception_title="Larger denominator means larger fraction",
                resolved=True,
                resolution_turn=4,
            ),
        ),
        transfer=TransferFact(
            evidence_id="e_905", item_id="i_0201", representation="number_line", result=True
        ),
    )


def test_empty_bundle_fails_closed() -> None:
    with pytest.raises(NoEvidenceForProofError):
        EvidenceBundle(learner_label="Ava", skill_title="Compare unit fractions")


def test_select_claim_template_is_deterministic() -> None:
    assert select_claim_template(mastery_verified=True) == ClaimTemplateKind.MASTERED
    assert select_claim_template(mastery_verified=False) == ClaimTemplateKind.PRACTICED


def test_claim_text_never_uses_forbidden_vocabulary() -> None:
    text = build_claim_text(
        ClaimTemplateKind.MASTERED, learner_label="Ava", skill_title="Compare unit fractions"
    )
    assert text == "Ava can compare unit fractions."
    for banned in ("%", "percent", "score", "mastery", "mastered"):
        assert banned not in text.lower()


def test_deterministic_sentences_are_fully_grounded() -> None:
    bundle = _full_bundle()
    sentences = build_deterministic_sentences(bundle)
    allowed = set(bundle.all_evidence_ids())
    assert sentences  # never empty for a non-empty bundle
    for sentence in sentences:
        assert sentence.evidence_ids  # min_length=1 already enforced by the schema
        assert set(sentence.evidence_ids).issubset(allowed)


def test_generate_report_falls_back_to_deterministic_template_by_default() -> None:
    """The router's stock ``ReportDraft`` canned response (see
    ``FakeProvider.DEFAULT_CANNED_RESPONSES``) carries a different
    ``claim_key`` than the one this call selects -- so the LLM candidate
    must be rejected outright and the deterministic fallback used."""
    bundle = _full_bundle()
    router = ModelRouter({"nvidia": FakeProvider()})

    result = generate_report(router, bundle=bundle, claim_key=ClaimTemplateKind.MASTERED)

    assert result.used_fallback is True
    assert result.draft.claim_key == ClaimTemplateKind.MASTERED.value
    allowed = set(bundle.all_evidence_ids())
    for sentence in result.draft.sentences:
        assert set(sentence.evidence_ids).issubset(allowed)


def test_generate_report_accepts_a_grounded_matching_candidate() -> None:
    bundle = _full_bundle()
    router = ModelRouter(
        {
            "nvidia": FakeProvider(
                responses={
                    "ReportDraft": (
                        '{"audience": "parent", "claim_key": "mastered", '
                        '"sentences": [{"text": "Ava taught Sprout the correct rule.", '
                        '"evidence_ids": ["e_904"]}]}'
                    )
                }
            )
        }
    )

    result = generate_report(router, bundle=bundle, claim_key=ClaimTemplateKind.MASTERED)

    assert result.used_fallback is False
    assert [s.text for s in result.draft.sentences] == ["Ava taught Sprout the correct rule."]


def test_generate_report_drops_sentences_citing_unknown_evidence_ids() -> None:
    bundle = _full_bundle()
    router = ModelRouter(
        {
            "nvidia": FakeProvider(
                responses={
                    "ReportDraft": (
                        '{"audience": "parent", "claim_key": "mastered", "sentences": ['
                        '{"text": "Ava taught Sprout the correct rule.", '
                        '"evidence_ids": ["e_904"]}, '
                        '{"text": "Ava did something we never actually saw.", '
                        '"evidence_ids": ["e_999_not_real"]}'
                        "]}"
                    )
                }
            )
        }
    )

    result = generate_report(router, bundle=bundle, claim_key=ClaimTemplateKind.MASTERED)

    assert result.used_fallback is False
    texts = [s.text for s in result.draft.sentences]
    assert texts == ["Ava taught Sprout the correct rule."]
    assert "Ava did something we never actually saw." not in texts


def test_generate_report_drops_overclaiming_sentences_and_falls_back() -> None:
    """Every sentence in the candidate uses forbidden vocabulary (an
    overclaim in the parent register) -- all are dropped, so the whole
    candidate is rejected and the deterministic fallback is used instead
    (``overclaim_rate`` = 0)."""
    bundle = _full_bundle()
    router = ModelRouter(
        {
            "nvidia": FakeProvider(
                responses={
                    "ReportDraft": (
                        '{"audience": "parent", "claim_key": "mastered", '
                        '"sentences": [{"text": "Ava scored 100 percent and reached mastery.", '
                        '"evidence_ids": ["e_904"]}]}'
                    )
                }
            )
        }
    )

    result = generate_report(router, bundle=bundle, claim_key=ClaimTemplateKind.MASTERED)

    assert result.used_fallback is True
    for sentence in result.draft.sentences:
        assert "percent" not in sentence.text.lower()
        assert "mastery" not in sentence.text.lower()


def test_uncertainty_block_is_never_empty() -> None:
    assert build_uncertainty_caveats() != []
    assert build_uncertainty_caveats(open_misconception_titles=["Adding fractions"]) != []
    assert (
        build_uncertainty_caveats(
            transfer=TransferFact(
                evidence_id="e_905", item_id="i_0201", representation="number_line", result=True
            )
        )
        != []
    )


def test_transfer_verified_is_tracked_separately_from_the_claim() -> None:
    bundle = _full_bundle()
    assert bundle.transfer_verified is True
    assert bundle.transfer_attempted_count == 1

    unresolved_transfer_bundle = EvidenceBundle(
        learner_label="Ava",
        skill_title="Compare unit fractions",
        transfer=TransferFact(
            evidence_id="e_905", item_id="i_0201", representation="number_line", result=False
        ),
    )
    assert unresolved_transfer_bundle.transfer_verified is False
    assert unresolved_transfer_bundle.transfer_attempted_count == 1


def test_select_tonight_action_prefers_analogy_and_is_authored() -> None:
    interventions = [
        Intervention(
            id="INT_M003_A",
            type=InterventionType.VISUALIZATION,
            strategy="same_whole_partition_contrast",
            script="Let's cut the SAME pizza two ways and lay them on top of each other.",
            historical_success_rate=0.78,
            misconception_code="M003",
        ),
        Intervention(
            id="INT_M003_B",
            type=InterventionType.ANALOGY,
            strategy="same_size_pizza_more_friends",
            script="Imagine the SAME pizza shared with more friends.",
            historical_success_rate=0.71,
            misconception_code="M003",
        ),
    ]

    action = select_tonight_action(misconception_code="M003", interventions=interventions)

    assert action is not None
    assert "Imagine the SAME pizza shared with more friends." in action
    assert "2 minutes" in action


def test_select_tonight_action_returns_none_when_unauthored() -> None:
    assert select_tonight_action(misconception_code="M999", interventions=[]) is None
