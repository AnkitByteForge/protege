"""Shared pytest fixtures for the contracts test suite."""

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
WORKED_EXAMPLE_JSON = FIXTURES / "worked_example_m003.json"


@pytest.fixture
def worked_example_json() -> str:
    return WORKED_EXAMPLE_JSON.read_text(encoding="utf-8")
