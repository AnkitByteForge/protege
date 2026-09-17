"""Domain exceptions for PROTÉGÉ bounded roles.

P5 and P6 role-specific failures live here. These errors represent
authoring/configuration or closed-set violations that must fail loudly rather
than silently inventing or coercing state.
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
    """``misconception_id`` has no authored ``SproutScript`` candidates."""

    def __init__(self, misconception_id: str) -> None:
        self.misconception_id = misconception_id
        super().__init__(
            f"no authored SproutScript candidates for misconception "
            f"{misconception_id!r}"
        )


class PromptTemplateError(RoleError):
    """The versioned Sprout prompt template could not be loaded."""

    def __init__(self, path: str) -> None:
        self.path = path
        super().__init__(f"Sprout prompt template not found at {path!r}")


class DiagnosticianError(RoleError):
    """Base class for every P6 Diagnostician domain error."""


class NoClosedSetProvidedError(DiagnosticianError):
    """``diagnose`` was called with an empty ``misconception_set``."""


class DistractorNotInClosedSetError(DiagnosticianError):
    """A distractor maps to a code outside the supplied closed set."""

    def __init__(self, misconception_code: str) -> None:
        self.misconception_code = misconception_code
        super().__init__(
            f"distractor maps to {misconception_code!r}, which is not in the "
            "supplied closed set of misconceptions"
        )