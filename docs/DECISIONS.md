# PROTÉGÉ — Decision Lock
### Engineering disambiguation · v1.0 · Sept 13, 2026

**Status:** Active. This document locks specific engineering decisions that remained ambiguous across v1.0 / v1.1 / v2.0. It changes **no product behavior** and re-opens **no settled decision** from the reconciliation in `PROTEGE_IMPLEMENTATION_ROADMAP.md` §1.

**Hierarchy:** Per `AGENTS.md`, this document sits in layer 2 — engineering corrections, the same tier as `PROTEGE_ENGINEERING_ADDENDUM.md` v1.1. Where it names a superseded statement in an earlier document, the statement here wins for implementation; the earlier prose stands as the historical record.

---

## D1 — Session state count: 21 (canonical)

- **Conflict.** Addendum §3.2 and §3.8 say the session statechart has "18 states"; the addendum's own reference `S` enum (§3.9) and the roadmap P7 ("`S` StrEnum of 21 states", exit criteria "all 21 states reachable") specify 21.
- **Decision.** The canonical count is **21 states** — exactly the set enumerated in the addendum §3.9 `S` StrEnum: `ARRIVAL, SPROUT_TEASE, DIAGNOSTIC, DISCOVERY, GUIDED_LEARNING, PRACTICE, EXPLANATION, SPROUT_SETUP, SPROUT_SETUP_HARD, TEACH_BACK, COACH_ASSIST, REFLECTION, INDEPENDENT_VERIFY, TRANSFER, MASTERY_DECISION, REWARD, SUMMARY, RETRIEVAL_SCHEDULE, COMPLETE, ESCALATE_TO_HUMAN, ABANDONED`.
- **Supersedes.** The "18 states" figures in addendum §3.2 and §3.8.
- **Consequence.** P7 exit criteria are unchanged. Any test, diagram, or dashboard that counts states uses 21.

## D2 — Embeddings: local `bge-small`, 384 dimensions, configuration-driven

- **Conflict.** v1.0 specifies `text-embedding-3-small` (1536-d) and hardcodes `vector(1536)` in the §22 DDL and table register; the addendum §7.2 replaces the model with local `bge-small` (384-d) but never reconciles the schema dimension.
- **Decision.**
  - Current embedding model: **local `bge-small`** (via `sentence-transformers`), per addendum §7.2. The two v1.0 RAG use cases and the "vectors never move a probability" rule are unchanged.
  - Current vector dimension: **384**.
  - The embedding model and its dimension MUST be **configuration** — a single settings source (Pydantic `BaseSettings`), consumed by the embedding worker and by the migration that creates the pgvector column. Neither value may be hardcoded in application code.
- **Supersedes.** The `vector(1536)` column definition in v1.0 §22 for implementation purposes. The v1.0 1536-d cost/config text remains valid only as the appendix cost model.
- **Consequence.** Swapping embedding models later is one config change plus an explicit re-embed migration; no code may assume 384 or 1536 literally. `bge-small` (384) is the seed value for that configuration.

## D3 — Diagnostician F1 bands

- **Conflict.** The ship gate is macro-F1 ≥ 0.75 (v1.0 §26, P6 exit), but the risk register triggers action at F1 < 0.70. Behavior between the two numbers was undefined.
- **Decision.** Measured on the 120-item golden set with the actual runtime model:
  - **≥ 0.75** — pass. Proceed; P6 exit criteria met.
  - **0.70 – 0.749** — **do not ship final diagnosis** on that configuration. Improve prompt, few-shot examples, and/or evidence representation, then re-measure. The gate is not met; the configuration is a development datapoint, not a shipping state.
  - **< 0.70** — **critical failure.** Diagnosis-dependent work does not proceed until fixed. The deterministic rule-based distractor→misconception fallback remains available for development and as the runtime fallback.
- **Consequence.** The 0.70 trigger in the risk register keeps its meaning (act immediately) without implying 0.70–0.749 is acceptable to ship.

## D4 — Voice latency: 1.3 s target, 2.0 s hard gate

- **Conflict.** v1.0 §18 targets ≤ 1.3 s perceived turn latency; roadmap P18 exit gate is ≤ 2.0 s p95; P30 restates 1.3 s target / 2.0 s gate. v1.0 also alerts at > 2 s.
- **Decision.**
  - **1.3 s** = target p95 perceived voice turn latency (aspiration).
  - **2.0 s p95** = hard acceptance gate (P18 exit).
  - **Above the gate:** voice remains **feature-flagged off** — it does not ship in the demo path until it passes. Voice stays first on the cut list.
- **Consequence.** Voice is an enhancement, never a requirement (v1.0 principle 17): the mute-child path must always complete the full loop, and removal of the voice flag must never break any path.

## D5 — Hackathon calendar: sequencing binding, dates not

- **Decision.**
  - The September 5 day-by-day schedules (v1.0 §41 and roadmap §3.4) are **not current** and must not be treated as a live plan.
  - What remains binding from them: **phase ordering, the dependency graph, scope bands, the architecture, and all exit criteria.**
  - Actual implementation scheduling is computed from **today's remaining time** at the moment work starts.
- **Consequence.** Relative effort estimates, cut-order guidance ("particles → garden variants → tutor styling → voice → transfer items → reflection screen → memory/RAG"; never cut the misconception library, Diagnostician + F1, deterministic validator, evidence chain, teach-back loop), and the risk-register triggers remain valid. Absolute dates in v1.0/roadmap prose do not.

---

## Meaning-preserving typo fixes applied

- Roadmap §1.1 table: "LlangGraph" → "LangGraph" (quote of the retracted v1.0 rationale). No meaning change.
