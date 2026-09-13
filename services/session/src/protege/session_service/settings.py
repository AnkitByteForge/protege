"""Application settings.

Single settings source for the session service (roadmap P0: "settings via
Pydantic BaseSettings"). Values come from the environment or the repo-root
`.env`; `.env.example` documents every key. Embedding model/dimension will also
live in configuration when introduced — never hardcoded (docs/DECISIONS.md D2).
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[5]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Runtime AI providers (addendum §7.2). Keys are secrets: env only. ---
    nvidia_api_key: str = ""
    deepgram_api_key: str = ""
    cartesia_api_key: str = ""
    # Offline authoring only — never a runtime dependency (addendum §9.4).
    anthropic_api_key: str = ""

    # --- Data ---
    # Host port 5433 matches docker-compose (5432 is left free for other
    # local projects). `ssl=disable` is required for the local stack: asyncpg
    # 0.30+ defaults to sslmode=prefer and Windows' Docker port proxy resets
    # that SSL negotiation. Production URLs override via env.
    database_url: str = "postgresql+asyncpg://protege:protege@localhost:5433/protege?ssl=disable"

    # --- Object storage slots (StorageAdapter arrives later) ---
    aws_region: str = "us-east-1"
    s3_bucket: str = ""

    # --- Service ---
    log_level: str = "INFO"
    otel_console_export: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
