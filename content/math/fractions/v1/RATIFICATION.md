# Human ratification — content/math/fractions/v1

**Status: NOT RATIFIED.**

Machine validation (`protege-authoring validate`, `manifest.json`) checks
schema validity, ID uniqueness, misconception-code and distractor mappings,
prerequisite-graph consistency, answer leakage, Sprout constraints,
intervention linkage, transfer-item correctness, required counts,
representation coverage, and WorkedExample validation. It does **not**
constitute pedagogical review, and no code path in `tools/authoring` may set
this file's status — only a human editing this file does.

Passing machine validation is a precondition for review, not a substitute
for it.

## What a reviewer should check per misconception

- `cognitive_origin` is a defensible, non-fabricated account of why children
  make this error (see each misconception's `citation` field for the body of
  literature it draws on).
- The 6 Sprout candidate utterances are age-appropriate (Grade 3 reading
  level — pending the P2 `educational_validator` gate, see
  `tools/authoring/src/protege/authoring/p2_adapter.py`), in character (a
  confused peer, never an authority), and pedagogically faithful to the
  misconception (not a caricature).
- The 3 interventions describe real, workable classroom/tutor strategies —
  not just plausible-sounding scripts.
- The 4 diagnostic items and 2 transfer items are mathematically correct
  (every `correct_answer` is actually correct; every distractor is a
  genuine, predictable wrong answer for a child holding this misconception,
  not an arbitrary wrong value).
- The worked example's narrated child explanation is realistic for the
  stated grade band.
- `distractor_likelihood_if_not_misconception` (added per docs/DECISIONS.md
  D13, the independent-Bernoulli Bayes update) is a genuine, independently
  reasoned `P(d | not M_k)` judgment for each behavior key — not a
  mechanical transform of `distractor_likelihood` and not a reuse of its
  `"other"` value (machine-checked: `complement_likelihood` validator rule).
  See the inline rationale comment above each misconception's complement
  table in `tools/authoring/src/protege/authoring/seed_fractions_v1.py` for
  the specific reasoning, including the one deliberate exception (M003's
  `says_equal`, where the complement value exceeds the primary value —
  documented in-line as intentional, not an error).

## Sign-off

| Misconception | Reviewer | Date | Notes |
|---|---|---|---|
| M001 | _unreviewed_ | | |
| M002 | _unreviewed_ | | |
| M003 | _unreviewed_ | | |
| M004 | _unreviewed_ | | |
| M005 | _unreviewed_ | | |
| M006 | _unreviewed_ | | |
| M007 | _unreviewed_ | | |
| M008 | _unreviewed_ | | |

This content is **not** to be served to a real learner until every row above
is signed off.
