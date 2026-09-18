"""Command-line entry point for the P8 thin thread.

    python -m protege.thin_thread [--provider {auto,nvidia,fake}] [--scenario {happy,recovery}]

``--provider auto`` (the default) uses the real NVIDIA endpoint when
``NVIDIA_API_KEY`` is set in the environment, and otherwise falls back to
the deterministic :class:`~protege.llm.providers.fake.FakeProvider` --
"keep deterministic fallbacks armed so the transcript remains executable
when a provider ... is unavailable" (roadmap P8). Real NVIDIA calls are
never made implicitly in a test run (docs/DECISIONS.md D9); this CLI is
the small, explicitly-invoked demo path the roadmap carves out for them.
"""

from __future__ import annotations

import argparse
import os
import sys

from protege.authoring.loader import load_content_pack

from .engine import run_thin_thread
from .fake_script import build_fake_script
from .router_setup import ProviderChoice, build_router
from .scenario import happy_path_scenario, recovery_scenario, resolve_misconception


def _resolve_provider(requested: str) -> ProviderChoice:
    if requested == "auto":
        return "nvidia" if os.environ.get("NVIDIA_API_KEY") else "fake"
    return "nvidia" if requested == "nvidia" else "fake"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="protege.thin_thread", description=__doc__)
    parser.add_argument("--provider", choices=["auto", "nvidia", "fake"], default="auto")
    parser.add_argument("--scenario", choices=["happy", "recovery"], default="happy")
    args = parser.parse_args(argv)

    provider = _resolve_provider(args.provider)
    scenario = happy_path_scenario() if args.scenario == "happy" else recovery_scenario()

    content = load_content_pack()
    misconception = resolve_misconception(content)

    if provider == "nvidia":
        print(
            "[provider] NVIDIA_API_KEY detected -- using the real NVIDIA endpoint.",
            file=sys.stderr,
        )
        router = build_router("nvidia")
    else:
        reason = "requested" if args.provider == "fake" else "no NVIDIA_API_KEY set"
        print(
            f"[provider] using FakeProvider ({reason}) -- deterministic fallback path.",
            file=sys.stderr,
        )
        script = build_fake_script(
            scenario, misconception=misconception, sprout_scripts=content.sprout_scripts
        )
        router = build_router("fake", script=script)

    result = run_thin_thread(scenario, router, content=content, trace_sink=print)

    print()
    print("=== RESULT ===")
    print(f"final state: {result.final_state}")
    print(f"state sequence: {' -> '.join(str(s) for s in result.state_sequence)}")
    if result.mastery_outcome is not None:
        print(f"claim: {result.mastery_outcome.claim!r}")
        print(f"evidence ids: {result.claim_evidence_ids}")
        outcome = result.mastery_outcome
        print(f"p_known: {outcome.p_known_before:.2f} -> {outcome.p_known_after:.2f}")
        print(f"misconception posteriors: {result.mastery_outcome.misconception_posteriors}")
        print(f"caveats: {result.mastery_outcome.caveats}")
    else:
        print("no evidence-backed mastery claim was produced this run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
