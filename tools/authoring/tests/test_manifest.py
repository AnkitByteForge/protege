"""The manifest never marks content as human-ratified (roadmap P3 "Human ratification")."""

from __future__ import annotations

import json

import pytest

from protege.authoring.loader import load_content_pack
from protege.authoring.manifest import build_manifest, write_manifest
from protege.authoring.validators import validate_content_pack


@pytest.fixture(scope="module")
def pack():
    return load_content_pack()


@pytest.fixture(scope="module")
def report(pack):
    return validate_content_pack(pack)


def test_manifest_reports_human_ratified_false(pack, report) -> None:
    manifest = build_manifest(pack, report)
    assert manifest["human_ratified"] is False


def test_manifest_reports_ok_validation_and_counts(pack, report) -> None:
    manifest = build_manifest(pack, report)
    assert manifest["validation"]["ok"] is True
    assert manifest["counts"]["misconceptions"] == 8
    assert manifest["counts"]["practice_items"] == 40
    assert manifest["counts"]["worked_examples"] == 8
    assert set(manifest["representations"]) == {
        "area_model",
        "number_line",
        "set_model",
        "symbolic",
    }


def test_manifest_never_sets_human_ratified_true_even_when_validation_fails(pack) -> None:
    from protege.authoring.errors import ContentValidationError
    from protege.authoring.validators import ValidationReport

    failing_report = ValidationReport(
        errors=[ContentValidationError("fake_rule", "synthetic failure for this test")],
        misconception_count=0,
        sprout_script_count=0,
        intervention_count=0,
        diagnostic_item_count=0,
        practice_item_count=0,
        transfer_item_count=0,
        worked_example_count=0,
    )
    manifest = build_manifest(pack, failing_report)
    assert manifest["human_ratified"] is False
    assert manifest["validation"]["ok"] is False


def test_write_manifest_round_trips_to_disk(pack, report, tmp_path) -> None:
    manifest = build_manifest(pack, report)
    path = write_manifest(manifest, tmp_path / "manifest.json")
    reloaded = json.loads(path.read_text(encoding="utf-8"))
    assert reloaded == manifest
