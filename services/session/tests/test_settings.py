"""Tests for application settings."""

import pytest

from protege.session_service.settings import Settings

P0_ENV_SLOTS = (
    "nvidia_api_key",
    "deepgram_api_key",
    "cartesia_api_key",
    "anthropic_api_key",
    "database_url",
    "aws_region",
    "s3_bucket",
)


def test_defaults_do_not_require_env_file() -> None:
    settings = Settings(_env_file=None)

    assert settings.log_level == "INFO"
    assert settings.otel_console_export is True
    assert settings.database_url.startswith("postgresql+asyncpg://")
    for field in P0_ENV_SLOTS:
        assert field in Settings.model_fields, f"missing P0 env slot: {field}"


def test_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://u:p@db:5432/protege_test")
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")

    settings = Settings(_env_file=None)

    assert settings.database_url == "postgresql+asyncpg://u:p@db:5432/protege_test"
    assert settings.nvidia_api_key == "nvapi-test-key"
