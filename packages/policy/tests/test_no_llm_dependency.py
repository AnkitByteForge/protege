"""Roadmap P11: "P11 must contain ZERO LLM calls. Do not import or call:
ModelRouter, NvidiaProvider, AnthropicProvider, Sprout, Diagnostician."

Checked two ways: the package has no dependency on ``protege-llm`` or
``protege-roles`` at all (``pyproject.toml``), and -- belt and braces,
matching ``packages/learning-engine/tests/test_threshold_service.py``'s own
"module is pure" convention -- no source file mentions any forbidden name.
"""

from __future__ import annotations

from pathlib import Path

_FORBIDDEN_IMPORT_LINES = (
    "import protege.llm",
    "from protege.llm",
    "import protege.roles.sprout",
    "from protege.roles.sprout",
    "import protege.roles.diagnostician",
    "from protege.roles.diagnostician",
    "ModelRouter(",
    "NvidiaProvider(",
    "AnthropicProvider(",
    "import openai",
)
"""Actual import/usage shapes, not bare substrings -- so a module
docstring that *describes* the forbidden names (as this package's own
``__init__.py`` does, quoting the roadmap) is not itself a false
positive."""

_PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src" / "protege" / "policy"


def test_no_source_file_references_llm_infrastructure() -> None:
    python_files = list(_PACKAGE_SRC.rglob("*.py"))
    assert python_files, "expected protege.policy source files to exist"
    for path in python_files:
        contents = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_IMPORT_LINES:
            assert forbidden not in contents, f"{path} references forbidden LLM usage {forbidden!r}"


def test_package_pyproject_has_no_llm_or_roles_dependency() -> None:
    pyproject = (_PACKAGE_SRC.parents[2] / "pyproject.toml").read_text(encoding="utf-8")
    assert "protege-llm" not in pyproject
    assert "protege-roles" not in pyproject
