"""CLI entry point for the P3 content pipeline: ``protege-authoring``.

Two subcommands, both deterministic and network-free:

- ``validate``  — load the content pack, run every rule in ``validators.py``,
  print a pass/fail summary, and exit non-zero on any failure (the CI gate).
- ``manifest``  — load, validate, and write ``manifest.json`` next to the
  content pack. Always writes ``human_ratified: false``; see
  ``manifest.py`` and ``content/math/fractions/v1/RATIFICATION.md``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .errors import ContentError
from .loader import default_content_root, load_content_pack
from .manifest import build_manifest, write_manifest
from .validators import validate_content_pack


def _cmd_validate(root: Path) -> int:
    try:
        pack = load_content_pack(root)
    except ContentError as exc:
        print(f"LOAD FAILED: {exc}", file=sys.stderr)
        return 1

    report = validate_content_pack(pack)
    print(f"Content pack: {pack.root}")
    print(f"  misconceptions:   {report.misconception_count}")
    print(f"  sprout_scripts:   {report.sprout_script_count}")
    print(f"  interventions:    {report.intervention_count}")
    print(f"  diagnostic_items: {report.diagnostic_item_count}")
    print(f"  practice_items:   {report.practice_item_count}")
    print(f"  transfer_items:   {report.transfer_item_count}")
    print(f"  worked_examples:  {report.worked_example_count}")
    print(f"  representations:  {report.representation_counts}")
    print(f"  reading_level:    {report.reading_level_status}")

    if report.ok:
        print("VALIDATION: PASS")
        return 0

    print(f"VALIDATION: FAIL ({len(report.errors)} error(s))", file=sys.stderr)
    for rule, messages in report.errors_by_rule.items():
        print(f"  [{rule}]", file=sys.stderr)
        for message in messages:
            print(f"    - {message}", file=sys.stderr)
    return 1


def _cmd_manifest(root: Path, out: Path) -> int:
    try:
        pack = load_content_pack(root)
    except ContentError as exc:
        print(f"LOAD FAILED: {exc}", file=sys.stderr)
        return 1

    report = validate_content_pack(pack)
    manifest = build_manifest(pack, report)
    path = write_manifest(manifest, out)
    print(f"Wrote {path} (validation ok={report.ok}, human_ratified=false)")
    return 0 if report.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="protege-authoring", description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Content package root (default: content/math/fractions/v1).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="Run every deterministic P3 content rule.")
    manifest_parser = sub.add_parser("manifest", help="Write manifest.json for the content pack.")
    manifest_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Manifest output path (default: <root>/manifest.json).",
    )

    args = parser.parse_args(argv)
    root = args.root or default_content_root()

    if args.command == "validate":
        return _cmd_validate(root)
    if args.command == "manifest":
        out = args.out or (root / "manifest.json")
        return _cmd_manifest(root, out)
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
