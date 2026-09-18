"""ModelRouter construction for the P8 thin thread.

Uses the existing P4 :class:`~protege.llm.router.ModelRouter` and its
already-configured ``ROLE_POLICY`` fallback chain (roadmap P8 rule 10: "Use
the existing P4 ModelRouter and its configured fallback chain. Do not create
another model client.") -- this module only registers a provider under the
``"nvidia"`` name the chain already expects; it never overrides
``ROLE_POLICY`` itself.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.providers.nvidia import NvidiaProvider
from protege.llm.router import ModelRouter

ProviderChoice = Literal["nvidia", "fake"]


def build_router(
    provider: ProviderChoice,
    *,
    script: Sequence[FakeOutcome] | None = None,
) -> ModelRouter:
    """Build a real :class:`ModelRouter` wired to either the real NVIDIA
    endpoint or a deterministic :class:`FakeProvider`.

    ``script`` is only meaningful for ``provider="fake"`` -- it is consumed
    in the exact order the engine makes calls (Sprout, then Diagnostician,
    per teach-back turn), since both roles' ``ROLE_POLICY`` chains resolve
    to the SAME registered ``"nvidia"`` provider instance.
    """
    if provider == "nvidia":
        return ModelRouter({"nvidia": NvidiaProvider()})
    return ModelRouter({"nvidia": FakeProvider(script=script)})
