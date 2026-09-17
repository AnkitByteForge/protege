"""The P6 Diagnostician golden set (roadmap P6: "120-item hand-labelled
golden set").

**Provenance, stated plainly (see ``golden_set/PROVENANCE.md``): this set is
machine-derived, deterministically, from content already authored and
checked into ``content/math/fractions/v1/`` for P3 (Sprout candidate
utterances, worked-example child explanations, and item-bank distractors).
It is NOT independently hand-labelled by a human rater, NOT Fable-generated
in this session, and carries no human ratification -- the same
NOT-RATIFIED status the underlying P3 content itself has
(``content/math/fractions/v1/RATIFICATION.md``: "Status: NOT RATIFIED").**
This module never claims otherwise; nothing here sets a ratified status.

Each of the 8 misconceptions contributes exactly 15 examples (120 total,
balanced for a meaningful macro-F1):

- 6 Sprout candidate utterances (``sprout_scripts.json``) -- unresolved,
  in-character confused reasoning exhibiting the misconception.
- 1 worked-example child explanation (``worked_examples/M0XX.json``) --
  resolved, correct reasoning that specifically addresses the misconception.
- 8 distractor-templated utterances, one per authored diagnostic-item
  distractor (``items/diagnostic.json``) -- unresolved, and (unlike the
  first two sources) each carries the real authored ``Distractor`` it was
  templated from, which is what lets :mod:`protege.roles.eval` measure the
  rule-based fallback in isolation on exactly the evidence type it is
  designed for.

:func:`generate_golden_set` reads the live content pack (via
``protege.authoring.loader.load_content_pack``) and is the one place that
dependency is used. :func:`load_golden_set` reads the frozen, checked-in
JSON snapshot and has no dependency on ``protege.authoring`` at all -- tests
and the eval harness use only this.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from protege.authoring.loader import ContentPack, load_content_pack
from protege.contracts import TextExplanation

GoldenSource = Literal["sprout_script", "worked_example", "distractor_template"]

_GOLDEN_SET_DIR = Path(__file__).resolve().parents[3] / "golden_set"
"""``packages/roles/src/protege/roles/golden_set.py`` -> ``packages/roles/golden_set/``."""

_DEFAULT_SNAPSHOT = _GOLDEN_SET_DIR / "diagnostician_v1.json"

_SPROUT_SCRIPTS_PER_CODE = 6
_DISTRACTORS_PER_CODE = 8


@dataclass(frozen=True)
class GoldenDistractor:
    """The real authored ``Distractor`` a ``distractor_template`` example
    was generated from -- lets the eval harness run the rule-based fallback
    on exactly the input shape it is designed for."""

    value: str
    maps_to: str
    likelihood: float


@dataclass(frozen=True)
class GoldenExample:
    """One golden-set record: a piece of text, its ground-truth
    misconception code, and (for ``distractor_template`` records only) the
    authored distractor it was templated from."""

    id: str
    misconception_code: str
    state: Literal["unresolved", "resolved"]
    text: str
    source: GoldenSource
    distractor: GoldenDistractor | None = None

    def to_explanation(self) -> TextExplanation:
        return TextExplanation(id=self.id, text=self.text)


def generate_golden_set(content_pack: ContentPack | None = None) -> list[GoldenExample]:
    """Deterministically build the 120-item golden set from the live P3
    content pack. Iteration order is the content files' own authored
    order, so re-running this against an unchanged content pack is
    byte-for-byte reproducible.
    """
    pack = content_pack if content_pack is not None else load_content_pack()

    scripts_by_code: dict[str, list[str]] = {}
    for script in pack.sprout_scripts:
        code = script.misconception_code
        if code is None:
            continue
        scripts_by_code.setdefault(code, []).append(script.utterance)

    distractors_by_code: dict[str, list[tuple[str, str, float]]] = {}
    for item in pack.diagnostic_items:
        for distractor in item.distractors:
            distractors_by_code.setdefault(distractor.maps_to, []).append(
                (item.stem, distractor.value, distractor.likelihood)
            )

    examples: list[GoldenExample] = []
    for misconception in pack.misconceptions:
        code = misconception.code

        utterances = scripts_by_code.get(code, [])[:_SPROUT_SCRIPTS_PER_CODE]
        for index, utterance in enumerate(utterances, start=1):
            examples.append(
                GoldenExample(
                    id=f"gs_{code}_script_{index:02d}",
                    misconception_code=code,
                    state="unresolved",
                    text=utterance,
                    source="sprout_script",
                )
            )

        worked_example = pack.worked_examples.get(code)
        if worked_example is not None:
            examples.append(
                GoldenExample(
                    id=f"gs_{code}_worked_01",
                    misconception_code=code,
                    state="resolved",
                    text=worked_example.learner_evidence.explanation_text,
                    source="worked_example",
                )
            )

        item_distractors = distractors_by_code.get(code, [])[:_DISTRACTORS_PER_CODE]
        for index, (stem, value, likelihood) in enumerate(item_distractors, start=1):
            examples.append(
                GoldenExample(
                    id=f"gs_{code}_distractor_{index:02d}",
                    misconception_code=code,
                    state="unresolved",
                    text=f'For "{stem}" I think the answer is {value}.',
                    source="distractor_template",
                    distractor=GoldenDistractor(value=value, maps_to=code, likelihood=likelihood),
                )
            )

    return examples


def _example_to_json(example: GoldenExample) -> dict[str, object]:
    data = asdict(example)
    return data


def _example_from_json(data: dict[str, object]) -> GoldenExample:
    distractor_data = data.get("distractor")
    distractor = GoldenDistractor(**distractor_data) if isinstance(distractor_data, dict) else None
    return GoldenExample(
        id=str(data["id"]),
        misconception_code=str(data["misconception_code"]),
        state=data["state"],  # type: ignore[arg-type]
        text=str(data["text"]),
        source=data["source"],  # type: ignore[arg-type]
        distractor=distractor,
    )


def save_golden_set(examples: Sequence[GoldenExample], path: Path = _DEFAULT_SNAPSHOT) -> None:
    payload = {
        "schema_version": "1.0",
        "count": len(examples),
        "examples": [_example_to_json(e) for e in examples],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_golden_set(path: Path = _DEFAULT_SNAPSHOT) -> list[GoldenExample]:
    """Read the frozen, checked-in 120-item snapshot. No dependency on
    ``protege.authoring`` -- this is what tests and the eval harness use."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return [_example_from_json(record) for record in data["examples"]]
