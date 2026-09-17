"""Manual, real-network Sprout fidelity harness against the actual NVIDIA
endpoint (docs/DECISIONS.md D9; mirrors packages/llm/tests/test_nvidia_smoke.py's
gating convention, at a much larger — and therefore much more deliberately
gated — scale: 200 generations x 8 misconceptions = 1600 real model calls).

EXCLUDED from the default test run and from CI, exactly like the P4 smoke
test: `.github/workflows/ci.yml` runs plain `uv run pytest`, which never
sets the flag this file requires. `uv run pytest` (no flag) collects this
file and reports it skipped, same as `test_nvidia_smoke.py`.

This intentionally does NOT reuse `PROTEGE_RUN_NVIDIA_SMOKE` (that flag
gates a ~2-call sanity check): 1600 calls burns a meaningfully larger
fraction of the finite NVIDIA credit allowance (addendum §2.3), so it gets
its own, more deliberate opt-in.

Run it manually, once, with `-s` so the printed report is visible::

    NVIDIA_API_KEY=nvapi-... PROTEGE_RUN_SPROUT_FIDELITY_NVIDIA=1 \\
        uv run pytest packages/roles/tests/test_sprout_fidelity_nvidia.py -v -s

Or set NVIDIA_API_KEY in a git-ignored `.env` at the repo root (never
printed or logged by this file; loaded via python-dotenv if present).

Uses the SINGLE `ModelRouter` instance's real defaults end to end: the
actual `ROLE_POLICY[SPROUT]` chain (whatever NVIDIA model is currently
configured as Sprout's primary), the real 35 RPM `TokenBucket`, and
`ModelRouter.DEFAULT_TEMPERATURE` (0.7) -- nothing here overrides any of
those, and every call for all 8 misconceptions goes through this one
router/one bucket, sequentially, in-process. No concurrency, no second
provider instance, no bypass of the shared limiter.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from protege.authoring.loader import ContentPack
from protege.learning_engine.educational_validator import answer_leaked
from protege.llm.providers.nvidia import NvidiaProvider
from protege.llm.router import ModelRouter
from protege.roles.sprout import SproutGenerator, SproutState, score_fidelity

try:
    from dotenv import load_dotenv

    load_dotenv()  # populates os.environ from a git-ignored .env, if present
except ImportError:  # pragma: no cover - dotenv is already a workspace dependency
    pass

_FLAG = "PROTEGE_RUN_SPROUT_FIDELITY_NVIDIA"

pytestmark = pytest.mark.skipif(
    os.environ.get(_FLAG) != "1",
    reason=(
        f"real-network, 1600-call Sprout fidelity harness -- set {_FLAG}=1 and "
        "NVIDIA_API_KEY (env or .env) to run it deliberately; never runs in CI "
        "(docs/DECISIONS.md D9)"
    ),
)

N_GENERATIONS = 200
_OUTPUT_PATH = Path(os.environ.get("PROTEGE_SPROUT_FIDELITY_OUTPUT", "")) or None
"""Optional: write the full structured report as JSON to this path (e.g. the
caller's scratch directory) for later inspection -- never into the repo by
default."""


@dataclass
class MisconceptionFidelityReport:
    code: str
    generate_turn_calls: int = 0
    router_call_count: int = 0
    """Every real `router.call_structured` invocation (>= generate_turn_calls,
    since a validator failure on attempt 1 triggers a second router call)."""
    successful_generated: int = 0
    """generate_turn calls where a real, model-generated candidate passed
    the four-stage gate and was used as-is (NOT a deterministic fallback)."""
    fallback_count: int = 0
    fallback_schema: int = 0
    fallback_validator: int = 0
    validator_failure_count: int = 0
    """Count of individual SproutAttemptRecord entries that failed the gate
    (schema, consistency, leak, or content-safety) -- may exceed
    fallback_count, since a generate_turn call that succeeds on attempt 2
    still has one recorded failure on attempt 1."""
    leak_count: int = 0
    """Over ALL emitted turns (generated + fallback) -- the true end-to-end
    child-facing safety measurement."""
    generated_fidelities: list[float] = field(default_factory=list)
    """Fidelity scores over ONLY the non-fallback (real model-generated)
    turns -- deterministic authored fallbacks are never counted as a
    model-generation fidelity success (explicit instruction)."""

    @property
    def fallback_rate(self) -> float:
        return self.fallback_count / self.generate_turn_calls if self.generate_turn_calls else 0.0

    @property
    def mean_fidelity_generated_only(self) -> float | None:
        if not self.generated_fidelities:
            return None
        return sum(self.generated_fidelities) / len(self.generated_fidelities)

    @property
    def answer_leak_rate(self) -> float:
        return self.leak_count / self.generate_turn_calls if self.generate_turn_calls else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "generate_turn_calls": self.generate_turn_calls,
            "router_call_count": self.router_call_count,
            "successful_generated": self.successful_generated,
            "fallback_count": self.fallback_count,
            "fallback_schema": self.fallback_schema,
            "fallback_validator": self.fallback_validator,
            "fallback_rate": self.fallback_rate,
            "validator_failure_count": self.validator_failure_count,
            "leak_count": self.leak_count,
            "answer_leak_rate": self.answer_leak_rate,
            "mean_fidelity_generated_only": self.mean_fidelity_generated_only,
        }


def _run_one_misconception(
    generator: SproutGenerator, content_pack: ContentPack, code: str
) -> MisconceptionFidelityReport:
    example = content_pack.worked_examples[code]
    item_stem = example.diagnostic_item.stem
    correct_answer = example.diagnostic_item.correct_answer
    misconception = next(m for m in content_pack.misconceptions if m.code == code)

    report = MisconceptionFidelityReport(code=code)
    for turn_index in range(N_GENERATIONS):
        result = generator.generate_turn(
            state=SproutState(misconception_id=code, turn_index=turn_index),
            item_stem=item_stem,
            correct_answer=correct_answer,
        )
        report.generate_turn_calls += 1
        report.router_call_count += len(result.attempts)
        report.validator_failure_count += sum(1 for a in result.attempts if not a.validation.passed)

        if result.used_fallback:
            report.fallback_count += 1
            if result.fallback_reason is not None and "schema" in str(result.fallback_reason):
                report.fallback_schema += 1
            else:
                report.fallback_validator += 1
        else:
            report.successful_generated += 1
            report.generated_fidelities.append(
                score_fidelity(
                    result.turn, misconception=misconception, correct_answer=correct_answer
                )
            )

        # Answer leakage: the existing P2 deterministic mechanism, over
        # EVERY final emitted turn (generated or fallback) -- the true
        # child-facing safety measurement. Zero tolerance.
        if answer_leaked(result.turn.utterance, correct_answer):
            report.leak_count += 1

        print(
            f"[{code}] {turn_index + 1}/{N_GENERATIONS} "
            f"fallback={result.used_fallback} reason={result.fallback_reason}",
            flush=True,
        )

    return report


def test_real_nvidia_sprout_fidelity_gate(content_pack: ContentPack) -> None:
    """The formal P5 exit gate, measured against the real, currently
    configured Sprout primary NVIDIA model (whatever `ROLE_POLICY[SPROUT]`
    names) -- not FakeProvider.

    Gate (roadmap P5, unchanged from the FakeProvider harness):
      - mean fidelity (over real model-generated, non-fallback turns) >= 0.90
      - answer_leak_rate (over ALL emitted turns) == 0.000
    both per-misconception and overall, across all 8 misconceptions.
    """
    # Real defaults end to end: ROLE_POLICY[SPROUT], 35 RPM, temperature 0.7.
    router = ModelRouter({"nvidia": NvidiaProvider()})
    generator = SproutGenerator(router, content=content_pack)

    reports: list[MisconceptionFidelityReport] = []
    for misconception in content_pack.misconceptions:
        reports.append(_run_one_misconception(generator, content_pack, misconception.code))

    total_calls = sum(r.generate_turn_calls for r in reports)
    total_leaks = sum(r.leak_count for r in reports)
    total_router_calls = sum(r.router_call_count for r in reports)
    total_successful_generated = sum(r.successful_generated for r in reports)
    total_fallback = sum(r.fallback_count for r in reports)
    total_validator_failures = sum(r.validator_failure_count for r in reports)
    all_generated_fidelities = [f for r in reports for f in r.generated_fidelities]
    overall_mean_fidelity = (
        sum(all_generated_fidelities) / len(all_generated_fidelities)
        if all_generated_fidelities
        else None
    )
    overall_leak_rate = total_leaks / total_calls if total_calls else 1.0

    summary = {
        "per_misconception": [r.as_dict() for r in reports],
        "overall": {
            "total_generate_turn_calls": total_calls,
            "total_router_call_count": total_router_calls,
            "total_successful_generated": total_successful_generated,
            "total_fallback_count": total_fallback,
            "overall_fallback_rate": total_fallback / total_calls if total_calls else 0.0,
            "total_validator_failure_count": total_validator_failures,
            "total_leak_count": total_leaks,
            "overall_answer_leak_rate": overall_leak_rate,
            "overall_mean_fidelity_generated_only": overall_mean_fidelity,
        },
    }
    print("\n=== P5 REAL-MODEL FIDELITY REPORT ===")
    print(json.dumps(summary, indent=2))

    if _OUTPUT_PATH is not None:
        _OUTPUT_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Hard, zero-tolerance safety gate first: any leak at all fails the run.
    assert total_leaks == 0, f"answer_leak_rate {overall_leak_rate:.4f} != 0.000 -- {summary}"

    failures = [
        r.code
        for r in reports
        if r.mean_fidelity_generated_only is None or r.mean_fidelity_generated_only < 0.90
    ]
    assert not failures, f"mean fidelity < 0.90 for {failures} -- {summary}"
    assert overall_mean_fidelity is not None and overall_mean_fidelity >= 0.90, summary
