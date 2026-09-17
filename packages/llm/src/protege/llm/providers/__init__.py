"""Concrete ``LLMProvider`` implementations (roadmap P4).

``FakeProvider`` — deterministic, no network; the default for every test.
``NvidiaProvider`` — the runtime provider (addendum §9 point 3).

No ``AnthropicProvider`` lives here, and this subpackage never imports
``anthropic`` (docs/DECISIONS.md D7).
"""

from .fake import DEFAULT_CANNED_RESPONSES, FakeOutcome, FakeProvider
from .nvidia import NVIDIA_BASE_URL, NvidiaProvider

__all__ = [
    "DEFAULT_CANNED_RESPONSES",
    "NVIDIA_BASE_URL",
    "FakeOutcome",
    "FakeProvider",
    "NvidiaProvider",
]
