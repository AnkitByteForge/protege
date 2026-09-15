"""Deterministic JSON Schema export for every PROTÉGÉ contract.

Roadmap P1: ``content/schema/*.json`` is published for content authoring (P3
validates against these files in CI) and drives TypeScript generation for the
frontend. Output is byte-deterministic: sorted keys, stable model order, no
timestamps — so the schema-snapshot test and the CI drift check compare
bytes.

Usage: ``python -m protege.contracts.export <output-dir>``
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from .artifacts import ProofClaim, TutorBriefing
from .content import (
    Concept,
    Distractor,
    Intervention,
    ItemVersion,
    LearningItem,
    Misconception,
    Prerequisite,
    Skill,
    SproutScript,
    TransferItem,
)
from .learning_state import (
    Evidence,
    MasteryEstimate,
    MasteryOutcome,
    MisconceptionBelief,
    TeachingEpisode,
)
from .roles import CoachHint, ReportDraft, SproutTurn
from .session import (
    CardExplanation,
    DiagnosisResult,
    DomainEvent,
    ManipulativeExplanation,
    PolicyDecision,
    TextExplanation,
    VoiceExplanation,
)
from .worked_example import WorkedExample

EXPORT_ORDER: list[type[BaseModel]] = [
    # Content domain
    Skill,
    Concept,
    Prerequisite,
    Misconception,
    Distractor,
    LearningItem,
    ItemVersion,
    Intervention,
    SproutScript,
    TransferItem,
    # Learner state
    Evidence,
    MasteryEstimate,
    MisconceptionBelief,
    TeachingEpisode,
    MasteryOutcome,
    # Session layer
    VoiceExplanation,
    TextExplanation,
    ManipulativeExplanation,
    CardExplanation,
    DiagnosisResult,
    PolicyDecision,
    DomainEvent,
    # Role outputs (ModelRouter structured-output schemas)
    SproutTurn,
    CoachHint,
    ReportDraft,
    # Artifacts
    ProofClaim,
    TutorBriefing,
    # Authored pipeline envelope
    WorkedExample,
]

EXPORT_FORMAT_VERSION = "1.0"


def export_schemas(out_dir: Path) -> list[Path]:
    """Write one JSON Schema per model plus ``index.json``; return the paths.

    Deterministic: the same contracts always produce byte-identical files.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model in EXPORT_ORDER:
        schema = model.model_json_schema()
        path = out_dir / f"{model.__name__}.json"
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    index = {
        "schema_version": EXPORT_FORMAT_VERSION,
        "models": [model.__name__ for model in EXPORT_ORDER],
    }
    index_path = out_dir / "index.json"
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    written.append(index_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path, help="Directory for the schema files.")
    args = parser.parse_args(argv)
    for path in export_schemas(args.out_dir):
        print(path.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
