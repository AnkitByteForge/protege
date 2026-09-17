from __future__ import annotations

import json
from collections.abc import Sequence

import pytest

from protege.authoring.loader import ContentPack, load_content_pack
from protege.contracts import Misconception
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.rate_limit import TokenBucket
from protege.llm.router import ModelRouter


@pytest.fixture(scope="session")
def content_pack() -> ContentPack:
    """Load the authored P3 fractions content pack once per test session."""
    return load_content_pack()


@pytest.fixture(scope="session")
def misconception_set(content_pack: ContentPack) -> Sequence[Misconception]:
    return content_pack.misconceptions


@pytest.fixture
def m003(misconception_set: Sequence[Misconception]) -> Misconception:
    return next(m for m in misconception_set if m.code == "M003")


def make_router(provider: FakeProvider, **kwargs: object) -> ModelRouter:
    """Build a ModelRouter wired to a FakeProvider without test throttling."""
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