"""Deterministic OpenAPI export for the P10 session API.

Sibling to ``protege.contracts.export`` (roadmap P1's JSON-Schema pipeline):
that module exports content-authoring domain contracts for
``apps/web``'s existing ``json-schema-to-typescript`` step; this module
exports the FastAPI app's *endpoint* contract (paths, request/response
shapes, discriminated unions) for a new, equally deterministic
``openapi-typescript`` step (see ``apps/web/package.json``'s
``generate:api-types`` script) -- the two pipelines stay separate rather
than merging into one, because ``content/schema/*.json`` is the domain
vocabulary (consumed by content authoring/P3 too, not just the frontend),
while this file is wire-transport-only.

Usage: ``python -m protege.session_service.openapi_export <output-file>``
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .app import create_app
from .settings import Settings


def export_openapi(out_file: Path) -> Path:
    """Write the app's OpenAPI schema, byte-deterministic (sorted keys, no
    timestamps) so the CI drift check this mirrors
    (``apps/web``'s existing pattern) can compare bytes."""
    # `_env_file` is pydantic-settings' dynamic per-instance override kwarg
    # (not part of the generated `__init__` signature mypy sees).
    app = create_app(Settings(_env_file=None, otel_console_export=False))  # type: ignore[call-arg]
    schema = app.openapi()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_file", type=Path, help="Path for the openapi.json file.")
    args = parser.parse_args(argv)
    path = export_openapi(args.out_file)
    print(path.as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
