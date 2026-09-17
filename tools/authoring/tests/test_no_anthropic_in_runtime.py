"""The Anthropic SDK belongs ONLY in offline authoring (addendum §1.3, §9.4-9.5).

This guards the architectural boundary this package sits on: no runtime
package may import ``anthropic``. It is a static source scan, not an import
check, so it catches the dependency even before anyone tries to install it
into a runtime package's environment.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

RUNTIME_SOURCE_DIRS = [
    "services/session/src",
    "packages/contracts/src",
    "packages/learning-engine/src",
    "packages/llm/src",
]

_ANTHROPIC_IMPORT = re.compile(r"^\s*(import\s+anthropic\b|from\s+anthropic\b)", re.MULTILINE)


def test_no_runtime_package_imports_anthropic() -> None:
    offenders: list[str] = []
    for rel_dir in RUNTIME_SOURCE_DIRS:
        directory = REPO_ROOT / rel_dir
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if _ANTHROPIC_IMPORT.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"anthropic SDK imported in runtime package(s): {offenders}"


def test_authoring_package_itself_does_not_import_anthropic_yet() -> None:
    """P3 does not use the offline Fable/anthropic drafting workflow at all —
    every record in content/math/fractions/v1 was hand-authored (see
    seed_fractions_v1.py's module docstring). This pins that fact so a future
    change that adds live model calls to this package is a deliberate,
    reviewed decision, not an accident."""
    directory = REPO_ROOT / "tools" / "authoring" / "src"
    for path in directory.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not _ANTHROPIC_IMPORT.search(text), path
