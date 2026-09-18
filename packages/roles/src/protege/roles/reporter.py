"""The P20 Reporter role (roadmap P20; ARCHITECTURE.md §17 provenance chain,
§29 parent proof card).

The Reporter never decides WHAT was learned -- it only narrates a
``EvidenceBundle`` that the caller (P20's ``engine/proof.py``) already
assembled from P9's authoritative evidence/mastery rows. Three
non-negotiables, enforced here rather than merely documented (mirroring
P5 Sprout's and P6 Diagnostician's own "enforced, not promised" pattern):

1. **Claims are enum-selected, not free-written** (roadmap P20). The caller
   decides ``ClaimTemplateKind`` from the existing P2 mastery threshold --
   never the LLM. If a model candidate disagrees with the ``claim_key`` it
   was given, its entire output is discarded, not repaired.
2. **Every sentence carries an evidence_id or is dropped**
   (``ungrounded_sentence_rate`` = 0). ``_filter_grounded`` whitelists
   against exactly the evidence ids the bundle itself carries -- an id the
   model invents, or one that belongs to a different bundle, cannot survive.
3. **A deterministic, always-available fallback**
   (:func:`build_deterministic_sentences`) -- the same "authored/template
   content always available" shape as Sprout's authored fallback and
   Coach's authored-intervention rewrite. Every fallback sentence is built
   directly from the bundle's own facts, so it is grounded by construction.

Nothing here calls a database or the session orchestrator: :class:`EvidenceBundle`
is a plain, already-resolved value the caller supplies (mirrors P6
``DiagnosticContext``'s "everything one call needs, already resolved").
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from protege.contracts import (
    Intervention,
    InterventionType,
    PedagogicalRole,
    ReportDraft,
    ReportSentence,
)
from protege.learning_engine.educational_validator import contains_forbidden_phrase
from protege.llm.base import Message
from protege.llm.router import ModelRouter

from .errors import NoEvidenceForProofError

PROMPT_VERSION = "reporter-v1"

# Reused verbatim in spirit from the child-facing forbidden-vocabulary rule
# (roadmap P20: "no scores, no percentages, no letter grades ... no
# child-facing technical vocabulary"), extended to the parent register: a
# parent-facing claim/sentence must never smuggle in the internal metric
# vocabulary the proof card's whole design exists to translate away from.
PARENT_FORBIDDEN_PHRASES: tuple[str, ...] = (
    "%",
    "percent",
    "score",
    "mastery",
    "mastered",
    " ai ",
    "artificial intelligence",
    "language model",
    "the model",
    "algorithm",
)


# --- Evidence bundle (caller-assembled; see engine/proof.py) ----------------


@dataclass(frozen=True)
class ResponseFact:
    """One ``"response"``-kind evidence row's parent-relevant facts."""

    evidence_id: str
    item_id: str
    correct: bool
    unaided: bool


@dataclass(frozen=True)
class TeachingEpisodeFact:
    """One ``"teaching_episode"``-kind evidence row's parent-relevant facts."""

    evidence_id: str
    misconception_code: str
    misconception_title: str
    resolved: bool
    resolution_turn: int | None = None


@dataclass(frozen=True)
class TransferFact:
    """The ``"transfer"``-kind evidence row's parent-relevant facts, if any."""

    evidence_id: str
    item_id: str
    representation: str | None
    result: bool | None


@dataclass(frozen=True)
class EvidenceBundle:
    """Everything one proof card's Reporter call needs, already resolved by
    the caller from P9's own repositories -- this module never queries a
    database (task instruction: no I/O in role packages).

    Raises :class:`~.errors.NoEvidenceForProofError` at construction if
    every fact list is empty -- roadmap P20: "no-evidence proof generation
    fails closed." A caller assembling a bundle for a session with zero
    recorded evidence must never reach this far; this is the last line of
    defense against silently emitting a fabricated card.
    """

    learner_label: str
    skill_title: str
    responses: tuple[ResponseFact, ...] = ()
    teaching_episodes: tuple[TeachingEpisodeFact, ...] = ()
    transfer: TransferFact | None = None

    def __post_init__(self) -> None:
        if not self.responses and not self.teaching_episodes and self.transfer is None:
            raise NoEvidenceForProofError(self.learner_label)

    @property
    def unaided_responses(self) -> tuple[ResponseFact, ...]:
        return tuple(r for r in self.responses if r.unaided)

    @property
    def unaided_correct_count(self) -> int:
        return sum(1 for r in self.unaided_responses if r.correct)

    @property
    def unaided_attempted_count(self) -> int:
        return len(self.unaided_responses)

    @property
    def transfer_attempted_count(self) -> int:
        """§2 threshold input: whether a transfer item was attempted at all
        (never whether it passed -- ``PROTEGE_ARCHITECTURE.md`` §1.3
        correction 3 keeps that a claim-downgrade concern, not a threshold
        one; see ``protege.learning_engine.threshold_service``)."""
        return 1 if self.transfer is not None else 0

    @property
    def transfer_verified(self) -> bool:
        """Shown SEPARATELY from the mastery claim on the parent card
        (roadmap P20 requirement) -- never folded into ``claim_key``."""
        return bool(self.transfer is not None and self.transfer.result)

    @property
    def resolved_teaching_episode(self) -> TeachingEpisodeFact | None:
        return next((e for e in self.teaching_episodes if e.resolved), None)

    def all_evidence_ids(self) -> tuple[str, ...]:
        ids = [r.evidence_id for r in self.responses]
        ids += [e.evidence_id for e in self.teaching_episodes]
        if self.transfer is not None:
            ids.append(self.transfer.evidence_id)
        return tuple(ids)


# --- Claim templates (enum-selected, never free-written) --------------------


class ClaimTemplateKind(StrEnum):
    """The closed set of parent-facing claim templates (roadmap P20:
    "claim templates are enum-selected, not free-written"; ARCHITECTURE.md
    §17 hallucination-control table, "Parent report" row: "Claims are
    enum-selected... Fallback: Downgrade to 'practiced'")."""

    MASTERED = "mastered"
    PRACTICED = "practiced"


def select_claim_template(*, mastery_verified: bool) -> ClaimTemplateKind:
    """The ONE piece of code that decides which claim template applies --
    always from the existing P2 ``evaluate_mastery_threshold`` decision
    (the caller's job), never from anything an LLM proposes."""
    return ClaimTemplateKind.MASTERED if mastery_verified else ClaimTemplateKind.PRACTICED


_CLAIM_TEXT_TEMPLATES: dict[ClaimTemplateKind, str] = {
    ClaimTemplateKind.MASTERED: "{learner} can {skill}.",
    ClaimTemplateKind.PRACTICED: "{learner} practiced {skill} today.",
}


def build_claim_text(kind: ClaimTemplateKind, *, learner_label: str, skill_title: str) -> str:
    """Render the enum-selected template -- the only place claim TEXT is
    produced; never LLM output (§38 worked example: ``"claim": "Ava can
    compare unit fractions"``, i.e. the skill title lower-cased into a verb
    phrase, exactly what this does)."""
    skill_phrase = skill_title[:1].lower() + skill_title[1:] if skill_title else skill_title
    return _CLAIM_TEXT_TEMPLATES[kind].format(learner=learner_label, skill=skill_phrase)


# --- Deterministic sentence fallback (always grounded, always available) ----


def build_deterministic_sentences(bundle: EvidenceBundle) -> list[ReportSentence]:
    """The Reporter's authored-fallback equivalent (roadmap P4
    ``ROLE_POLICY[REPORTER]``'s terminal ``pure_template`` sentinel; same
    shape as Sprout's ``emit_authored_fallback``). Every sentence is built
    directly from ``bundle``'s own facts, so it is grounded by
    construction -- no filter is needed on this path, only on LLM output.

    Raises :class:`~.errors.NoEvidenceForProofError` if it somehow produces
    nothing (defensive: ``EvidenceBundle.__post_init__`` already guarantees
    at least one fact exists, so this should be unreachable in practice).
    """
    sentences: list[ReportSentence] = []

    episode = bundle.resolved_teaching_episode
    if episode is not None:
        sentences.append(
            ReportSentence(
                text=(
                    f"{bundle.learner_label} taught Sprout the correct idea about "
                    f"{episode.misconception_title[:1].lower()}{episode.misconception_title[1:]}."
                ),
                evidence_ids=[episode.evidence_id],
            )
        )

    if bundle.unaided_attempted_count:
        sentences.append(
            ReportSentence(
                text=(
                    f"{bundle.learner_label} got {bundle.unaided_correct_count} of "
                    f"{bundle.unaided_attempted_count} new problems right without any hints."
                ),
                evidence_ids=[r.evidence_id for r in bundle.unaided_responses],
            )
        )

    if bundle.transfer is not None:
        transfer = bundle.transfer
        where = (
            f" on a {transfer.representation.replace('_', ' ')}" if transfer.representation else ""
        )
        outcome = "solved a new problem" if transfer.result else "tried a new kind of problem"
        sentences.append(
            ReportSentence(
                text=f"{bundle.learner_label} {outcome}{where} they hadn't seen before.",
                evidence_ids=[transfer.evidence_id],
            )
        )

    if not sentences:  # pragma: no cover - EvidenceBundle already guarantees this
        raise NoEvidenceForProofError(bundle.learner_label)
    return sentences


# --- LLM-narrated path (grounded, validated, falls back on any violation) ---

_SYSTEM_PROMPT = """You are the PROTÉGÉ Reporter. You write short, warm sentences for a PARENT \
about ONE completed learning session. You are not talking to the child, and you are not a tutor.

Rules, no exceptions:
1. Every sentence must be built ONLY from the FACTS block you are given. Never state a fact \
that is not listed there, and never guess at what might have happened.
2. Every sentence needs an "evidence_ids" list containing ONLY ids that appear in the FACTS \
block, in square brackets. Never invent an id, and never leave the list empty.
3. Use the exact CLAIM_KEY you are given, unchanged, as the "claim_key" field.
4. Never use the words "score", "percent", "mastery", "mastered", "AI", "algorithm", or "model". \
Never write a number as a percentage.
5. Keep sentences short, warm, and specific to what actually happened -- like a caring teacher \
describing one real moment, not a report card.
6. Respond with ONLY a JSON object matching the requested schema. No prose, no markdown fences.
"""


def _facts_block(bundle: EvidenceBundle) -> str:
    lines: list[str] = []
    for response in bundle.responses:
        hint_note = "without hints" if response.unaided else "with hints available"
        outcome = "correctly" if response.correct else "incorrectly"
        lines.append(f"- [{response.evidence_id}] answered a problem {outcome}, {hint_note}")
    for episode in bundle.teaching_episodes:
        state = (
            f"resolved at turn {episode.resolution_turn}"
            if episode.resolved
            else "still unresolved"
        )
        lines.append(
            f"- [{episode.evidence_id}] taught Sprout about "
            f"'{episode.misconception_title}' -- {state}"
        )
    if bundle.transfer is not None:
        transfer = bundle.transfer
        rep = f" ({transfer.representation})" if transfer.representation else ""
        result = (
            "correct"
            if transfer.result
            else "incorrect"
            if transfer.result is not None
            else "not scored"
        )
        lines.append(f"- [{transfer.evidence_id}] transfer problem{rep}: {result}")
    return "\n".join(lines)


def build_reporter_messages(
    bundle: EvidenceBundle, *, claim_key: ClaimTemplateKind
) -> list[Message]:
    user_content = (
        f"LEARNER: {bundle.learner_label}\n"
        f"SKILL: {bundle.skill_title}\n"
        f"CLAIM_KEY: {claim_key.value}\n\n"
        f"FACTS (cite only these evidence ids -- never any other):\n{_facts_block(bundle)}"
    )
    return [Message("system", _SYSTEM_PROMPT), Message("user", user_content)]


def _filter_grounded(
    sentences: Sequence[ReportSentence], *, allowed_evidence_ids: set[str]
) -> list[ReportSentence]:
    """Drop any sentence citing an id outside ``allowed_evidence_ids``, or
    containing parent-forbidden vocabulary. This is the enforcement point
    for ``ungrounded_sentence_rate`` = 0 and ``overclaim_rate`` = 0
    (roadmap P20 testing requirements) on the LLM-generated path."""
    kept: list[ReportSentence] = []
    for sentence in sentences:
        if not sentence.evidence_ids:
            continue
        if any(evidence_id not in allowed_evidence_ids for evidence_id in sentence.evidence_ids):
            continue
        if contains_forbidden_phrase(sentence.text, PARENT_FORBIDDEN_PHRASES) is not None:
            continue
        kept.append(sentence)
    return kept


@dataclass(frozen=True)
class ReporterResult:
    draft: ReportDraft
    used_fallback: bool


def generate_report(
    router: ModelRouter,
    *,
    bundle: EvidenceBundle,
    claim_key: ClaimTemplateKind,
    audience: str = "parent",
    trace_id: str | None = None,
) -> ReporterResult:
    """Generate one ``ReportDraft`` for ``bundle`` (roadmap P20: "Reporter
    writes prose only from a fixed evidence bundle").

    Tries the LLM path once through the P4 ``ModelRouter``
    (``ROLE_POLICY[REPORTER]``): a candidate is accepted only if it kept the
    exact ``claim_key`` it was given AND at least one of its sentences
    survives grounding. Any other outcome -- the router's own deterministic
    fallback (``pure_template``), an unexpected exception, a claim_key
    mismatch, or every sentence failing grounding -- falls through to
    :func:`build_deterministic_sentences`, which is always grounded by
    construction and therefore always available (mirrors Sprout's "the
    authored fallback must always be available").
    """
    allowed_evidence_ids = set(bundle.all_evidence_ids())
    messages = build_reporter_messages(bundle, claim_key=claim_key)

    try:
        outcome = router.call_structured(PedagogicalRole.REPORTER, messages, trace_id=trace_id)
    except Exception:
        outcome = None

    if (
        outcome is not None
        and not outcome.used_deterministic_fallback
        and isinstance(outcome.value, ReportDraft)
        and outcome.value.claim_key == claim_key.value
    ):
        grounded = _filter_grounded(
            outcome.value.sentences, allowed_evidence_ids=allowed_evidence_ids
        )
        if grounded:
            return ReporterResult(
                draft=ReportDraft(audience=audience, claim_key=claim_key.value, sentences=grounded),
                used_fallback=False,
            )

    fallback_sentences = build_deterministic_sentences(bundle)
    return ReporterResult(
        draft=ReportDraft(
            audience=audience, claim_key=claim_key.value, sentences=fallback_sentences
        ),
        used_fallback=True,
    )


# --- Uncertainty block (mandatory, never empty) ------------------------------


def build_uncertainty_caveats(
    *,
    open_misconception_titles: Sequence[str] = (),
    transfer: TransferFact | None = None,
) -> list[str]:
    """The "not yet confirmed" block (roadmap P20: "mandatory non-empty
    uncertainty block"; ARCHITECTURE.md §29: "a report with no uncertainty
    is a report that is lying").

    Every entry here is either a real fact about what was NOT assessed
    (an unresolved misconception this learner has, or a transfer check
    limited to one representation) or, only when literally nothing else
    applies, an honest statement about future re-verification -- never a
    fabricated claim about the child, so it needs no ``evidence_id``
    (matching ``ProofClaim.caveats: list[str]``'s existing plain-string
    shape, not ``ReportSentence``'s evidence-bound one).
    """
    caveats: list[str] = [
        f"Not yet checked: {title[:1].lower()}{title[1:]}." for title in open_misconception_titles
    ]
    if transfer is not None and transfer.representation:
        rep = transfer.representation.replace("_", " ")
        caveats.append(f"So far only checked with a {rep} -- we'll try it a different way soon.")
    if not caveats:
        caveats.append("We'll check this again in a future session to make sure it's holding.")
    return caveats


# --- Tonight's action (authored, never LLM-invented) -------------------------


def select_tonight_action(
    *, misconception_code: str, interventions: Sequence[Intervention]
) -> str | None:
    """One concrete ~2-minute action (roadmap P20 requirement), built from
    an AUTHORED P3 ``Intervention`` -- the Reporter never invents pedagogy,
    exactly as P17's Coach only ever rewrites an authored intervention.
    Prefers the ``ANALOGY`` type (the most parent-doable-tonight framing of
    the three authored types); falls back to the first authored
    intervention for this misconception. ``None`` if none is authored.
    """
    pool = [i for i in interventions if i.misconception_code == misconception_code]
    if not pool:
        return None
    preferred = next((i for i in pool if i.type == InterventionType.ANALOGY), pool[0])
    return f"Tonight, try this for about 2 minutes: {preferred.script}"
