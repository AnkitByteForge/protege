# Provenance — Diagnostician golden set v1 (`diagnostician_v1.json`)

**Status: NOT RATIFIED.** No human has reviewed or signed off on this file.
Nothing in `protege.roles` or its tests may set this status to ratified —
only a human editing this file does, exactly as
`content/math/fractions/v1/RATIFICATION.md` already establishes for the
underlying content pack.

## What this is

120 examples, 15 per authored misconception (`M001`–`M008`), generated
**deterministically by code**
(`protege.roles.golden_set.generate_golden_set`) from content already
authored and checked into `content/math/fractions/v1/` for roadmap P3:

| Source (per misconception) | Count | Ground-truth state | Origin file |
|---|---|---|---|
| Sprout candidate utterance | 6 | `unresolved` | `sprout_scripts.json` |
| Worked-example child explanation | 1 | `resolved` | `worked_examples/M0XX.json` |
| Item-bank distractor, templated | 8 | `unresolved` | `items/diagnostic.json` |

## What this is **not**

- **Not independently hand-labelled.** No human rater read a transcript and
  assigned a label; the ground-truth label is the label the source content
  was already authored under (the Sprout script's own
  `misconception_code`, the worked example's own diagnosis, the item
  bank's own `Distractor.maps_to`).
- **Not Fable-generated in this session.** The roadmap (P6 Data field)
  calls for a Fable-drafted-then-human-ratified golden set ($25 budget);
  no such generation or spend happened here. Reusing already-authored P3
  content is the honest alternative available without fabricating either a
  model call that did not happen or a human review that did not happen.
- **Not a substitute for the roadmap's actual gate.** ARCHITECTURE.md §21:
  "Re-measure Diagnostician macro-F1 on the 120-item golden set with the
  actual open model" — that measurement requires a real NVIDIA credential,
  excluded from this repository's default CI
  (docs/DECISIONS.md D9). See `packages/roles/tests/test_eval.py` for what
  is actually measured against this set in this repository today (the
  rule-based fallback, in isolation) and what is explicitly deferred.

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
