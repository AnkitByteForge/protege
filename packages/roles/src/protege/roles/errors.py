"""Errors for ``protege.roles`` (roadmap P5).

These are all authoring/configuration-bug signals, not runtime conditions a
session should route around: an unknown misconception code or an empty
candidate pool means the content pack and the caller disagree about what
exists, which must fail loudly (AGENTS.md: "never create a second source of
truth for state already represented elsewhere" -- silently inventing a
placeholder pool or misconception here would be exactly that).
"""

from __future__ import annotations


class RoleError(Exception):
    """Base for every ``protege.roles`` error."""


class UnknownMisconceptionError(RoleError):
    """``misconception_id`` has no authored ``Misconception`` record."""

    def __init__(self, misconception_id: str) -> None:
        self.misconception_id = misconception_id
        super().__init__(f"no authored Misconception with code {misconception_id!r}")


class NoCandidatePoolError(RoleError):
    """``misconception_id`` has no authored ``SproutScript`` candidates.

    The Sprout critical rule ("deterministic authored fallback must always
    be available") depends on this pool existing -- P3 authors six candidate
    utterances per misconception specifically so this never happens for real
    content.
    """

    def __init__(self, misconception_id: str) -> None:
        self.misconception_id = misconception_id
        super().__init__(
            f"no authored SproutScript candidates for misconception {misconception_id!r}"
        )


class PromptTemplateError(RoleError):
    """The versioned Sprout prompt template could not be loaded."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Sprout prompt template not found at {path!r}")
