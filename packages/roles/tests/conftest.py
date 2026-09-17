from __future__ import annotations

import json
from collections.abc import Sequence

import pytest

from protege.authoring.loader import ContentPack, load_content_pack
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.rate_limit import TokenBucket
from protege.llm.router import ModelRouter


@pytest.fixture(scope="session")
def content_pack() -> ContentPack:
    """The real, ratified P3 fractions content pack -- loaded once per test
    session since it is read-only and reasonably expensive to parse."""
    return load_content_pack()


def make_router(provider: FakeProvider, **kwargs: object) -> ModelRouter:
    """A `ModelRouter` wired to a `FakeProvider`, with the rate limiter
    opened up so tests never wait on it (mirrors packages/llm/tests
    convention)."""
    kwargs.setdefault("rate_limiter", TokenBucket(rate_per_minute=6000.0))
    return ModelRouter({"nvidia": provider}, **kwargs)  # type: ignore[arg-type]


def sprout_turn_json(
    *,
    utterance: str,
    exhibits: str,
    emotion: str = "confused",
    confidence_shown: str = "high",
) -> str:
    return json.dumps(
        {
            "utterance": utterance,
            "exhibits": exhibits,
            "emotion": emotion,
            "confidence_shown": confidence_shown,
        }
    )


def scripted_provider(bodies: Sequence[str]) -> FakeProvider:
    return FakeProvider(script=[FakeOutcome.ok(body) for body in bodies])
