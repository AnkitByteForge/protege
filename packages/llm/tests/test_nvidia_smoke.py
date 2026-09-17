"""Manual, real-network smoke test for `NvidiaProvider` (docs/DECISIONS.md D9).

This test makes a REAL call to NVIDIA's hosted endpoint and spends real
NVIDIA credits against the 40 RPM / finite-credit budget (addendum §2.3).
It is EXCLUDED from the default test run and from CI — `.github/workflows/ci.yml`
runs plain `uv run pytest`, which never sets the flag this test requires.

Run it manually, deliberately, one call at a time::

    NVIDIA_API_KEY=nvapi-... PROTEGE_RUN_NVIDIA_SMOKE=1 \
        uv run pytest packages/llm/tests/test_nvidia_smoke.py -v -s

It never prints the API key or any Authorization header — only the response
shape and latency the router depends on.
"""

from __future__ import annotations

import os

import pytest

from protege.contracts import PedagogicalRole, SproutTurn
from protege.llm.base import Message
from protege.llm.providers.nvidia import NvidiaProvider
from protege.llm.rate_limit import TokenBucket
from protege.llm.router import ModelRouter

_FLAG = "PROTEGE_RUN_NVIDIA_SMOKE"

pytestmark = pytest.mark.skipif(
    os.environ.get(_FLAG) != "1",
    reason=(
        f"real-network NVIDIA smoke test — set {_FLAG}=1 and NVIDIA_API_KEY "
        "to run it deliberately; never runs in CI (docs/DECISIONS.md D9)"
    ),
)

_DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"
"""Live-verified default (2026-09-17 smoke run). `meta/llama-3.3-70b-instruct`
and `meta/llama-3.1-8b-instruct` both returned HTTP 410 Gone — permanently
retired — and must never be used as a default here again."""


def test_nvidia_round_trip_returns_text() -> None:
    """A minimal real call to the NVIDIA endpoint.

    Deliberately does not assert on model wording — only on the shape the
    router depends on: some text came back, tagged with a real
    provider/model_id and a non-negative latency.
    """
    provider = NvidiaProvider()  # raises ProviderConfigError if NVIDIA_API_KEY unset
    model_id = os.environ.get("PROTEGE_NVIDIA_SMOKE_MODEL", _DEFAULT_MODEL)
    result = provider.complete(
        [Message("user", "Reply with exactly one word: hello")],
        model_id=model_id,
        max_tokens=8,
        temperature=0.0,
        timeout_s=10.0,
    )
    assert result.text.strip() != ""
    assert result.provider == "nvidia"
    assert result.model_id == model_id
    assert result.latency_ms >= 0


def test_nvidia_structured_output_round_trip() -> None:
    """Exercises the FULL structured-output path the router actually
    depends on (tier 1/2 + parse + validate against a real P1 contract
    model) against a real NVIDIA model — not just a plain-text completion.

    Run against a specific candidate with::

        PROTEGE_NVIDIA_SMOKE_MODEL=nvidia/<model-id> \\
            NVIDIA_API_KEY=nvapi-... PROTEGE_RUN_NVIDIA_SMOKE=1 \\
            uv run pytest packages/llm/tests/test_nvidia_smoke.py -k structured -v -s
    """
    model_id = os.environ.get("PROTEGE_NVIDIA_SMOKE_MODEL", _DEFAULT_MODEL)
    router = ModelRouter(
        {"nvidia": NvidiaProvider()},
        role_policy={PedagogicalRole.SPROUT: (f"nvidia:{model_id}", "authored_fallback")},
        rate_limiter=TokenBucket(rate_per_minute=35.0),
        timeout_s=10.0,
    )
    outcome = router.call_structured(
        PedagogicalRole.SPROUT,
        [
            Message(
                "system",
                "You are testing a JSON API. Respond only with JSON matching the schema.",
            ),
            Message(
                "user",
                'Produce a SproutTurn where exhibits="M003", emotion is one of '
                "confused/thinking/dawning/delighted, confidence_shown is one of "
                "high/medium/low, and utterance is at most 30 words about fractions.",
            ),
        ],
        model_cls=SproutTurn,
    )
    assert not outcome.used_deterministic_fallback, (
        f"model {model_id} could not produce schema-valid output "
        f"(structured_mode={outcome.structured_mode})"
    )
    assert isinstance(outcome.value, SproutTurn)
    assert outcome.model_id == model_id
