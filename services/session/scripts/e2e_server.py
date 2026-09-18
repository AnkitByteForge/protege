"""Dev/test-only server for P15 Playwright E2E runs.

No real Clerk tenant is available in this environment. This script reuses
the exact same test-JWT pattern `services/session/tests/_auth_helpers.py`
already uses for the backend's own P10 contract tests: a throwaway RSA
keypair stands in for a Clerk instance's signing key, the public half is
handed to `Settings.clerk_jwt_key` (networkless RS256 verification -- the
*real* `clerk_backend_api` verification path, never a hand-rolled bypass),
and a token is minted with the private half using the same claim shape a
real Clerk session token carries.

On startup this seeds one parent (linked to the minted token's `sub`) and
one learner, then writes `{token, learnerId, apiBaseUrl}` to
`apps/web/.e2e/auth.json` for Playwright's `globalSetup` to pick up. Never
used outside local E2E runs -- production always uses real Clerk.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path

import jwt
import uvicorn
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from protege.session_service.app import create_app
from protege.session_service.db.engine import session_scope
from protege.session_service.repositories.learners import LearnerRepository
from protege.session_service.settings import Settings

_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUTH_FILE = _REPO_ROOT / "apps" / "web" / ".e2e" / "auth.json"
_HOST = "127.0.0.1"
_PORT = 8301


def _mint_keypair() -> tuple[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return public_pem, private_pem


def _mint_token(*, sub: str, private_pem: str) -> str:
    now = int(time.time())
    claims = {
        "sub": sub,
        "iat": now,
        "nbf": now,
        "exp": now + 6 * 3600,
        "iss": "https://e2e.test.clerk.accounts.dev",
        "sid": f"sess_{uuid.uuid4().hex[:20]}",
        "role": "parent",
    }
    return jwt.encode(claims, private_pem, algorithm="RS256")


async def _seed(*, clerk_user_id: str) -> uuid.UUID:
    async with session_scope() as session:
        repo = LearnerRepository(session)
        parent = await repo.create_parent(email=f"{clerk_user_id}@e2e.test", consent_version="v1")
        await repo.link_clerk_user_id(parent_id=parent.id, clerk_user_id=clerk_user_id)
        learner = await repo.create_learner(
            parent_id=parent.id, display_name="Riley", grade_band="3-4"
        )
        return learner.id


async def _async_main() -> None:
    # Seeding and serving must share one event loop: asyncpg connections
    # (via `db/engine.py`'s module-level, loop-bound engine cache) cannot
    # cross from one closed loop to another -- exactly the Windows
    # ProactorEventLoop failure `tests/_p10_helpers.py` already documents
    # for the same reason. A prior version of this script called
    # `asyncio.run(_seed(...))` before `uvicorn.run(...)`, which creates and
    # tears down its own loop first; fixed by doing both under one
    # `asyncio.run` instead.
    public_pem, private_pem = _mint_keypair()
    clerk_user_id = f"user_e2e_{uuid.uuid4().hex[:16]}"
    token = _mint_token(sub=clerk_user_id, private_pem=private_pem)

    settings = Settings(
        clerk_secret_key="sk_test_e2e_unused",
        clerk_jwt_key=public_pem,
        clerk_authorized_parties="",
        log_level="WARNING",
        otel_console_export=False,
    )

    learner_id = await _seed(clerk_user_id=clerk_user_id)

    _AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    _AUTH_FILE.write_text(
        json.dumps(
            {
                "token": token,
                "learnerId": str(learner_id),
                "apiBaseUrl": f"http://{_HOST}:{_PORT}",
            }
        )
    )

    app = create_app(settings)
    config = uvicorn.Config(app, host=_HOST, port=_PORT, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
