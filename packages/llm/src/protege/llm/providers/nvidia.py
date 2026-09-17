"""NVIDIA-hosted runtime provider (addendum §1.4, §9 point 3).

Uses the ``openai`` Python SDK pointed at NVIDIA's OpenAI-compatible
endpoint via ``base_url`` — the exact wire contract the ``openai`` client
already speaks, per the addendum. No NVIDIA-specific SDK, no
``langchain-nvidia-ai-endpoints``.

This module is the ONLY place an NVIDIA endpoint or API key touches this
package. It never logs the API key or a raw Authorization header, and never
stores the key anywhere but inside the ``openai`` client itself (which owns
that concern).
"""

from __future__ import annotations

import os
import time
from collections.abc import Sequence

from openai import APIStatusError, APITimeoutError, OpenAI, RateLimitError

from ..base import LLMResult, Message
from ..errors import ProviderConfigError, ProviderFailed, ProviderRateLimited, ProviderTimeout

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
"""Addendum §1.4: NVIDIA's OpenAI-compatible Chat Completions endpoint."""


class NvidiaProvider:
    """The runtime ``LLMProvider`` (addendum §9 point 3).

    Owns no retry policy of its own — ``max_retries=0`` on the client,
    because the ``ModelRouter`` owns the documented retry/fallback budget
    (addendum §1.6: "we own retry policy at the router level").
    """

    name = "nvidia"

    def __init__(self, *, api_key: str | None = None, base_url: str = NVIDIA_BASE_URL) -> None:
        key = api_key if api_key is not None else os.environ.get("NVIDIA_API_KEY", "")
        if not key:
            raise ProviderConfigError(
                self.name, "", "NVIDIA_API_KEY is not set (env var or explicit api_key)"
            )
        self.base_url = base_url
        self._client = OpenAI(base_url=base_url, api_key=key, max_retries=0)

    def complete(
        self,
        messages: Sequence[Message],
        *,
        model_id: str,
        max_tokens: int,
        temperature: float,
        timeout_s: float,
        json_schema: dict[str, object] | None = None,
    ) -> LLMResult:
        kwargs: dict[str, object] = {}
        if json_schema is not None:
            # Support for constrained decoding varies per model on NIM
            # (addendum §2.5) — the router, not this adapter, decides
            # whether to pass a schema at all.
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "out", "schema": json_schema, "strict": True},
            }
        t0 = time.perf_counter()
        try:
            # The SDK's overloads expect its own TypedDict message params and
            # a fixed keyword set; building the payload dynamically (a plain
            # role/content dict per message, plus an optional response_format
            # kwarg) is deliberately loose at this one boundary so the router
            # above never needs to know an SDK-specific type exists.
            response = self._client.chat.completions.create(  # type: ignore[call-overload]
                model=model_id,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout_s,
                **kwargs,
            )
        except RateLimitError as exc:
            raise ProviderRateLimited(self.name, model_id) from exc
        except APITimeoutError as exc:
            raise ProviderTimeout(self.name, model_id) from exc
        except APIStatusError as exc:
            raise ProviderFailed(self.name, model_id, exc.status_code) from exc

        usage = response.usage
        choice = response.choices[0]
        return LLMResult(
            text=choice.message.content or "",
            provider=self.name,
            model_id=model_id,
            tokens_in=getattr(usage, "prompt_tokens", 0) if usage is not None else 0,
            tokens_out=getattr(usage, "completion_tokens", 0) if usage is not None else 0,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            finish_reason=choice.finish_reason or "unknown",
            raw_id=response.id,
        )
