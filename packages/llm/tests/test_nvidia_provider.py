"""Unit tests for `NvidiaProvider` — error classification and request
construction, with the `openai` client's network call monkeypatched.

No test here makes a real network call. `test_nvidia_smoke.py` is the one
deliberate, manually-run exception (docs/DECISIONS.md D9).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import httpx2
import openai
import pytest

from protege.llm.base import Message
from protege.llm.errors import (
    ProviderConfigError,
    ProviderFailed,
    ProviderRateLimited,
    ProviderTimeout,
)
from protege.llm.providers.nvidia import NVIDIA_BASE_URL, NvidiaProvider


def _fake_request() -> httpx2.Request:
    return httpx2.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions")


def _make_provider() -> NvidiaProvider:
    return NvidiaProvider(api_key="nvapi-test-key-not-real")


def test_missing_api_key_raises_provider_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    with pytest.raises(ProviderConfigError):
        NvidiaProvider()


def test_explicit_api_key_bypasses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    provider = NvidiaProvider(api_key="nvapi-explicit")
    assert provider.base_url == NVIDIA_BASE_URL


def test_never_logs_or_exposes_the_api_key(capsys: pytest.CaptureFixture[str]) -> None:
    provider = _make_provider()
    print(provider)
    print(vars(provider))
    captured = capsys.readouterr()
    assert "nvapi-test-key-not-real" not in captured.out


def test_rate_limit_error_is_classified_as_provider_rate_limited(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _make_provider()
    request = _fake_request()
    response = httpx2.Response(429, request=request)

    def raise_rate_limited(**_kwargs: Any) -> None:
        raise openai.RateLimitError("rate limited", response=response, body=None)

    monkeypatch.setattr(provider._client.chat.completions, "create", raise_rate_limited)
    with pytest.raises(ProviderRateLimited) as exc_info:
        provider.complete(
            [Message("user", "hi")], model_id="m1", max_tokens=8, temperature=0.0, timeout_s=1.0
        )
    assert exc_info.value.provider == "nvidia"
    assert exc_info.value.model_id == "m1"


def test_timeout_error_is_classified_as_provider_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider()
    request = _fake_request()

    def raise_timeout(**_kwargs: Any) -> None:
        raise openai.APITimeoutError(request)

    monkeypatch.setattr(provider._client.chat.completions, "create", raise_timeout)
    with pytest.raises(ProviderTimeout):
        provider.complete(
            [Message("user", "hi")], model_id="m1", max_tokens=8, temperature=0.0, timeout_s=1.0
        )


def test_5xx_status_error_is_classified_as_provider_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider()
    request = _fake_request()
    response = httpx2.Response(503, request=request)

    def raise_server_error(**_kwargs: Any) -> None:
        raise openai.APIStatusError("server error", response=response, body=None)

    monkeypatch.setattr(provider._client.chat.completions, "create", raise_server_error)
    with pytest.raises(ProviderFailed) as exc_info:
        provider.complete(
            [Message("user", "hi")], model_id="m1", max_tokens=8, temperature=0.0, timeout_s=1.0
        )
    assert exc_info.value.status_code == 503


def test_successful_response_is_normalized_into_llm_result(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider()

    fake_response = SimpleNamespace(
        id="chatcmpl-abc",
        choices=[
            SimpleNamespace(message=SimpleNamespace(content="hello there"), finish_reason="stop")
        ],
        usage=SimpleNamespace(prompt_tokens=5, completion_tokens=7),
    )

    def fake_create(**_kwargs: Any) -> Any:
        return fake_response

    monkeypatch.setattr(provider._client.chat.completions, "create", fake_create)
    result = provider.complete(
        [Message("system", "sys"), Message("user", "hi")],
        model_id="m1",
        max_tokens=8,
        temperature=0.5,
        timeout_s=1.0,
        json_schema={"title": "SproutTurn"},
    )
    assert result.text == "hello there"
    assert result.provider == "nvidia"
    assert result.model_id == "m1"
    assert result.tokens_in == 5
    assert result.tokens_out == 7
    assert result.finish_reason == "stop"
    assert result.raw_id == "chatcmpl-abc"
    assert result.latency_ms >= 0


def test_missing_usage_defaults_token_counts_to_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider()
    fake_response = SimpleNamespace(
        id="chatcmpl-abc",
        choices=[SimpleNamespace(message=SimpleNamespace(content="hi"), finish_reason="stop")],
        usage=None,
    )
    monkeypatch.setattr(
        provider._client.chat.completions, "create", lambda **_kwargs: fake_response
    )
    result = provider.complete(
        [Message("user", "hi")], model_id="m1", max_tokens=8, temperature=0.0, timeout_s=1.0
    )
    assert result.tokens_in == 0
    assert result.tokens_out == 0


def test_json_schema_is_only_passed_through_when_given(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _make_provider()
    captured: dict[str, Any] = {}

    fake_response = SimpleNamespace(
        id="id",
        choices=[SimpleNamespace(message=SimpleNamespace(content="{}"), finish_reason="stop")],
        usage=None,
    )

    def fake_create(**kwargs: Any) -> Any:
        captured.update(kwargs)
        return fake_response

    monkeypatch.setattr(provider._client.chat.completions, "create", fake_create)
    provider.complete(
        [Message("user", "hi")], model_id="m1", max_tokens=8, temperature=0.0, timeout_s=1.0
    )
    assert "response_format" not in captured

    provider.complete(
        [Message("user", "hi")],
        model_id="m1",
        max_tokens=8,
        temperature=0.0,
        timeout_s=1.0,
        json_schema={"title": "X"},
    )
    assert captured["response_format"]["type"] == "json_schema"
    assert captured["response_format"]["json_schema"]["schema"] == {"title": "X"}
