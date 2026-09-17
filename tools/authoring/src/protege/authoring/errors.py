"""Deterministic content-validation errors (roadmap P3).

The authoring workflow validates and normalizes authored content; it never
silently repairs it. Every failure surfaces here with enough context (which
file, which record, which rule) for a human to fix the source JSON.
"""

from __future__ import annotations


class ContentError(Exception):
    """Base class for every P3 content-pipeline error."""


class ContentLoadError(ContentError):
    """A content file failed to parse as JSON or failed Pydantic validation.

    Raised by ``loader.py`` before any semantic (cross-file) check runs —
    a malformed record is never partially trusted.
    """

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: {reason}")


class ContentValidationError(ContentError):
    """One deterministic P3 validation rule failed (validators.py).

    ``rule`` is a stable machine-readable slug (e.g. ``"id_uniqueness"``) so
    the manifest and CI output can group failures by rule, not just by
    message text.
    """

    def __init__(self, rule: str, message: str) -> None:
        self.rule = rule
        self.message = message
        super().__init__(f"[{rule}] {message}")


class ContentValidationFailed(ContentError):
    """Raised by the CLI/gate when one or more validation rules failed.

    Carries every individual :class:`ContentValidationError` so a caller can
    report all failures at once rather than stopping at the first.
    """

    def __init__(self, errors: list[ContentValidationError]) -> None:
        self.errors = errors
        summary = "; ".join(f"[{e.rule}] {e.message}" for e in errors)
        super().__init__(f"{len(errors)} content validation rule(s) failed: {summary}")
