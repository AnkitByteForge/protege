"""Builds a deterministic ``FakeProvider`` script for a :class:`Scenario`.

Only used for ``--provider fake`` runs (the default when ``NVIDIA_API_KEY``
is unset) and for every unit/integration test (task instruction: "Use
FakeProvider in normal unit/integration tests"). Every Sprout line used
here is one of the six real, already-authored ``SproutScript`` utterances
for M003 (``content/math/fractions/v1/sprout_scripts.json``) -- never
invented text -- standing in for "whatever the real model would have
generated," since that generation is exactly what a canned response
replaces in a fake run. Every Diagnostician JSON body matches the real
:class:`~protege.contracts.DiagnosisResult` schema exactly.
"""

from __future__ import annotations

import json
from collections.abc import Sequence

from protege.contracts import Misconception, SproutScript
from protege.llm.providers.fake import FakeOutcome

from .scenario import RESOLUTION_EVIDENCE_SPAN, Scenario

RESOLVED_CONFIDENCE = 0.89
"""ARCHITECTURE.md §42's own illustrative confidence -- reused here because
this scripted resolution IS the §42 exchange."""

UNRESOLVED_CONFIDENCE = 0.40
UNRESOLVED_EVIDENCE_SPAN = "maybe eighths"
"""A literal substring of ``STUCK_EXPLANATION_TEXT`` (scenario.py) -- the
Diagnostician's evidence-span verification (roadmap P6) drops any span
that is not a real, verbatim quote, so a scripted span must actually
appear in the scripted child text."""


def _sprout_turn_json(utterance: str, misconception_code: str) -> str:
    return json.dumps(
        {
            "utterance": utterance,
            "exhibits": misconception_code,
            # Overwritten by SproutGenerator with the resolution-belief-driven
            # presentation emotion regardless of what is sent here (roadmap
            # P5) -- any valid enum member satisfies the schema.
            "emotion": "confused",
            "confidence_shown": "high",
        }
    )


def _diagnosis_resolved_json(misconception_code: str) -> str:
    return json.dumps(
        {
            "labels": [
                {
                    "misconception_id": misconception_code,
                    "state": "resolved",
                    "confidence": RESOLVED_CONFIDENCE,
                    "evidence_span": RESOLUTION_EVIDENCE_SPAN,
                }
            ],
            "understanding_signals": [
                "inverse_denominator_relationship",
                "partitioning_language",
            ],
            "asr_reliable": True,
            "abstained": False,
        }
    )


def _diagnosis_unresolved_json(misconception_code: str) -> str:
    return json.dumps(
        {
            "labels": [
                {
                    "misconception_id": misconception_code,
                    "state": "unresolved",
                    "confidence": UNRESOLVED_CONFIDENCE,
                    "evidence_span": UNRESOLVED_EVIDENCE_SPAN,
                }
            ],
            "understanding_signals": [],
            "asr_reliable": True,
            "abstained": False,
        }
    )


def build_fake_script(
    scenario: Scenario,
    *,
    misconception: Misconception,
    sprout_scripts: Sequence[SproutScript],
) -> list[FakeOutcome]:
    """Return the ordered ``FakeOutcome`` list for ``scenario``'s
    teach-back turns: one (Sprout, Diagnostician) call pair per turn, in
    the exact order the engine makes them.
    """
    pool = tuple(s for s in sprout_scripts if s.misconception_code == misconception.code)
    outcomes: list[FakeOutcome] = []
    for turn_index, turn in enumerate(scenario.teach_back_turns):
        utterance = pool[turn_index % len(pool)].utterance
        outcomes.append(FakeOutcome.ok(_sprout_turn_json(utterance, misconception.code)))
        diagnosis_json = (
            _diagnosis_resolved_json(misconception.code)
            if turn.resolves
            else _diagnosis_unresolved_json(misconception.code)
        )
        outcomes.append(FakeOutcome.ok(diagnosis_json))
    return outcomes
