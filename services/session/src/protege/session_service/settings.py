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

    # --- Object storage (StorageAdapter; roadmap P9) ---
    aws_region: str = "us-east-1"
    s3_bucket: str = ""
    storage_backend: str = "local"
    storage_local_root: str = "./local_storage"

    # --- Embeddings (docs/DECISIONS.md D2: local bge-small, 384-d,
    # configuration-driven -- never hardcoded in application code or the
    # migration that creates the pgvector column). ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = 384

    # --- Jobs worker (roadmap P9) ---
    job_worker_id: str = "worker-local"
    job_poll_interval_s: float = 1.0
    job_max_attempts: int = 5
    # A claimed ("running") job whose claim is older than this is treated as
    # abandoned (the worker that claimed it crashed or was killed) and
    # becomes reclaimable again -- addendum §6: "if the worker dies mid-job,
    # it must be retried." Generous relative to any single model call
    # (addendum §2.3's 2.5 s LLM timeout) so a merely slow, still-alive
    # worker is never falsely reclaimed out from under itself.
    job_stale_claim_timeout_s: float = 300.0

    # --- Service ---
    log_level: str = "INFO"
    otel_console_export: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
