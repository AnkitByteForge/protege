"""Manual, real-network Sprout fidelity harness against the actual NVIDIA
endpoint (docs/DECISIONS.md D9; mirrors packages/llm/tests/test_nvidia_smoke.py's
gating convention).

EXCLUDED from the default test run and from CI: `.github/workflows/ci.yml`
runs plain `uv run pytest`, which never sets the flag this file requires.

Run it manually, once, with `-s` so progress is visible::

    PROTEGE_RUN_SPROUT_FIDELITY_NVIDIA=1 uv run pytest \\
        packages/roles/tests/test_sprout_fidelity_nvidia.py -v -s

Configuration (all optional; defaults run the full formal-scale sweep):

    PROTEGE_SPROUT_FIDELITY_N                  generations per misconception
                                                (default 200; pilot uses 16)
    PROTEGE_SPROUT_FIDELITY_MISCONCEPTIONS     comma-separated codes to run
                                                (default: all 8)
    PROTEGE_SPROUT_FIDELITY_CHECKPOINT_DIR     per-misconception checkpoint
                                                directory (default: a
                                                system-temp subdirectory,
                                                never inside the repo)
    PROTEGE_SPROUT_FIDELITY_ASSERT_GATE        "1" to assert the formal
                                                mean-fidelity >= 0.90 gate.
                                                Unset for a pilot/data-only
                                                run (task instruction: "Do
                                                NOT treat the pilot as the
                                                formal P5 gate"). The
                                                answer_leak_rate == 0.000
                                                gate is ALWAYS asserted --
                                                it is unconditional, zero
                                                tolerance, never gated.
    PROTEGE_SPROUT_FIDELITY_FORCE              "1" to ignore existing
                                                checkpoints and re-run
                                                (default: resume/skip
                                                already-checkpointed
                                                misconceptions)
    PROTEGE_SPROUT_FIDELITY_OUTPUT             optional path to also write
                                                the full JSON summary

NVIDIA_API_KEY is loaded from a git-ignored .env at the repo root if
present (never printed or logged).

Uses ONE ModelRouter instance, its real ROLE_POLICY[SPROUT] chain and 35
RPM TokenBucket, sequentially, in-process -- see _eval_harness.py for the
circuit-breaker-aware, resumable, unbiased evaluation logic this file only
configures and invokes.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from _eval_harness import (
    BREAKER_COOLDOWN_S,
    BREAKER_FAILURE_THRESHOLD,
    aggregate_reports,
    evaluate_misconception,
)

from protege.authoring.loader import ContentPack
from protege.llm.circuit_breaker import CircuitBreaker
from protege.llm.providers.nvidia import NvidiaProvider
from protege.llm.router import ModelRouter
from protege.llm.telemetry import InMemoryTelemetrySink
from protege.roles.sprout import SproutGenerator

try:
    from dotenv import load_dotenv

    # Explicit path avoids python-dotenv's frame-inspection-based
    # find_dotenv() (unreliable outside a normal module import). This file
    # lives at packages/roles/tests/ -- three parents up is the repo root.
    _repo_root_env = Path(__file__).resolve().parents[3] / ".env"
    load_dotenv(dotenv_path=_repo_root_env)
except ImportError:  # pragma: no cover - dotenv is already a workspace dependency
    pass

_FLAG = "PROTEGE_RUN_SPROUT_FIDELITY_NVIDIA"

pytestmark = pytest.mark.skipif(
    os.environ.get(_FLAG) != "1",
    reason=(
        f"real-network Sprout fidelity harness -- set {_FLAG}=1 and NVIDIA_API_KEY "
        "(env or .env) to run it deliberately; never runs in CI (docs/DECISIONS.md D9)"
    ),
)

_ALL_MISCONCEPTIONS = tuple(f"M{i:03d}" for i in range(1, 9))
_DEFAULT_N = 200


def _selected_misconceptions() -> tuple[str, ...]:
    raw = os.environ.get("PROTEGE_SPROUT_FIDELITY_MISCONCEPTIONS", "")
    if not raw.strip():
        return _ALL_MISCONCEPTIONS
    return tuple(code.strip() for code in raw.split(",") if code.strip())


def _n_generations() -> int:
    return int(os.environ.get("PROTEGE_SPROUT_FIDELITY_N", str(_DEFAULT_N)))


def _checkpoint_dir() -> Path:
    raw = os.environ.get("PROTEGE_SPROUT_FIDELITY_CHECKPOINT_DIR", "")
    if raw.strip():
        return Path(raw)
    return Path(tempfile.gettempdir()) / "protege_sprout_fidelity_checkpoints"


def test_real_nvidia_sprout_fidelity_evaluation(content_pack: ContentPack) -> None:
    n_generations = _n_generations()
    codes = _selected_misconceptions()
    checkpoint_dir = _checkpoint_dir()
    force = os.environ.get("PROTEGE_SPROUT_FIDELITY_FORCE") == "1"
    assert_gate = os.environ.get("PROTEGE_SPROUT_FIDELITY_ASSERT_GATE") == "1"

    print(f"\nEvaluating {codes} at n={n_generations}, checkpoint_dir={checkpoint_dir}")

    breaker = CircuitBreaker(
        failure_threshold=BREAKER_FAILURE_THRESHOLD, cooldown_s=BREAKER_COOLDOWN_S
    )
    telemetry = InMemoryTelemetrySink()
    # Real defaults end to end: ROLE_POLICY[SPROUT], 35 RPM, temperature 0.7,
    # except timeout_s -- a direct isolated probe against the real endpoint
    # with this prompt shape measured 4-6s real latency (plus an observed
    # transient 503); the router's production DEFAULT_TIMEOUT_S (2.5s,
    # addendum §2.3) is far too short for that. This overrides only THIS
    # harness's ModelRouter instance, not packages/llm's source or default.
    router = ModelRouter({"nvidia": NvidiaProvider()}, circuit_breaker=breaker, timeout_s=20.0)
    generator = SproutGenerator(router, content=content_pack)

    reports = [
        evaluate_misconception(
            generator,
            content_pack,
            code,
            n_generations=n_generations,
            breaker=breaker,
            telemetry=telemetry,
            checkpoint_dir=checkpoint_dir,
            force=force,
            progress=print,
        )
        for code in codes
    ]

    summary = aggregate_reports(reports)
    print("\n=== P5 REAL-MODEL FIDELITY REPORT ===")
    print(json.dumps(summary, indent=2))

    output_path = os.environ.get("PROTEGE_SPROUT_FIDELITY_OUTPUT", "")
    if output_path:
        Path(output_path).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    overall = summary["overall"]
    assert isinstance(overall, dict)

    # Unconditional, zero-tolerance -- never gated behind ASSERT_GATE.
    assert overall["total_leak_count"] == 0, (
        f"answer_leak_rate {overall['overall_answer_leak_rate']:.4f} != 0.000 -- {summary}"
    )

    if not assert_gate:
        pytest.skip(
            "PROTEGE_SPROUT_FIDELITY_ASSERT_GATE not set -- this was a data-collection "
            "run (e.g. the pilot), not the formal P5 gate. Leak gate passed; fidelity "
            "gate intentionally not asserted. See the printed report for the numbers."
        )

    mean_fidelity = overall["overall_mean_fidelity"]
    assert mean_fidelity is not None and mean_fidelity >= 0.90, (
        f"mean fidelity {mean_fidelity} < 0.90 -- {summary}"
    )
    per_misconception_failures = [
        r["code"]
        for r in summary["per_misconception"]
        if r["mean_fidelity"] is None or r["mean_fidelity"] < 0.90  # type: ignore[operator]
    ]
    assert not per_misconception_failures, (
        f"mean fidelity < 0.90 for {per_misconception_failures} -- {summary}"
    )
