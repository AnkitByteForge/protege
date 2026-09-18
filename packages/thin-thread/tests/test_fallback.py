"""P8 testing requirement #10: the fallback path still completes the
thread without corrupting learning state.

Forces every real NVIDIA chain entry for the SPROUT role to fail schema
parsing (malformed responses), driving the ``ModelRouter`` all the way to
its deterministic ``authored_fallback`` sentinel, and confirms
``SproutGenerator`` then emits its own authored line and the thin thread
still runs start to finish with a correct, uncorrupted claim.
"""

from __future__ import annotations

import json

from _helpers import get_content

from protege.contracts import SessionState as S
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.llm.router import ModelRouter
from protege.thin_thread.engine import run_thin_thread
from protege.thin_thread.scenario import RESOLUTION_EVIDENCE_SPAN, happy_path_scenario

# Two real ROLE_POLICY chain entries for SPROUT, each attempted natively
# plus one repair before the router gives up on it (see
# packages/llm/src/protege/llm/router.py's ROLE_POLICY) -- 2 entries x
# (native + 1 repair) = 4 real network calls before the router reaches its
# `authored_fallback` sentinel.
_MALFORMED_SPROUT_CALLS = 4


def test_sprout_schema_fallback_still_completes_with_a_correct_claim() -> None:
    content = get_content()
    scenario = happy_path_scenario()
    script = [
        *(FakeOutcome.malformed() for _ in range(_MALFORMED_SPROUT_CALLS)),
        FakeOutcome.ok(
            json.dumps(
                {
                    "labels": [
                        {
                            "misconception_id": "M003",
                            "state": "resolved",
                            "confidence": 0.89,
                            "evidence_span": RESOLUTION_EVIDENCE_SPAN,
                        }
                    ],
                    "understanding_signals": [
                        "inverse_denominator_relationship",
                        "partitioning_language",
                    ],
                    "asr_reliable": True,
                    "abstained": False,
                }
            )
        ),
    ]
    router = ModelRouter({"nvidia": FakeProvider(script=script)})

    result = run_thin_thread(scenario, router, content=content)

    assert result.sprout_attempts[0].used_fallback is True
    assert result.final_state == S.COMPLETE
    assert result.mastery_outcome is not None
    assert len(result.claim_evidence_ids) == 5
    assert result.mastery_outcome.p_known_after > result.mastery_outcome.p_known_before
