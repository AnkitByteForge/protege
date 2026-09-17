"""Three-tier structured-output primitives (addendum §2.5, §9 point 8).

Tier 1 — native constrained decoding: the provider is asked for
``json_schema``-shaped output directly.
Tier 2 — one repair attempt: the model's own malformed output is fed back
with an explicit instruction to return ONLY JSON matching the schema.
Tier 3 — deterministic fallback: the caller moves to the next
fallback-chain entry, ending in a role's authored/rule-based content.

This module implements the parsing and repair-prompt primitives for tiers
1-2; ``router.ModelRouter`` owns tier 3 and the orchestration between tiers.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from enum import StrEnum

from pydantic import BaseModel, ValidationError

from .base import Message

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.S)


class StructuredMode(StrEnum):
    """``model_runs.structured_mode`` (addendum §2.7): which tier produced
    the parsed value, or that every tier failed for this attempt."""

    NATIVE = "native"
    PROMPT = "prompt"
    FAILED = "failed"


class StructuredParseError(Exception):
    """``raw`` could not be parsed and validated against a target model.

    Wraps whichever of ``ValueError`` / ``json.JSONDecodeError`` /
    ``pydantic.ValidationError`` was raised, so callers only ever need to
    catch one exception type regardless of which parsing step failed.
    """

    def __init__(self, cause: Exception) -> None:
        self.cause = cause
        super().__init__(str(cause))


def extract_json_object(raw: str) -> str:
    """Tolerate prose wrappers around the JSON object (addendum §2.5)."""
    match = _JSON_OBJECT_RE.search(raw)
    if match is None:
        raise ValueError("no JSON object found in model output")
    return match.group(0)


def parse_structured[ModelT: BaseModel](raw: str, model_cls: type[ModelT]) -> ModelT:
    """Extract, decode, and validate ``raw`` against ``model_cls``.

    Raises ``StructuredParseError`` for any failure in that pipeline.
    """
    try:
        candidate = extract_json_object(raw)
        data = json.loads(candidate)
        return model_cls.model_validate(data)
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        raise StructuredParseError(exc) from exc


def build_repair_messages(original: Sequence[Message], raw: str, error: Exception) -> list[Message]:
    """One repair turn: show the model its own bad output and the validation
    error, and ask for JSON only (addendum §2.5's ``call_structured`` example).
    """
    return [
        *original,
        Message("assistant", raw),
        Message(
            "user",
            "That was not valid. Return ONLY JSON matching the requested "
            f"schema, with no prose. Error: {error}",
        ),
    ]
