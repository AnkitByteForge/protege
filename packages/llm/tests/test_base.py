"""Tests for the provider-neutral core types (`base.py`)."""

import dataclasses

import pytest

from protege.llm.base import LLMProvider, LLMResult, Message
from protege.llm.providers.fake import FakeProvider
from protege.llm.providers.nvidia import NvidiaProvider


def test_message_is_frozen() -> None:
    message = Message("user", "hi")
    with pytest.raises(dataclasses.FrozenInstanceError):
        message.content = "changed"  # type: ignore[misc]


def test_llm_result_carries_every_documented_field() -> None:
    result = LLMResult(
        text="hi",
        provider="fake",
        model_id="m1",
        tokens_in=1,
        tokens_out=2,
        latency_ms=3,
        finish_reason="stop",
        raw_id="r1",
    )
    assert (result.text, result.provider, result.model_id) == ("hi", "fake", "m1")
    assert (result.tokens_in, result.tokens_out, result.latency_ms) == (1, 2, 3)
    assert result.finish_reason == "stop"
    assert result.raw_id == "r1"


def test_llm_result_raw_id_defaults_to_none() -> None:
    result = LLMResult(
        text="hi",
        provider="fake",
        model_id="m1",
        tokens_in=1,
        tokens_out=1,
        latency_ms=1,
        finish_reason="stop",
    )
    assert result.raw_id is None


def test_fake_provider_satisfies_llm_provider_protocol() -> None:
    assert isinstance(FakeProvider(), LLMProvider)


def test_nvidia_provider_class_declares_the_protocol_shape() -> None:
    # NvidiaProvider requires an API key to construct; check the class shape
    # directly rather than instantiating it, so this test never touches env.
    assert hasattr(NvidiaProvider, "complete")
    assert NvidiaProvider.name == "nvidia"
