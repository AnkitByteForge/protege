"""Load the versioned fractions content pack into P1 contract objects.

Roadmap P3: content lives as version-controlled JSON files under
``content/math/fractions/v1/`` and is validated against the P1 schemas
(``packages/contracts``) in CI. This module only *loads and parses* — it
never edits, repairs, or invents a value. Anything malformed raises
:class:`~protege.authoring.errors.ContentLoadError` with the offending file
and reason; ``validators.py`` runs the semantic (cross-file) checks on top of
what this module returns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from protege.contracts import (
    Intervention,
    LearningItem,
    Misconception,
    Prerequisite,
    Skill,
    SproutScript,
    TransferItem,
    WorkedExample,
)

from .errors import ContentLoadError

_DEFAULT_ROOT = Path(__file__).resolve().parents[5] / "content" / "math" / "fractions" / "v1"
"""``tools/authoring/src/protege/authoring/loader.py`` -> repo root -> content/math/fractions/v1."""


def default_content_root() -> Path:
    """The canonical P3 content package: ``content/math/fractions/v1/``."""
    return _DEFAULT_ROOT


def _read_json(path: Path) -> Any:
    if not path.is_file():
        raise ContentLoadError(str(path), "file does not exist")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentLoadError(str(path), f"invalid JSON: {exc}") from exc


def _parse_list[ModelT: BaseModel](
    path: Path, key: str, model: type[ModelT], *, records: list[Any] | None = None
) -> list[ModelT]:
    """Parse ``{key: [...]}`` at ``path`` into a list of ``model`` instances."""
    if records is None:
        data = _read_json(path)
        if not isinstance(data, dict) or key not in data:
            raise ContentLoadError(str(path), f"expected an object with a '{key}' array")
        records = data[key]
    parsed: list[ModelT] = []
    for index, record in enumerate(records):
        try:
            parsed.append(model.model_validate(record))
        except ValidationError as exc:
            raise ContentLoadError(
                str(path), f"{key}[{index}] failed schema validation: {exc}"
            ) from exc
    return parsed


def _parse_misconceptions(path: Path) -> list[Misconception]:
    """Parse ``misconceptions.json`` via ``Misconception.validate_authored``.

    Per D13 (docs/DECISIONS.md, locked on ``feature/p2-learning``) and the
    ``Misconception`` docstring itself: authoring tooling must call
    ``validate_authored`` rather than the bare ``model_validate``, so that
    new v1 content is required to carry
    ``distractor_likelihood_if_not_misconception`` — only the legacy §38
    fixture (owned by ``packages/contracts``, not this content pack) is
    allowed to omit it.
    """
    data = _read_json(path)
    if not isinstance(data, dict) or "misconceptions" not in data:
        raise ContentLoadError(str(path), "expected an object with a 'misconceptions' array")
    parsed: list[Misconception] = []
    for index, record in enumerate(data["misconceptions"]):
        try:
            parsed.append(Misconception.validate_authored(record))
        except (ValidationError, ValueError) as exc:
            raise ContentLoadError(
                str(path), f"misconceptions[{index}] failed authored validation: {exc}"
            ) from exc
    return parsed


@dataclass(frozen=True)
class ContentPack:
    """Everything loaded from one content package, parsed and raw.

    Parsed lists are P1 contract instances (validated). ``*_raw`` mirrors are
    the original JSON dicts, kept only where a P3-only bookkeeping field
    (e.g. the transfer-item ``pool`` tag) does not belong in a P1 schema and
    so is not retained by ``extra="ignore"`` parsing.
    """

    root: Path
    skills: list[Skill]
    prerequisites: list[Prerequisite]
    misconceptions: list[Misconception]
    sprout_scripts: list[SproutScript]
    interventions: list[Intervention]
    diagnostic_items: list[LearningItem]
    practice_items: list[LearningItem]
    transfer_items: list[TransferItem]
    transfer_items_raw: list[dict[str, Any]] = field(repr=False)
    worked_examples: dict[str, WorkedExample] = field(default_factory=dict)


def load_content_pack(root: Path | None = None) -> ContentPack:
    """Load and schema-validate every file in a content package.

    Raises :class:`ContentLoadError` on the first malformed file or record.
    Does not run cross-file semantic checks (see ``validators.py``).
    """
    root = root or default_content_root()

    skills = _parse_list(root / "skills.json", "skills", Skill)
    prerequisites = _parse_list(root / "prerequisites.json", "prerequisites", Prerequisite)
    misconceptions = _parse_misconceptions(root / "misconceptions.json")
    sprout_scripts = _parse_list(root / "sprout_scripts.json", "sprout_scripts", SproutScript)
    interventions = _parse_list(root / "interventions.json", "interventions", Intervention)
    diagnostic_items = _parse_list(root / "items" / "diagnostic.json", "items", LearningItem)
    practice_items = _parse_list(root / "items" / "practice.json", "items", LearningItem)

    transfer_path = root / "items" / "transfer.json"
    transfer_raw_doc = _read_json(transfer_path)
    if not isinstance(transfer_raw_doc, dict) or "transfer_items" not in transfer_raw_doc:
        raise ContentLoadError(
            str(transfer_path), "expected an object with a 'transfer_items' array"
        )
    transfer_items_raw = list(transfer_raw_doc["transfer_items"])
    transfer_items = _parse_list(
        transfer_path, "transfer_items", TransferItem, records=transfer_items_raw
    )

    worked_examples: dict[str, WorkedExample] = {}
    worked_dir = root / "worked_examples"
    if not worked_dir.is_dir():
        raise ContentLoadError(str(worked_dir), "worked_examples directory does not exist")
    for path in sorted(worked_dir.glob("*.json")):
        data = _read_json(path)
        try:
            example = WorkedExample.model_validate(data)
        except ValidationError as exc:
            raise ContentLoadError(str(path), f"failed WorkedExample validation: {exc}") from exc
        worked_examples[path.stem] = example

    return ContentPack(
        root=root,
        skills=skills,
        prerequisites=prerequisites,
        misconceptions=misconceptions,
        sprout_scripts=sprout_scripts,
        interventions=interventions,
        diagnostic_items=diagnostic_items,
        practice_items=practice_items,
        transfer_items=transfer_items,
        transfer_items_raw=transfer_items_raw,
        worked_examples=worked_examples,
    )
