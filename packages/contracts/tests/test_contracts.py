"""Smoke test: the contracts package imports cleanly in the workspace venv."""

import protege.contracts as contracts


def test_package_imports() -> None:
    assert contracts.__version__
