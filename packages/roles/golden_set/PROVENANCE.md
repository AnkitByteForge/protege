# Provenance — Diagnostician golden set v1 (`diagnostician_v1.json`)

**Status: DEVELOPMENT / PROVISIONAL. NOT RATIFIED. NOT independently
labelled.** No human has reviewed or signed off on this file, and no
independent rater has ever looked at any of the 120 texts below and
assigned a label separately from its source. Nothing in `protege.roles` or
its tests may set this status to ratified — only a human editing this file
does, exactly as `content/math/fractions/v1/RATIFICATION.md` already
establishes for the underlying content pack. Every `EvalReport` this
codebase produces from this set carries `dataset_status =
"development_not_ratified"` (`protege.roles.golden_set.DATASET_STATUS`) for
exactly this reason — **do not cite any number computed against this file
as the roadmap's formal ship-gate result** (docs/DECISIONS.md D3: macro-F1
≥ 0.75, ECE ≤ 0.10, Brier ≤ 0.18 "measured on the 120-item golden set with
the actual runtime model"). Until this file says ratified, every such
number is a development measurement only.

## What this is

120 examples, 15 per authored misconception (`M001`–`M008`), generated
**deterministically by code**
(`protege.roles.golden_set.generate_golden_set`) from content already
authored and checked into `content/math/fractions/v1/` for roadmap P3:

| Source (per misconception) | Count | Ground-truth state | Origin file | Ground truth = |
|---|---|---|---|---|
| Sprout candidate utterance | 6 | `unresolved` | `sprout_scripts.json` | `SproutScript.misconception_code` |
| Worked-example child explanation | 1 | `resolved` | `worked_examples/M0XX.json` | the file's own identity (it IS that misconception's worked example) |
| Item-bank distractor, templated | 8 | `unresolved` | `items/diagnostic.json` | `Distractor.maps_to` |

## Why this is not merely "unratified" — it is not independent at all

For every one of the 120 examples, the ground-truth label was **copied
from the exact same authored field that produced the example's text**.
No transcript was read blind and labelled; the label and the text share a
single origin. This matters differently for the two evidence shapes in
this set:

- **The 64 `distractor_template` examples are circular for the rule-based
  path specifically.** Their ground truth is `Distractor.maps_to` — the
  literal field `protege.roles.rule_based.rule_based_diagnosis` reads to
  answer. Measuring the rule-based fallback against this subset (see
  `packages/roles/tests/test_eval.py`) produces a perfect score **by
  construction**, not because the fallback demonstrates any diagnostic
  skill. It proves only that the lookup echoes its own input. Read
  `protege.roles.eval`'s module docstring before citing any number from
  that subset.
- **All 120 examples are "easy mode" for any classifier, rule-based or
  LLM.** A Sprout script was authored specifically *to exhibit* one named
  misconception in clear, stylized language — real child speech is
  noisier, more ambiguous, and more likely to blend cues from more than
  one misconception. A classifier that scores well here has not yet been
  shown to generalize to an authentic child transcript.

## What this is **not**

- **Not independently hand-labelled.** See above.
- **Not Fable-generated in this session.** The roadmap (P6 Data field)
  calls for a Fable-drafted-then-human-ratified golden set ($25 budget);
  no such generation or spend happened here. Reusing already-authored P3
  content is the honest alternative available without fabricating either a
  model call that did not happen or a human review that did not happen.
- **Not a substitute for the roadmap's actual gate**, even once a real
  NVIDIA model is evaluated against it (`protege.roles.eval.run_nvidia_diagnostician_evaluation`).
  ARCHITECTURE.md §21: "Re-measure Diagnostician macro-F1 on the 120-item
  golden set with the actual open model" assumes a *hand-labelled* golden
  set. A real-model score against this file is a real, useful development
  signal — but it is not the roadmap's ship-gate result until the
  ratification below happens.

## What independent human ratification would still require

All of the following are currently **not done**:

1. Recruit at least one rater who did **not** author the P3 content and
   did **not** write this golden-set generator.
2. Give that rater each of the 120 `text` fields **only** — no
   `misconception_code`, no `source`, no file path that would reveal the
   authored origin.
3. The rater independently assigns one of the 8 codes, or "none/unclear",
   to each example.
4. Compute inter-rater agreement if more than one rater is used (e.g.
   Cohen's/Fleiss' kappa) — a single rater is a weaker but still
   meaningful signal; document which was done.
5. Compare the rater's labels against this file's machine-derived labels;
   resolve disagreements by discussion or by discarding the disputed
   example, not by silently keeping the machine label.
6. Record each rater's identity, date, and per-item (or per-misconception)
   agreement in a table in **this file**, the same way
   `content/math/fractions/v1/RATIFICATION.md` records its own sign-off —
   and only then may this file's status change from "NOT RATIFIED".
7. Ideally, also add examples that are **not** derived from P3's own
   authored fields at all (e.g. real or independently-written child
   transcripts) so the set is no longer "easy mode" only.

## Regenerating

```
uv run python -c "
from pathlib import Path
from protege.roles.golden_set import generate_golden_set, save_golden_set
save_golden_set(generate_golden_set(), Path('packages/roles/golden_set/diagnostician_v1.json'))
"
```

Deterministic: re-running against an unchanged
`content/math/fractions/v1/` reproduces this file byte-for-byte (modulo the
JSON key order `json.dumps` already fixes). If P3 content changes, this
file goes stale and should be regenerated and re-reviewed like any other
P3-derived artifact.
