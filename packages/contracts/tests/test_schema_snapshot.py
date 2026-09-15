"""Schema-snapshot test: ``content/schema/*.json`` must match the schemas
generated from the contracts, byte for byte. Any contract change must be
regenerated via ``make types`` and land in the same PR — this is what makes
contract drift impossible to merge silently (roadmap P1)."""

import json
from pathlib import Path

import pytest

from protege.contracts.export import EXPORT_ORDER, export_schemas

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_DIR = REPO_ROOT / "content" / "schema"


def test_schema_dir_is_committed() -> None:
    index = SCHEMA_DIR / "index.json"
    assert index.is_file(), (
        "content/schema/ is missing. Run `make types` (or "
        "`python -m protege.contracts.export content/schema`) and commit the output."
    )


def test_index_lists_every_model() -> None:
    index = json.loads((SCHEMA_DIR / "index.json").read_text(encoding="utf-8"))
    assert index["models"] == [model.__name__ for model in EXPORT_ORDER]


@pytest.mark.parametrize("model", EXPORT_ORDER, ids=lambda m: m.__name__)
def test_schema_snapshot_matches(model: type) -> None:
    committed = SCHEMA_DIR / f"{model.__name__}.json"
    assert committed.is_file(), (
        f"{committed} missing. Run `make types` and commit the regenerated schemas."
    )
    expected = (
        json.dumps(model.model_json_schema(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    )
    assert committed.read_text(encoding="utf-8") == expected, (
        f"{model.__name__} schema drifted from content/schema. "
        "Run `make types` and commit the regenerated files."
    )


def test_export_is_deterministic(tmp_path: Path) -> None:
    first = export_schemas(tmp_path / "a")
    second = export_schemas(tmp_path / "b")
    assert [p.read_bytes() for p in first] == [p.read_bytes() for p in second]
