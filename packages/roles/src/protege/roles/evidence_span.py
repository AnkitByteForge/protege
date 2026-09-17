"""Evidence-span extraction for the P6 Diagnostician (roadmap P6; §7.3).

Every label's ``evidence_span`` must be a real, verifiable quote (or, for a
non-text modality, a deterministically synthesized description) grounded in
what the child actually did -- never a model-invented paraphrase presented
as a quote. Two responsibilities live here:

1. :func:`describe_explanation` -- turn any of the four teach-back
   modalities (roadmap P13/§1.4: voice, text, manipulative,
   explanation_card) into one plain-text description, used both as the
   model prompt's grounding text and as the source text a candidate span is
   checked against.
2. :func:`extract_evidence_span` -- verify a candidate span is an actual
   substring of that source text (case/whitespace-insensitive); an
   unverifiable span is dropped (``None``), never fabricated or trimmed to
   "close enough".
"""

from __future__ import annotations

from protege.contracts import (
    CardExplanation,
    Explanation,
    ManipulativeAction,
    ManipulativeExplanation,
    TextExplanation,
    VoiceExplanation,
)


def _describe_action(action: ManipulativeAction) -> str:
    targets = (
        action.targets if action.targets is not None else ([action.target] if action.target else [])
    )
    target_desc = ",".join(t for t in targets if t)
    return f"{action.action}:{target_desc}" if target_desc else action.action


def describe_explanation(explanation: Explanation) -> str:
    """A plain-text description of ``explanation``, regardless of modality.

    Voice/text carry a literal ``text`` field and are returned verbatim.
    Manipulative and card explanations carry no free text (roadmap P13: the
    manipulative trace is "a first-class diagnostic input, equal in
    standing to speech") -- this synthesizes a deterministic description
    from the structured trace/card data instead of inventing prose.
    """
    if isinstance(explanation, VoiceExplanation | TextExplanation):
        # `str(...)`: protege.contracts has no py.typed marker (see this
        # workspace's mypy overrides), so `explanation.text` is seen as
        # `Any` here even though it is a genuine `str` at runtime.
        return str(explanation.text)
    if isinstance(explanation, ManipulativeExplanation):
        return "; ".join(_describe_action(a) for a in explanation.manipulative_trace)
    if isinstance(explanation, CardExplanation):
        return "chose cards: " + ", ".join(explanation.card_ids)
    raise TypeError(f"unrecognized explanation modality: {type(explanation)!r}")  # pragma: no cover


def is_free_text_modality(explanation: Explanation) -> bool:
    """Whether ``explanation`` carries child-authored free text (voice/text)
    versus a structured, non-prose trace (manipulative/card).

    Only free-text modalities are checked for a *verbatim quoted* evidence
    span; a manipulative/card span is always the synthesized description
    from :func:`describe_explanation` (there is no prose for a model to
    misquote).
    """
    return isinstance(explanation, VoiceExplanation | TextExplanation)


def extract_evidence_span(source_text: str | None, candidate: str | None) -> str | None:
    """Return ``candidate`` verbatim if it is truly present in
    ``source_text`` (normalized: collapsed whitespace, case-insensitive);
    otherwise ``None``.

    Never fuzzy-matches, truncates, or otherwise invents a "close enough"
    span -- an unverifiable candidate is dropped rather than presented as
    grounded evidence it is not.
    """
    if not source_text or not candidate:
        return None
    normalized_source = " ".join(source_text.split()).lower()
    normalized_candidate = " ".join(candidate.split()).lower()
    if not normalized_candidate:
        return None
    if normalized_candidate in normalized_source:
        return candidate.strip()
    return None
