"""Deterministic canned-response provider (roadmap P4).

``FakeProvider`` is the testing interface for every downstream phase that
needs an ``LLMProvider`` without a real network call — P5 (Sprout), P6
(Diagnostician), and P7 (FSM integration tests) construct a ``ModelRouter``
with ``{"nvidia": FakeProvider()}`` in place of a real ``NvidiaProvider``.

Two independent knobs:

- A ``script`` of ``FakeOutcome``s, consumed in order, one per ``complete()``
  call — for exercising the router's rate-limit/timeout/5xx/malformed-JSON/
  schema-mismatch fallback paths deterministically.
- Once the script is exhausted (or if none was given), ``complete()``
  returns a stable canned JSON body selected by the requested schema's
  title (``json_schema["title"]``, e.g. ``"SproutTurn"``) — every call for
  the same schema returns byte-identical text, so tests never depend on
  model randomness.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

from ..base import LLMResult, Message
from ..errors import ProviderFailed, ProviderRateLimited, ProviderTimeout

DEFAULT_CANNED_RESPONSES: dict[str, str] = {
    "SproutTurn": (
        '{"utterance": "I think 1/8 is bigger! Eight is way more than four.", '
        '"exhibits": "M003", "emotion": "confused", "confidence_shown": "high"}'
    ),
    "DiagnosisResult": (
        '{"labels": [{"misconception_id": "M003", "state": "unresolved", '
        '"confidence": 0.62, "evidence_span": "eight is more than four"}], '
        '"understanding_signals": [], "asr_reliable": true, "abstained": false}'
    ),
    "CoachHint": (
        '{"intervention_id": "INT_M003_A", '
        '"text": "Let\'s cut the SAME pizza two ways and lay them on top of each other.", '
        '"persona_note": null}'
    ),
    "ReportDraft": (
        '{"audience": "parent", "claim_key": "fraction_comparison_progress", '
        '"sentences": [{"text": "Ava practiced comparing unit fractions today.", '
        '"evidence_ids": ["e_901"]}]}'
    ),
}
"""Byte-stable per-schema canned bodies, keyed by Pydantic's default JSON
Schema ``title`` (the model class name). Values reuse the misconception,
intervention, and evidence ids from the ARCHITECTURE.md §38 worked example
so downstream fixtures can cross-reference the same content."""


@dataclass
class FakeOutcome:
    """One scripted ``complete()`` result: either an exception to raise, or
    a canned success body."""

    raises: Exception | None = None
    text: str | None = None
    tokens_in: int = 10
    tokens_out: int = 10
    latency_ms: int = 5

    @classmethod
    def ok(
        cls, text: str, *, tokens_in: int = 10, tokens_out: int = 10, latency_ms: int = 5
    ) -> FakeOutcome:
        return cls(text=text, tokens_in=tokens_in, tokens_out=tokens_out, latency_ms=latency_ms)

    @classmethod
    def rate_limited(cls) -> FakeOutcome:
        return cls(raises=ProviderRateLimited("fake", "fake-model"))

    @classmethod
    def timeout(cls) -> FakeOutcome:
        return cls(raises=ProviderTimeout("fake", "fake-model"))

    @classmethod
    def server_error(cls, status_code: int = 503) -> FakeOutcome:
        return cls(raises=ProviderFailed("fake", "fake-model", status_code))

    @classmethod
    def malformed(cls) -> FakeOutcome:
        """Success at the transport level, but not JSON at all."""
        return cls(text="Sprout says something without any JSON in it.")

    @classmethod
    def schema_invalid(cls) -> FakeOutcome:
        """Valid JSON, but missing every schema's required fields."""
        return cls(text="{}")


class FakeProvider:
    """Deterministic stand-in for a real ``LLMProvider``. Never touches a network."""

    name = "fake"
    base_url = ""

    def __init__(
        self,
        *,
        responses: dict[str, str] | None = None,
        script: Sequence[FakeOutcome] | None = None,
    ) -> None:
        self._responses = {**DEFAULT_CANNED_RESPONSES, **(responses or {})}
        self._script: deque[FakeOutcome] = deque(script or ())
        self.calls: list[tuple[str, str | None]] = []
        """``(model_id, schema_title)`` for every ``complete()`` call, in
        order — lets tests assert exactly how many network calls a router
        made against this provider."""

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
        schema_title: str | None = None
        if json_schema is not None:
            title = json_schema.get("title")
            schema_title = title if isinstance(title, str) else None
        self.calls.append((model_id, schema_title))

        outcome = self._script.popleft() if self._script else None

        if outcome is not None and outcome.raises is not None:
            raise outcome.raises

        text = (
            outcome.text
            if outcome is not None and outcome.text is not None
            else self._responses.get(schema_title or "", "{}")
        )
        tokens_in = outcome.tokens_in if outcome is not None else 10
        tokens_out = outcome.tokens_out if outcome is not None else 10
        latency_ms = outcome.latency_ms if outcome is not None else 5

        return LLMResult(
            text=text,
            provider=self.name,
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            finish_reason="stop",
            raw_id=f"fake-{len(self.calls)}",
        )
