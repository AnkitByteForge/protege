"""Content and domain entities: the skill graph, the misconception library,
and the item bank (roadmap P1; ARCHITECTURE.md §14, §22, §38).

Field naming follows ARCHITECTURE.md §22 (the database register) with wire
aliases where the §38 worked example uses a different key (``id`` for item
identifiers, ``correct`` for ``correct_answer``), so the §38 document
validates verbatim — that is the P1 exit criterion.

Where §38 omits a field that §22 requires of the database (``description``,
``skill_id``, ``content_version``), the contract keeps it optional: the
contracts are the permissive core vocabulary, and the content package (P3)
adds authoring-time strictness on top. ``Misconception`` applies the same
pattern explicitly (see ``validate_authored``) for
``distractor_likelihood_if_not_misconception`` — the field D13 (locked on
``feature/p2-learning``'s ``docs/DECISIONS.md``) requires.
"""

from typing import Annotated

from pydantic import AliasChoices, Field, model_validator

from .base import ProtegeBaseModel
from .enums import InterventionType, ItemRole, RepresentationType, SproutScriptEmotion
from .ids import (
    ContentVersion,
    EloRating,
    GradeBand,
    InterventionId,
    ItemId,
    MisconceptionCode,
    Probability,
    SkillCode,
    SproutScriptId,
)


class MissingComplementLikelihoodError(ValueError):
    """Raised when a caller needs P(d | not M_k) but a ``Misconception`` has
    no ``distractor_likelihood_if_not_misconception``.

    D13 (locked on ``feature/p2-learning``'s ``docs/DECISIONS.md``) requires
    this term to normalize the independent-Bernoulli Bayes update —
    ``P(M_k | d) = P(d|M_k)P(M_k) / [P(d|M_k)P(M_k) + P(d|¬M_k)(1-P(M_k))]``
    — and explicitly rejects candidate-set normalization as a substitute. P2's
    ``mastery_engine`` must let this propagate rather than substituting a
    default (0, 1, or ``distractor_likelihood``'s ``"other"`` key): a silent
    substitution would silently corrupt the misconception posterior.
    """

    def __init__(self, misconception_code: str) -> None:
        self.misconception_code = misconception_code
        super().__init__(
            f"Misconception {misconception_code!r} has no "
            "distractor_likelihood_if_not_misconception; the §10.2 Bayes update "
            "requires P(d | not M_k) and must not proceed without it."
        )


class Skill(ProtegeBaseModel):
    """Skill graph node (§38; §22 ``skills`` table)."""

    code: SkillCode
    title: str
    grade_band: GradeBand
    prerequisites: list[SkillCode] = Field(default_factory=list)
    standard: str | None = None


class Concept(ProtegeBaseModel):
    """Conceptual grouping of skills.

    Synthesized shape: the roadmap lists ``Concept`` as a P1 entity and
    §10.1 speaks of "concept mastery", but no document defines the fields.
    Modeled as a grouping node over skill codes until P33 (multi-domain)
    forces the general form.
    """

    code: Annotated[str, Field(pattern=r"^C\d{3}$", examples=["C001"])]
    title: str
    description: str
    skill_codes: list[SkillCode] = Field(default_factory=list)


class Prerequisite(ProtegeBaseModel):
    """Directed skill-graph edge ``prereq_of`` (§14 ERD; §22 ``skill_prereq``)."""

    skill_code: SkillCode
    prereq_code: SkillCode


class Misconception(ProtegeBaseModel):
    """The moat: one authored misconception record (§22, §38, roadmap P3).

    ``distractor_likelihood`` is the authored ``P(d | M_k)`` table that the
    misconception Bayes update consumes (§10.2) — authored, never learned.
    Keys are distractor-behavior slugs (§38: ``picks_1_8``, ``says_equal``).
    Its ``"other"`` catch-all key belongs only to this ``M_k``-conditional
    distribution and must never be reused as, or confused with, the
    complement distribution below — the two are authored independently and
    need not (and generally will not) share a common normalization.

    ``distractor_likelihood_if_not_misconception`` is the complementary
    ``P(d | not M_k)`` table required by D13 (locked on
    ``feature/p2-learning``'s ``docs/DECISIONS.md``): §10.2's misconception
    beliefs are independent Bernoullis, and a correct binary Bayes update —
    ``P(M_k | d) = P(d|M_k)P(M_k) / [P(d|M_k)P(M_k) + P(d|¬M_k)(1-P(M_k))]``
    — needs both the numerator likelihood (``distractor_likelihood``) and
    this complement to normalize. §10.2's shorthand
    ``P(M_k | d) ∝ P(d | M_k) · P(M_k)`` elided the complement term; D13
    locks that it is not optional in an actual update, and explicitly
    rejects candidate-set normalization as an alternative.

    The field is nullable: the §38 ``M003`` fixture predates this
    clarification and must keep validating verbatim (P1's exit criterion),
    so ``None`` is accepted here with no error. ``None`` means "this record
    has not been authored against the complement-likelihood requirement" —
    it is never a stand-in for "complement likelihood is zero" or for
    ``distractor_likelihood``'s ``"other"`` bucket.

    New v1 misconception content must supply it: authoring code should call
    ``Misconception.validate_authored`` rather than the bare
    ``model_validate``, and runtime code that needs ``P(d | not M_k)`` (P2's
    Bayes update) must call ``require_complement_likelihood()`` rather than
    reading the optional field directly, so an absent complement likelihood
    raises ``MissingComplementLikelihoodError`` instead of silently
    proceeding with no update, a zero, or the wrong dict.
    """

    code: MisconceptionCode
    title: str
    description: str | None = None
    cognitive_origin: str
    skill_code: SkillCode | None = None
    distractor_likelihood: dict[str, Probability] = Field(default_factory=dict)
    distractor_likelihood_if_not_misconception: dict[str, Probability] | None = Field(
        default=None,
        description=(
            "Authored P(d | not M_k) — the complement of distractor_likelihood, "
            "required to normalize the §10.2 Bayes update. None only for content "
            "authored before this field existed (§38's M003 fixture); new v1 "
            "content must set it (see Misconception.validate_authored)."
        ),
    )
    prevalence_prior: Probability = 0.200
    citation: str | None = None
    sprout_forbidden: list[str] = Field(default_factory=list)
    content_version: ContentVersion | None = None

    @classmethod
    def validate_authored(cls, data: object) -> "Misconception":
        """Strict entry point for newly authored (P3) misconception content.

        Identical to ``model_validate`` except it additionally requires
        ``distractor_likelihood_if_not_misconception`` to be present — the
        §38 fixture is legacy content and uses plain ``model_validate``
        instead, which keeps accepting ``None`` (P1's §38 exit criterion).
        Authoring tooling (P3) is expected to call this, not re-implement
        the check, so the requirement lives exactly once.
        """
        model = cls.model_validate(data)
        if model.distractor_likelihood_if_not_misconception is None:
            raise ValueError(
                f"Misconception {model.code!r}: distractor_likelihood_if_not_misconception "
                "is required for authored v1 content (D13, locked on "
                "feature/p2-learning's docs/DECISIONS.md) — only the legacy §38 "
                "fixture may omit it."
            )
        return model

    def require_complement_likelihood(self) -> dict[str, Probability]:
        """Return ``P(d | not M_k)``, raising rather than returning ``None``.

        Runtime consumers of the Bayes update (P2's ``mastery_engine``) must
        call this instead of reading ``distractor_likelihood_if_not_misconception``
        directly: a missing complement likelihood must fail loudly, never be
        treated as zero, as "no update", or as ``distractor_likelihood``'s
        unrelated ``"other"`` bucket.
        """
        if self.distractor_likelihood_if_not_misconception is None:
            raise MissingComplementLikelihoodError(self.code)
        return self.distractor_likelihood_if_not_misconception


class Distractor(ProtegeBaseModel):
    """One wrong answer option, mapped to the misconception it predicts (§38)."""

    value: str
    maps_to: MisconceptionCode
    likelihood: Probability


class LearningItem(ProtegeBaseModel):
    """A learning/assessment item (§22 ``learning_items``; §38 diagnostic item).

    ``correct_answer`` carries the §22 database name; the §38 wire key
    ``correct`` is accepted via alias. ``skill_code`` is optional because the
    §38 example attaches the skill at the package level.
    """

    item_id: ItemId = Field(alias="id")
    stem: str
    representation: RepresentationType
    correct_answer: str = Field(validation_alias=AliasChoices("correct_answer", "correct"))
    distractors: list[Distractor] = Field(default_factory=list)
    elo: EloRating | None = None
    role: ItemRole = ItemRole.PRACTICE
    skill_code: SkillCode | None = None
    content_version: ContentVersion | None = None


class ItemVersion(ProtegeBaseModel):
    """Immutable content snapshot of one item (§22 ``item_versions``).

    Rollback = flipping the version pointer; versions are never mutated.
    """

    item_id: ItemId
    content_version: ContentVersion
    stem: str
    correct_answer: str
    distractors: list[Distractor] = Field(default_factory=list)
    elo: EloRating | None = None
    representation: RepresentationType | None = None


class Intervention(ProtegeBaseModel):
    """Authored intervention the Coach selects — never invents pedagogy (§38).

    ``historical_success_rate`` seeds Coach retrieval ranking; it is updated
    from outcomes, never from model self-assessment.
    """

    intervention_id: InterventionId = Field(alias="id")
    type: InterventionType
    strategy: str
    script: str
    historical_success_rate: Probability
    misconception_code: MisconceptionCode | None = None


class SproutScript(ProtegeBaseModel):
    """Pre-authored Sprout candidate utterance (§38; §8.1 candidate pool).

    The 30-word cap is the §7.3 Sprout output contract, applied at authoring
    time so the pool itself can never violate it.
    """

    script_id: SproutScriptId = Field(alias="id")
    utterance: str
    emotion: SproutScriptEmotion
    misconception_code: MisconceptionCode | None = None

    @model_validator(mode="after")
    def _max_thirty_words(self) -> "SproutScript":
        if len(self.utterance.split()) > 30:
            raise ValueError("Sprout utterance must be at most 30 words (§7.3)")
        return self


class TransferItem(ProtegeBaseModel):
    """Novel-representation probe for the separate transfer claim (§1.3, §38).

    ``result`` is a runtime observation attached by the verification flow;
    content authoring leaves it None. Transfer failure downgrades the
    transfer claim — it never erases local mastery.
    """

    item_id: ItemId = Field(alias="id")
    stem: str
    representation: RepresentationType
    correct_answer: str = Field(validation_alias=AliasChoices("correct_answer", "correct"))
    elo: EloRating | None = None
    skill_code: SkillCode | None = None
    result: bool | None = None
