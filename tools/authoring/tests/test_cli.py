"""The ``protege-authoring`` CLI (validate / manifest subcommands)."""

from __future__ import annotations

import json

from protege.authoring.cli import main


def test_validate_command_exits_zero_on_the_real_content_pack(capsys) -> None:
    exit_code = main(["validate"])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "VALIDATION: PASS" in out


def test_manifest_command_writes_a_manifest_with_human_ratified_false(tmp_path) -> None:
    out_path = tmp_path / "manifest.json"
    exit_code = main(["manifest", "--out", str(out_path)])
    assert exit_code == 0
    manifest = json.loads(out_path.read_text(encoding="utf-8"))
    assert manifest["human_ratified"] is False
    assert manifest["validation"]["ok"] is True


def test_validate_command_fails_on_a_broken_root(tmp_path, capsys) -> None:
    exit_code = main(["--root", str(tmp_path / "missing"), "validate"])
    err = capsys.readouterr().err
    assert exit_code == 1
    assert "LOAD FAILED" in err
