"""Test-only Clerk JWT minting.

No real Clerk tenant is reachable in CI/local tests, so these tests exercise
the *real* Clerk SDK verification path (``clerk_backend_api``) in its
documented networkless mode: a throwaway RSA keypair stands in for a Clerk
instance's signing key, the public half is configured as
``Settings.clerk_jwt_key`` (exactly the "Clerk dashboard -> API Keys -> Show
JWT public key" value in production), and tokens are minted here with the
private half using the same claim shape a real Clerk session token carries
(``sub``, ``exp``, ``nbf``, ``iat``, plus the custom ``role``/``learner_id``/
``email`` session-token claims this service reads -- see ``auth.py``). This proves the
verification *logic* end-to-end without touching a network or a real account.
"""

from __future__ import annotations

import time
import uuid

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)

TEST_JWT_PUBLIC_KEY_PEM = (
    _PRIVATE_KEY.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode()
)

_PRIVATE_KEY_PEM = _PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()

# A second, unrelated keypair -- used to prove a token signed by the wrong
# key is rejected (never accepted just because it *looks* like a JWT).
_OTHER_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_OTHER_PRIVATE_KEY_PEM = _OTHER_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()


def mint_token(
    *,
    sub: str | None = None,
    role: str | None = None,
    learner_id: str | None = None,
    email: str | None = None,
    azp: str | None = None,
    expires_in_s: float = 3600.0,
    not_before_offset_s: float = 0.0,
    signing_key_pem: str = _PRIVATE_KEY_PEM,
) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "sub": sub or f"user_{uuid.uuid4().hex[:20]}",
        "iat": now,
        "nbf": now + int(not_before_offset_s),
        "exp": now + int(expires_in_s),
        "iss": "https://test.clerk.accounts.dev",
        "sid": f"sess_{uuid.uuid4().hex[:20]}",
    }
    if role is not None:
        claims["role"] = role
    if learner_id is not None:
        claims["learner_id"] = learner_id
    if email is not None:
        claims["email"] = email
    if azp is not None:
        claims["azp"] = azp
    return jwt.encode(claims, signing_key_pem, algorithm="RS256")


def mint_token_signed_by_wrong_key(**kwargs: object) -> str:
    return mint_token(signing_key_pem=_OTHER_PRIVATE_KEY_PEM, **kwargs)  # type: ignore[arg-type]
