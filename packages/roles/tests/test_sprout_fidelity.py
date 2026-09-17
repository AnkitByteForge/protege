"""Sprout fidelity harness (roadmap P5 testing requirement):

    "Fidelity harness: 200 generations per misconception. Gate: mean
    fidelity >= 0.90, answer_leak_rate = 0.000 (deterministic substring +
    numeric-equivalence check, not an LLM judge)."

Runs entirely against `FakeProvider` (docs/DECISIONS.md D9: no real NVIDIA
calls in default CI). Each misconception's script interleaves short,
Grade-3-safe synthetic "good" candidates (standing in for a well-behaved
generation -- real P3 Sprout scripts are authored content whose reading
level is not itself asserted anywhere in this repo's existing P3 test
suite, see tools/authoring/tests/test_sprout_scripts.py, so reusing them
verbatim here would measure P3 content authoring, not the P5 pipeline)
with periodic deliberately-leaking candidates, so the harness exercises
both the fidelity gate AND the zero-leak guarantee under the same 200-count
budget the roadmap specifies -- not just a pass-through of clean input.
"""

from __future__ import annotations

from conftest import make_router, sprout_turn_json

from protege.authoring.loader import ContentPack
from protege.llm.providers.fake import FakeOutcome, FakeProvider
from protege.roles.sprout import SproutGenerator, SproutState, score_fidelity

N_GENERATIONS = 200
_BAD_EVERY = 25
"""Every 25th generation is forced to fail validation twice (a deliberate
answer leak), so ~4% of the 200 exercise the authored-fallback path."""

_SAFE_GOOD_UTTERANCES = (
    "My answer feels right. I am pretty sure about it!",
    "I picked this one. It just seems true to me!",
    "That is what I think. It looks right to me!",
    "I feel sure about my answer. It makes sense to me!",
    "This is my answer. I think it is correct!",
)
"""Short, Grade-3-safe, content-neutral stand-ins for a well-behaved
generation. Neutral wording is intentional: stage 2 of the validation gate
(misconception consistency) checks the structured `exhibits` field, not the
utterance's prose, so these are valid "good" candidates for any
misconception code without needing to be topically specific."""


def _misconception_codes(content_pack: ContentPack) -> list[str]:
    return [m.code for m in content_pack.misconceptions]


def _item_context(content_pack: ContentPack, code: str) -> tuple[str, str]:
    """(item_stem, correct_answer) for this misconception's §38 worked
    example -- reusing real P3 content rather than inventing fixtures."""
    example = content_pack.worked_examples[code]
    return example.diagnostic_item.stem, example.diagnostic_item.correct_answer


def _build_script(code: str, correct_answer: str) -> list[FakeOutcome]:
    outcomes: list[FakeOutcome] = []
    for i in range(N_GENERATIONS):
        if (i + 1) % _BAD_EVERY == 0:
            leaking = sprout_turn_json(
                utterance=f"I bet it's {correct_answer}, has to be!", exhibits=code
            )
            # Both attempts leak -> generate_turn exhausts its 2 attempts
            # and falls back; two script entries are consumed for this slot.
            outcomes.append(FakeOutcome.ok(leaking))
            outcomes.append(FakeOutcome.ok(leaking))
        else:
            utterance = _SAFE_GOOD_UTTERANCES[i % len(_SAFE_GOOD_UTTERANCES)]
            body = sprout_turn_json(utterance=utterance, exhibits=code)
            outcomes.append(FakeOutcome.ok(body))
    return outcomes


def test_fidelity_and_leak_gates_hold_for_every_misconception(content_pack: ContentPack) -> None:
    for code in _misconception_codes(content_pack):
        assert any(s.misconception_code == code for s in content_pack.sprout_scripts), (
            f"{code} has no authored candidate pool"
        )
        item_stem, correct_answer = _item_context(content_pack, code)
        misconception = next(m for m in content_pack.misconceptions if m.code == code)

        script = _build_script(code, correct_answer)
        provider = FakeProvider(script=script)
        generator = SproutGenerator(make_router(provider), content=content_pack)

        fidelities: list[float] = []
        leaks = 0
        fallbacks = 0
        for turn_index in range(N_GENERATIONS):
            result = generator.generate_turn(
                state=SproutState(misconception_id=code, turn_index=turn_index),
                item_stem=item_stem,
                correct_answer=correct_answer,
            )
            if result.used_fallback:
                fallbacks += 1
            fidelities.append(
                score_fidelity(
                    result.turn, misconception=misconception, correct_answer=correct_answer
                )
            )
            if correct_answer.lower() in result.turn.utterance.lower():
                leaks += 1

        mean_fidelity = sum(fidelities) / len(fidelities)
        leak_rate = leaks / N_GENERATIONS

        assert mean_fidelity >= 0.90, f"{code}: mean fidelity {mean_fidelity:.3f} < 0.90"
        assert leak_rate == 0.0, f"{code}: answer_leak_rate {leak_rate:.3f} != 0.000"
        assert fallbacks > 0, f"{code}: fallback path was never exercised by the harness"
