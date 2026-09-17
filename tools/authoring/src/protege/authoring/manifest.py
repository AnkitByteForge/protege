"""The P3 content manifest: a machine-generated report, not a sign-off.

Roadmap P3 "Human ratification": machine validation and human ratification
are kept separate. This module writes ``manifest.json`` — misconceptions,
item counts, representations, and validation results — and always sets
``human_ratified: false``. Only a human editing ``RATIFICATION.md`` (see
``content/math/fractions/v1/RATIFICATION.md``) advances that state; no code
path in this package may flip it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .loader import ContentPack
from .validators import ValidationReport

MANIFEST_SCHEMA_VERSION = "1.0"


def build_manifest(
    pack: ContentPack, report: ValidationReport, *, content_version: str = "v1"
) -> dict[str, Any]:
    """Assemble the manifest dict. Pure function — no filesystem, no clock
    dependency beyond the caller-supplied moment, so it is trivially testable."""
    misconceptions = [
        {
            "code": m.code,
            "title": m.title,
            "skill_code": m.skill_code,
            "prevalence_prior": m.prevalence_prior,
            "citation": m.citation,
            "sprout_script_count": sum(
                1 for s in pack.sprout_scripts if s.misconception_code == m.code
            ),
            "intervention_count": sum(
                1 for i in pack.interventions if i.misconception_code == m.code
            ),
            "diagnostic_item_count": sum(
                1
                for i in pack.diagnostic_items
                if i.skill_code == m.skill_code and m.skill_code is not None
            ),
            "has_worked_example": m.code in pack.worked_examples,
        }
        for m in pack.misconceptions
    ]

    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "content_version": content_version,
        "domain": "math",
        "unit": "fractions",
        "generated_at": datetime.now(UTC).isoformat(),
        "human_ratified": False,
        "human_ratification_note": (
            "Machine validation only. See content/math/fractions/v1/RATIFICATION.md "
            "for the required human sign-off before this content is used with a real "
            "learner (roadmap P3 'Human ratification')."
        ),
        "counts": {
            "misconceptions": report.misconception_count,
            "sprout_scripts": report.sprout_script_count,
            "interventions": report.intervention_count,
            "diagnostic_items": report.diagnostic_item_count,
            "practice_items": report.practice_item_count,
            "transfer_items": report.transfer_item_count,
            "worked_examples": report.worked_example_count,
        },
        "representations": report.representation_counts,
        "misconceptions_detail": misconceptions,
        "validation": {
            "ok": report.ok,
            "reading_level_status": report.reading_level_status,
            "reading_level_owner": "P2 educational_validator (packages/learning-engine); "
            "see tools/authoring/src/protege/authoring/p2_adapter.py",
            "errors_by_rule": report.errors_by_rule,
            "error_count": len(report.errors),
        },
    }


def write_manifest(manifest: dict[str, Any], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return out_path
