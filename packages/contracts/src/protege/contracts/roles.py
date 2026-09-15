"""Role-layer structured-output schemas (ARCHITECTURE.md §7.3 role contracts;
addendum §2.5). These are the schemas the ModelRouter enforces when an LLM
role answers — P4 parses into them, and the educational validator (P2) checks
them after. They are proposals only: none of them has authority.

``SproutTurn`` and ``DiagnosisResult`` are doc-attested. ``CoachHint`` and
``ReportDraft`` are synthesized from the role constraints (§7.3: the Coach
rewrites an authored intervention, §17: a hint must match an authored
``intervention_id``; the Reporter emits sentences that each carry an
``evidence_id`` or are dropped).
"""

from typing import Literal

from pydantic import Field, model_validator

from .base import ProtegeBaseModel
from .enums import SproutConfidenceShown, SproutPresentationEmotion
from .ids import EvidenceId, InterventionId, MisconceptionCode


def _at_most_n_words(text: str, limit: int) -> bool:
    return len(text.split()) <= limit


class SproutTurn(ProtegeBaseModel):
    """One in-character Sprout line (addendum §2.5; §7.3).

    The addendum sample types ``exhibits``/``emotion``/``confidence_shown``
    as bare ``str``; the contracts use the closed enums instead. Sprout may
    not state the correct answer while the misconception is unresolved —
    that check is the deterministic answer-leak validator's job, not this
    schema's.
    """

    utterance: str = Field(description="At most 30 words (§7.3).")
    exhibits: MisconceptionCode
    emotion: SproutPresentationEmotion
    confidence_shown: SproutConfidenceShown

    @model_validator(mode="after")
    def _max_thirty_words(self) -> "SproutTurn":
        if not _at_most_n_words(self.utterance, 30):
            raise ValueError("Sprout utterance must be at most 30 words (§7.3)")
        return self


class CoachHint(ProtegeBaseModel):
    """Coach output: a personalized rewrite of ONE authored intervention.

    ``unauthored_hint_rate`` must be 0 (roadmap P17): every delivered hint
    maps to an authored ``intervention_id`` — enforced downstream by
    checking the id against the content library.
    """

    intervention_id: InterventionId
    text: str
    persona_note: str | None = None


class ReportSentence(ProtegeBaseModel):
    """One sentence of parent/tutor prose with its evidence anchors (§7.3).

    Every sentence must carry at least one ``evidence_id``; the validator
    rejects any sentence without one — that is how "Ava mastered denominator
    magnitude" stays traceable (§17).
    """

    text: str
    evidence_ids: list[EvidenceId] = Field(min_length=1)


class ReportDraft(ProtegeBaseModel):
    """Reporter output: grounded prose from a fixed evidence bundle.

    Claims are enum-selected, not free-written (§17); the ``claim_key``
    carries the selected claim template, and ``audience`` selects the
    parent/tutor surface (§29, §30).
    """

    audience: Literal["parent", "tutor"]
    claim_key: str
    sentences: list[ReportSentence] = Field(min_length=1)
