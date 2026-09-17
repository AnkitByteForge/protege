"""Every content file loads and schema-validates (roadmap P3 "Tests")."""

from __future__ import annotations

import pytest

from protege.authoring.errors import ContentLoadError
from protege.authoring.loader import default_content_root, load_content_pack


@pytest.fixture(scope="module")
def pack():
    return load_content_pack()


def test_content_root_exists() -> None:
    assert default_content_root().is_dir()


def test_all_files_load(pack) -> None:
    assert len(pack.skills) == 8
    assert len(pack.misconceptions) == 8
    assert len(pack.sprout_scripts) == 48
    assert len(pack.interventions) == 24
    assert len(pack.diagnostic_items) == 32
    assert len(pack.practice_items) == 40
    assert len(pack.transfer_items) == 24
    assert len(pack.worked_examples) == 8


def test_missing_root_raises(tmp_path) -> None:
    with pytest.raises(ContentLoadError):
        load_content_pack(tmp_path / "does_not_exist")


def test_malformed_json_raises(tmp_path) -> None:
    root = tmp_path / "content"
    root.mkdir()
    (root / "skills.json").write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ContentLoadError):
        load_content_pack(root)
