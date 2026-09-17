"""The rule-based distractor -> misconception fallback (roadmap P6;
ARCHITECTURE.md §21/§39: "Diagnosis fails -> fall back to
distractor->misconception mapping (deterministic, still works)").

This is the ``DIAGNOSTICIAN`` role's terminal ``ROLE_POLICY`` chain entry
(``packages/llm/src/protege/llm/router.py``: ``"rule_based_distractor_map"``)
-- it never calls a model and never fails on a healthy content pack, so a
total LLM outage degrades diagnosis to a scripted-but-correct result, never
an error (ARCHITECTURE.md §39).

Deliberately narrow: it maps exactly one already-*scored* response's
``Distractor`` (authored, closed-set: ``Distractor.maps_to`` from
``packages/contracts``) to one :class:`~protege.contracts.DiagnosisLabel`.
It does not read free text, does not run NLU, and does not guess -- with no
distractor to map, it abstains (see :func:`rule_based_diagnosis`'s
docstring).

**Why the confidence is a constant, not ``Distractor.likelihood``.**
``Distractor.likelihood`` and ``Misconception.distractor_likelihood`` are
authored from the same table (content/math/fractions/v1: an item's
``Distractor.likelihood`` value matches its misconception's
``distractor_likelihood[behavior_key]`` value exactly) -- it is
``P(this specific wrong text | the child holds M_k)``, a population
phrasing-frequency, **not** ``P(M_k | this text was chosen)``, which is
what a diagnosis confidence needs; reusing it directly conflates the two
and badly miscalibrates confidence (a rare-but-still-diagnostic phrasing
would report a low confidence despite ``maps_to`` being authored as
certain). Unlike the LLM path -- which infers a probabilistic belief from
ambiguous free text -- this path performs a **deterministic lookup** of an
already-authored, already machine-validated fact (P3: "every distractor
maps to a real misconception code"); there is no residual uncertainty in
the lookup itself for :data:`RULE_BASED_CONFIDENCE` to hedge against. The
session-level probabilistic question -- "given this and prior evidence, how
strongly does the learner hold M_k" -- is a genuinely different, Bayesian
question, answered by :mod:`protege.roles.beliefs` via the real P2
``misconception_belief_update`` API (roadmap P6: "Diagnostician feeds
misconception beliefs via the P2 learning engine"), not by this label's
``confidence`` field.
"""

from __future__ import annotations

from collections.abc import Sequence

from protege.contracts import (
    DiagnosisLabel,
    DiagnosisResult,
    Distractor,
    Misconception,
    MisconceptionState,
)

from .errors import DistractorNotInClosedSetError, NoClosedSetProvidedError
from .evidence_span import extract_evidence_span

RULE_BASED_CONFIDENCE = 1.0
"""The rule-based path's diagnosis confidence: certainty, because
``selected_distractor.maps_to`` is an authored, machine-validated fact
looked up verbatim -- not a probabilistic estimate (see module docstring)."""


def rule_based_diagnosis(
    *,
    misconception_set: Sequence[Misconception],
    selected_distractor: Distractor | None,
    source_text: str | None = None,
) -> DiagnosisResult:
    """Deterministic, LLM-free diagnosis from one scored response.

    - No ``misconception_set``: raises :class:`NoClosedSetProvidedError` --
      there is no closed set to classify into (a caller bug, not a runtime
      condition to degrade past).
    - ``selected_distractor is None`` (e.g. the child answered correctly, or
      no response has been scored yet): returns an abstaining result
      (``abstained=True``, no labels) -- degrading to a *guess* would
      violate "the model does NOT invent new misconception IDs" just as
      much as an LLM guess would; abstention is the only honest
      deterministic answer here (roadmap P6: "Model failure must degrade
      deterministically").
    - ``selected_distractor.maps_to`` not in ``misconception_set``: raises
      :class:`DistractorNotInClosedSetError` -- the item bank and the
      caller's closed set have drifted apart, a content-wiring bug.
    - Otherwise: one label with ``state=unresolved`` (a wrong answer is
      evidence the misconception is still held, never evidence it is
      resolved), ``confidence=RULE_BASED_CONFIDENCE``, and an
      ``evidence_span`` extracted from ``source_text`` if one was supplied
      and verifiably contains the distractor's own text.
    """
    if not misconception_set:
        raise NoClosedSetProvidedError

    if selected_distractor is None:
        return DiagnosisResult(
            abstained=True, asr_reliable=True, labels=[], understanding_signals=[]
        )

    closed_set_codes = {m.code for m in misconception_set}
    if selected_distractor.maps_to not in closed_set_codes:
        raise DistractorNotInClosedSetError(selected_distractor.maps_to)

    evidence_span = extract_evidence_span(source_text, selected_distractor.value)
    label = DiagnosisLabel(
        misconception_id=selected_distractor.maps_to,
        state=MisconceptionState.UNRESOLVED,
        confidence=RULE_BASED_CONFIDENCE,
        evidence_span=evidence_span,
    )
    return DiagnosisResult(
        labels=[label],
        understanding_signals=[],
        asr_reliable=True,
        abstained=False,
    )
