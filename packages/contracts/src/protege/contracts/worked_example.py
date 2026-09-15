"""The §38 worked-example envelope — the P1 exit criterion.

``docs/PROTEGE_ARCHITECTURE.md`` §38 ("DATA & CONTENT PIPELINE — ONE COMPLETE
WORKED EXAMPLE") defines one complete record spanning skill → misconception →
Sprout scripts → diagnostic item → learner evidence → intervention →
verification → mastery outcome. Roadmap P1 requires that document to validate
against these schemas as a single JSON document; the field names here match
§38 exactly. ``packages/contracts/tests/fixtures/worked_example_m003.json``
is the verbatim fixture.
"""

from pydantic import AliasChoices, Field, model_validator

from .base import ProtegeBaseModel
from .content import Intervention, LearningItem, Misconception, Skill, SproutScript
from .enums import RepresentationType
from .ids import ItemId, Probability
from .learning_state import MasteryOutcome
from .session import DiagnosisResult, ManipulativeAction


class LearnerEvidence(ProtegeBaseModel):
    """What the child did, exactly as §38 records it.

    §38 predates the ``Explanation`` modality discriminator, so the envelope
    carries the raw fields; the session layer (P10) emits the union form.
    The §38 wire key is ``explanation``; ``explanation_text`` is the
    canonical field name (matching the ``text`` naming used elsewhere in the
    session layer), accepted via the same alias-choice pattern as
    ``LearningItem.correct_answer``/``correct``.
    """

    explanation_text: str = Field(validation_alias=AliasChoices("explanation_text", "explanation"))
    asr_confidence: Probability | None = None
    manipulative_trace: list[ManipulativeAction] = Field(default_factory=list)
    diagnosis: DiagnosisResult


class TransferObservation(ProtegeBaseModel):
    """Runtime observation of one attempted transfer probe (§38 verification;
    ARCHITECTURE.md §1.3, §9 TRANSFER state).

    Deliberately distinct from the authored ``TransferItem`` content record
    (content.py): verification observes *which* item was attempted, in what
    representation, and whether it passed — it never carries the authored
    stem/answer. A failed transfer downgrades the transfer *claim*; it does
    not require (or allow) re-deriving the content record here (§1.3
    correction 3: transfer failure never erases local mastery). This mirrors
    the addendum §4 TRANSFER row, whose only recorded data is `responses`
    plus the `transfer_verified` flag — not a duplicated content row.
    """

    item_id: ItemId = Field(alias="id")
    representation: RepresentationType | None = None
    result: bool | None = None


class VerificationRecord(ProtegeBaseModel):
    """Independent verification + transfer observations (§38 verification).

    Verification is LLM-free by rule; this record carries its results. The
    transfer result lives inside ``transfer_item`` (§38) — a failed transfer
    downgrades the transfer claim, never local mastery (§1.3).
    """

    unaided_items: list[ItemId] = Field(min_length=1)
    results: list[bool]
    transfer_item: TransferObservation | None = None

    @model_validator(mode="after")
    def _results_align_with_items(self) -> "VerificationRecord":
        if len(self.results) != len(self.unaided_items):
            raise ValueError(
                f"results ({len(self.results)}) must align with unaided_items "
                f"({len(self.unaided_items)})"
            )
        return self


class WorkedExample(ProtegeBaseModel):
    """One complete authored pipeline record (§38). "Author 8 of these."

    That JSON object, x8, is the intellectual property of the submission
    (§38 closing note) — the misconception library (P3) is exactly this
    envelope, validated.
    """

    skill: Skill
    misconception: Misconception
    sprout_scripts: list[SproutScript] = Field(default_factory=list)
    sprout_forbidden: list[str] = Field(default_factory=list)
    diagnostic_item: LearningItem
    learner_evidence: LearnerEvidence
    intervention: Intervention
    verification: VerificationRecord
    mastery_outcome: MasteryOutcome
