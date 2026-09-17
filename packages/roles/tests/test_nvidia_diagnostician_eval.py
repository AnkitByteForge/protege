"""Manual, real-network evaluation of the P6 Diagnostician against
``ROLE_POLICY[DIAGNOSTICIAN]``'s actual configured models (roadmap P6;
docs/DECISIONS.md D3, D9).

This makes up to 120 REAL calls to NVIDIA's hosted endpoint (one per golden
example) and spends real NVIDIA credits (addendum §2.3) -- far more than
``packages/llm/tests/test_nvidia_smoke.py``'s two calls. It is EXCLUDED
from the default test run and from CI, using the exact same gating pattern
as that smoke test, plus its own, separate flag (so enabling the cheap
smoke test never accidentally triggers this 120-call run):

    NVIDIA_API_KEY=nvapi-... PROTEGE_RUN_DIAGNOSTICIAN_EVAL=1 \\
        uv run pytest packages/roles/tests/test_nvidia_diagnostician_eval.py -v -s

**This does not use a custom role policy.** It constructs the router with
``packages/llm``'s real, unmodified ``ROLE_POLICY`` so the "primary model"
in the report is genuinely ``ROLE_POLICY[DIAGNOSTICIAN]``'s first chain
entry, not a substitute chosen for convenience.

**This is a development/provisional measurement, not the roadmap's formal
ship-gate result** -- the golden set it runs against is machine-derived
from P3 content, not independently hand-labelled
(``packages/roles/golden_set/PROVENANCE.md``). The report this test writes
says so explicitly (``dataset_status``), and this test does not assert
macro-F1/ECE/Brier against the 0.75/0.10/0.18 gate values: a numeric
threshold assertion here would either rubber-stamp an unratified dataset as
if it were the gate, or (if it failed) block on a measurement whose fix is
prompt/few-shot work, not a threshold change (roadmap instruction: "if real
NVIDIA metrics fail, fix prompt/few-shot/classifier behavior before
proceeding; do not simply lower the threshold" -- neither direction belongs
in an automated assertion here). It reports every number, prints a full
summary, and writes a timestamped JSON report to
``packages/roles/golden_set/nvidia_eval_reports/`` for a human to read.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from protege.authoring.loader import load_content_pack
from protege.contracts import Misconception, PedagogicalRole
from protege.llm import ModelRouter, NvidiaProvider
from protege.llm.rate_limit import TokenBucket
from protege.roles.eval import (
    PerClassMetrics,
    evaluate_rule_based_only,
    run_nvidia_diagnostician_evaluation,
)
from protege.roles.golden_set import DATASET_STATUS, load_golden_set

_FLAG = "PROTEGE_RUN_DIAGNOSTICIAN_EVAL"

_DIAGNOSTICIAN_TIMEOUT_S = 45.0
"""``ModelRouter``'s ``DEFAULT_TIMEOUT_S`` (2.5 s) is tuned for Sprout's
turn-taking latency budget (addendum §2.3), not for DIAGNOSTICIAN's primary
model -- a live diagnostic run against this exact ``ROLE_POLICY`` entry
measured 11-20 s real latency for a single completion (550B reasoning
model). Using the 2.5 s default here does not test the model; it
guarantees a timeout on every call, which then trips the 3-failure circuit
breaker (``packages/llm/src/protege/llm/circuit_breaker.py``) and cascades
into `circuit_open` failures for everything after -- exactly what a first
run against this file, before this constant existed, produced (0/120
primary successes, 117/120 falling through to the rule-based fallback).
Not a workaround for a slow model to "make the gate" -- an evaluation
harness must use a timeout the role's actual configured model can be
fairly measured against; 2.5 s never gave it that chance."""

pytestmark = pytest.mark.skipif(
    os.environ.get(_FLAG) != "1",
    reason=(
        f"real-network Diagnostician golden-set evaluation (up to 120 NVIDIA "
        f"calls) — set {_FLAG}=1 and NVIDIA_API_KEY to run it deliberately; "
        "never runs in CI (docs/DECISIONS.md D9)"
    ),
)

_REPORT_DIR = Path(__file__).resolve().parents[1] / "golden_set" / "nvidia_eval_reports"


def _print_confusion(confusion: dict[tuple[str, str], int]) -> None:
    print("\nConfusion matrix (true_code, predicted_code) -> count:")
    for (true_code, predicted_code), count in sorted(confusion.items()):
        print(f"  {true_code:>6} -> {predicted_code:<8} : {count}")


def _print_per_class(per_class: dict[str, PerClassMetrics]) -> None:
    print("\nPer-misconception precision / recall / F1 / support:")
    for code in sorted(per_class):
        m = per_class[code]
        line = f"  {code}: precision={m.precision:.4f}  recall={m.recall:.4f}"
        line += f"  f1={m.f1:.4f}  support={m.support}"
        print(line)


def test_real_nvidia_diagnostician_evaluation() -> None:
    examples = load_golden_set()
    misconception_set: list[Misconception] = load_content_pack().misconceptions

    router = ModelRouter(
        {"nvidia": NvidiaProvider()},  # real ROLE_POLICY, unmodified
        timeout_s=_DIAGNOSTICIAN_TIMEOUT_S,
        # Real 35 RPM budget, same as ModelRouter's own default (addendum
        # §2.3) -- named explicitly here, not left implicit, since this
        # constructor call is the one place in the codebase that spends it.
        rate_limiter=TokenBucket(rate_per_minute=35.0),
    )
    nvidia_report = run_nvidia_diagnostician_evaluation(
        examples, router, misconception_set=misconception_set
    )
    rule_based_report = evaluate_rule_based_only(examples, misconception_set=misconception_set)

    accounted = (
        nvidia_report.primary_success_count
        + nvidia_report.secondary_fallback_count
        + nvidia_report.rule_based_fallback_count
        + nvidia_report.no_telemetry_count
    )
    assert accounted == nvidia_report.n == 120
    assert nvidia_report.dataset_status == DATASET_STATUS == "development_not_ratified"

    print(f"\n{'=' * 70}")
    print("DIAGNOSTICIAN real-model evaluation — DEVELOPMENT/PROVISIONAL")
    print(f"dataset_status = {nvidia_report.dataset_status!r} (NOT human-ratified)")
    print(f"n = {nvidia_report.n}")
    print(f"role_policy = {PedagogicalRole.DIAGNOSTICIAN}")
    print(f"  primary chain[0]   = {nvidia_report.primary_model_id}")
    print(f"  secondary chain[1] = {nvidia_report.secondary_model_id}")
    print(f"  primary_success_count   = {nvidia_report.primary_success_count}")
    print(f"  secondary_fallback_count = {nvidia_report.secondary_fallback_count}")
    print(f"  rule_based_fallback_count = {nvidia_report.rule_based_fallback_count}")
    print(f"  no_telemetry_count      = {nvidia_report.no_telemetry_count}")
    print(f"  primary_rate  = {nvidia_report.primary_rate:.4f}")
    print(f"  fallback_rate = {nvidia_report.fallback_rate:.4f}")
    print(f"  abstention_rate = {nvidia_report.report.abstention_rate:.4f}")
    print(f"  macro_f1 = {nvidia_report.report.macro_f1:.4f}  (gate: >= 0.75)")
    print(f"  ece      = {nvidia_report.report.ece:.4f}  (gate: <= 0.10)")
    print(f"  brier    = {nvidia_report.report.brier:.4f}  (gate: <= 0.18)")
    _print_confusion(nvidia_report.report.confusion)
    _print_per_class(nvidia_report.report.per_class)

    print("\nRule-based baseline (full 120-item set, for comparison):")
    print(f"  abstention_rate = {rule_based_report.abstention_rate:.4f}")
    print(f"  macro_f1 = {rule_based_report.macro_f1:.4f}")
    print(f"  ece      = {rule_based_report.ece:.4f}")
    print(f"  brier    = {rule_based_report.brier:.4f}")
    _print_per_class(rule_based_report.per_class)

    gate_note = (
        "MEETS the numeric gate values, but the dataset is development/provisional "
        "(see packages/roles/golden_set/PROVENANCE.md) -- this is NOT a ratified "
        "ship-gate pass."
        if (
            nvidia_report.report.macro_f1 >= 0.75
            and nvidia_report.report.ece <= 0.10
            and nvidia_report.report.brier <= 0.18
        )
        else "Does NOT meet one or more numeric gate values on this development set."
    )
    print(f"\n{gate_note}")
    print(f"{'=' * 70}\n")

    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = _REPORT_DIR / f"nvidia_eval_{timestamp}.json"
    report_path.write_text(
        json.dumps(
            {
                "dataset_status": nvidia_report.dataset_status,
                "generated_at": timestamp,
                "n": nvidia_report.n,
                "primary_model_id": nvidia_report.primary_model_id,
                "secondary_model_id": nvidia_report.secondary_model_id,
                "primary_success_count": nvidia_report.primary_success_count,
                "secondary_fallback_count": nvidia_report.secondary_fallback_count,
                "rule_based_fallback_count": nvidia_report.rule_based_fallback_count,
                "no_telemetry_count": nvidia_report.no_telemetry_count,
                "primary_rate": nvidia_report.primary_rate,
                "fallback_rate": nvidia_report.fallback_rate,
                "abstention_rate": nvidia_report.report.abstention_rate,
                "macro_f1": nvidia_report.report.macro_f1,
                "ece": nvidia_report.report.ece,
                "brier": nvidia_report.report.brier,
                "confusion": {
                    f"{t}->{p}": c for (t, p), c in nvidia_report.report.confusion.items()
                },
                "per_class": {
                    code: {
                        "precision": m.precision,
                        "recall": m.recall,
                        "f1": m.f1,
                        "support": m.support,
                    }
                    for code, m in nvidia_report.report.per_class.items()
                },
                "rule_based_baseline": {
                    "abstention_rate": rule_based_report.abstention_rate,
                    "macro_f1": rule_based_report.macro_f1,
                    "ece": rule_based_report.ece,
                    "brier": rule_based_report.brier,
                    "per_class": {
                        code: {
                            "precision": m.precision,
                            "recall": m.recall,
                            "f1": m.f1,
                            "support": m.support,
                        }
                        for code, m in rule_based_report.per_class.items()
                    },
                },
                "gate_note": gate_note,
                "gate_values": {"macro_f1_min": 0.75, "ece_max": 0.10, "brier_max": 0.18},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Full report written to {report_path}")
