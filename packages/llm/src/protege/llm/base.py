"""Provider-neutral core types (addendum §1.6).

``Message`` and ``LLMResult`` are the only shapes every provider adapter
speaks; ``LLMProvider`` is the protocol every adapter implements. Nothing
above this module knows a model name exists — only the ``ModelRouter`` and
the concrete provider modules do (addendum §1.5).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


@dataclass(frozen=True)
class Message:
    """One chat turn sent to a provider.

    ``role`` is the wire-level chat role, not a ``PedagogicalRole`` — a
    single Sprout turn may carry a ``system`` message, a ``user`` message
    (the child's delimited utterance block, never concatenated in raw per
    ARCHITECTURE.md §16), and prior ``assistant`` turns.
    """

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class LLMResult:
    """One provider response, normalized across every adapter (addendum §1.6)."""

    text: str
    provider: str
    model_id: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    finish_reason: str
    raw_id: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    """Every provider adapter's shape (addendum §1.6).

    ``FakeProvider`` and ``NvidiaProvider`` both satisfy this structurally,
    without inheriting from anything.
    """

    name: str

    def complete(
        self,
        messages: Sequence[Message],
        *,
        model_id: str,
        max_tokens: int,
        temperature: float,
        timeout_s: float,
        json_schema: dict[str, object] | None = None,
    ) -> LLMResult: ...
