"""Shared fixtures for the session service tests."""

import pytest
from fastapi.testclient import TestClient

from protege.session_service.app import create_app
from protege.session_service.settings import Settings


@pytest.fixture()
def client() -> TestClient:
    settings = Settings(_env_file=None, log_level="WARNING", otel_console_export=False)
    return TestClient(create_app(settings))
