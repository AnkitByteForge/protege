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

## D6 — P2/P4 package homes: `packages/learning-engine` and `packages/llm` as new uv workspace members

- **Gap.** No canonical document names a directory for the roadmap P2 ("Deterministic Core") or P4 ("Provider Layer & ModelRouter") components. Roadmap P2 requires its functions to be "pure functions, no I/O, no framework coupling — **importable by tests, the service, and the eval harness alike**" (P2 Backend field). Roadmap P4 says only "`protege/llm/` package" without a parent directory.
- **Decision.**
  - `packages/learning-engine` — package `protege-learning-engine`, module `protege.learning_engine`. Owns P2's `answer_validator`, `mastery_engine`, `educational_validator`, `threshold_service`, `evidence_builder`.
  - `packages/llm` — package `protege-llm`, module `protege.llm`. Owns P4's `LLMProvider` protocol, `NvidiaProvider`, `FakeProvider`, `ModelRouter`.
  - Both are registered as `uv` workspace members alongside `services/session`, `packages/contracts`, `tools/authoring`, following the existing `packages/contracts` convention exactly (hatchling wheel build, `src/protege/<module>` layout, namespace package under `protege.*`).
- **Why this follows from the architecture.** Roadmap P24 (Evaluation Harness) will need to import the deterministic core and the provider layer without depending on FastAPI, SQLAlchemy, asyncpg, or uvicorn — those are `services/session`'s dependencies (`services/session/pyproject.toml`), not P2's or P4's. Nesting either package inside `services/session` would force `evals/` to depend on the entire session service to reuse pure math or a provider abstraction, which roadmap P2 explicitly forbids ("no framework coupling"). A sibling `packages/*` workspace member — the same shape `packages/contracts` already uses — keeps both new packages importable by the service, by `tools/authoring`, and by the future `evals/` package alike, with no framework weight.
- **Prevents.** Guessing the package location during P2/P4 implementation and having to move/rename `protege.learning_engine`/`protege.llm` later, which would touch every import site in P5–P9. It also prevents `packages/learning-engine` or `packages/llm` from accidentally acquiring a FastAPI/SQLAlchemy dependency by being co-located with the service.
- **References.** `PROTEGE_IMPLEMENTATION_ROADMAP.md` P2 ("Backend" field), P4 ("Backend" field), P24 ("Backend" field: "`evals/` package runnable as `make eval`"); `AGENTS.md` "Never create a second source of truth for state already represented elsewhere" (a nested copy of pure logic inside the service would risk exactly that).
- **Consequence.** `packages/learning-engine` and `packages/llm` exist from this point forward as empty, importable skeletons. Real P2/P4 logic and dependencies (SymPy, Hypothesis, the `openai` SDK) are added only on `feature/p2-learning` and `feature/p4-llm`, not here.

## D7 — Runtime provider policy: no concrete `AnthropicProvider` in P4

- **Conflict.** Addendum §1.3 and §9 point 4 state, without qualification: *"Anthropic is removed from the request path. The `anthropic` SDK lives only in `tools/authoring/`."* Roadmap P4's component list, however, names a concrete `AnthropicProvider (config-swap, unused at runtime)` as one of the things P4 builds inside `protege/llm/` — which would require the `anthropic` SDK as a dependency of a runtime package.
- **Decision.** P4 implements the `LLMProvider` protocol, `FakeProvider`, and `NvidiaProvider` only. **No concrete `AnthropicProvider` class ships in `packages/llm`, and `packages/llm` never depends on the `anthropic` SDK.** The protocol itself is what proves provider-swappability; a concrete second implementation is not required to demonstrate that. When production genuinely needs the swap, addendum §1.6 already describes it as "~40 lines" and P29's trigger table ("quality or compliance requires frontier models → ModelRouter config → Anthropic/Bedrock. *One file changes*") is where that class gets written, at which point it is added to whichever package needs it.
- **Why this follows from the architecture.** Per `AGENTS.md`'s document hierarchy, the Engineering Addendum (layer 2) outranks the Roadmap (layer 3) on engineering specifics. The addendum's SDK-isolation rule is unqualified and repeated twice (§1.3, §9.4); the roadmap's P4 component list is execution-sequencing detail, not a product or engineering-correction decision, and roadmap §1.2 itself only "carries forward" product decisions, not this particular engineering placement. Where the two conflict, the addendum wins.
- **Prevents.** Adding the `anthropic` SDK as a dependency of `packages/llm`, which would put a supposedly-unused runtime dependency directly in the request-path package the addendum says must never contain it — a violation that would only surface as an audit failure later, not a test failure now.
- **References.** `PROTEGE_ENGINEERING_ADDENDUM.md` §1.3, §1.6, §9 point 4; `PROTEGE_IMPLEMENTATION_ROADMAP.md` P4 (Components), P29 (Backend field); `AGENTS.md` document hierarchy.
- **Consequence.** `packages/llm`'s skeleton (and its eventual P4 implementation) declares no `anthropic` dependency. `tools/authoring` remains the sole home of that SDK, per its own docstring.

## D8 — P2's response/evidence input types stay internal until P9 defines the persisted contract

- **Gap.** `PROTEGE_ARCHITECTURE.md` §22 documents a `responses` table (scored answers: `item_id`, `raw`, `is_correct`, `hints_used`, `unaided`), but roadmap P1's entity list never included a `Response` contract, and `packages/contracts` has none today — `Evidence.payload` (`packages/contracts/src/protege/contracts/learning_state.py`) is the only place response-shaped data currently appears, as an open `dict[str, JSONValue]`.
- **Decision.** P2's `mastery_engine` and `evidence_builder` accept their own internal, non-exported input types (e.g. a local dataclass/TypedDict for a scored response) defined inside `packages/learning-engine`. These types are **not** added to `packages/contracts`. When P9 ("Persistence, Evidence Ledger, Events & Jobs") defines the canonical persisted `Response` contract per §22, P2's internal types are reconciled against it at that time — either by importing the new contract or by conversion at the P2/P9 boundary.
- **Why this follows from the architecture.** `AGENTS.md`: "Never create a second source of truth for state already represented elsewhere." Adding a `Response` contract to `packages/contracts` now, ahead of P9, would be inventing the persisted shape from P2's local needs rather than from §22's actual table definition — exactly the kind of premature, undocumented modeling this document exists to prevent. Keeping the type internal to P2 costs nothing today (P2 has no persistence) and avoids a contract that P9 would likely have to change anyway.
- **Prevents.** `packages/contracts` acquiring a `Response`/`ScoredResponse` model shaped by P2's convenience instead of by the §22 database register, which would force a breaking rename in P9 and a second migration of every P2 call site.
- **References.** `PROTEGE_ARCHITECTURE.md` §22 (`responses` table); `PROTEGE_IMPLEMENTATION_ROADMAP.md` P1 (entity list), P2 (Components: `evidence_builder`), P9 (Components: "Full schema from v1.0 §22"); `AGENTS.md` "Never create a second source of truth."
- **Consequence.** `packages/contracts` is unmodified by P2. The eventual `Response` contract is P9-owned.

## D9 — Real NVIDIA integration tests are excluded from default CI

- **Gap.** Addendum §2.3 documents a hard **40 requests-per-minute** cap and a finite, exhaustible credit allowance ("your evaluation suite alone... consumes 300+" of a ~1,000-credit signup grant); roadmap P4's exit criterion requires "a round-trip call to a real NVIDIA model returns a schema-valid object" to be demonstrated, but no document says this call may run unconditionally in CI on every push/PR.
- **Decision.** Any test that performs a real network call to the NVIDIA endpoint is marked (e.g. a dedicated pytest marker such as `integration` or `external`) and is **excluded from the default `pytest` run** used by `make test` and the CI `backend` job (`.github/workflows/ci.yml`). It is invoked manually, or by an explicitly separate, deliberately-triggered job, never automatically on every commit.
- **Why this follows from the architecture.** Addendum §2.8's failure taxonomy and §2.3's mitigations ("Never demo with concurrent live users," "Cache every eval result to disk keyed by prompt hash") both treat the rate limit and credit budget as scarce, shared, easily-exhausted resources. `.github/workflows/ci.yml` currently runs `uv run pytest` unconditionally on every push to `main` and every pull request (`on: push/pull_request`); an unmarked real-model test would burn credits and risk the 40 RPM ceiling on every commit and every concurrent PR, which addendum §2.3's Day-1 action list is explicitly trying to protect against.
- **Prevents.** CI silently exhausting the NVIDIA credit allowance or tripping the 40 RPM limiter across concurrent PR runs, which addendum §2.3 identifies as a critical, build-ending risk (roadmap §3.3 risk register: "NVIDIA credits exhausted mid-build — Critical").
- **References.** `PROTEGE_ENGINEERING_ADDENDUM.md` §2.3, §2.8; `PROTEGE_IMPLEMENTATION_ROADMAP.md` P4 (Testing, exit criteria), §3.3 risk register; `.github/workflows/ci.yml` (`on: push/pull_request` triggers).
- **Consequence.** P4's real-model round-trip check is written but excluded from `[tool.pytest.ini_options]` default collection (or gated behind an explicit marker/opt-in flag) when P4 lands. This decision does not itself add the test — it constrains how P4 must add it.

## D10 — UNRESOLVED: Elo update formula and Bayesian zero-likelihood handling are not specified

- **Status: OPEN. Do not implement against this entry — it records a gap, not a decision.**
- **Gap 1 — Elo.** `PROTEGE_ARCHITECTURE.md` §10.2 says only "Elo item difficulty, updated online (no cold-start item calibration needed)" and lists it as "Use from day 1." No document anywhere (Architecture, Addendum, Roadmap, this file) specifies a K-factor, an expected-score function, or when/how the update fires relative to a response.
- **Gap 2 — Bayesian misconception update.** §10.2 gives `P(M_k | d) ∝ P(d | M_k) · P(M_k)`, with `P(d | M_k)` authored per misconception (`Misconception.distractor_likelihood` in `packages/contracts`). No document specifies behavior when an observed distractor `d` has no authored entry in `distractor_likelihood` (a zero or missing likelihood), which is a real case: `packages/contracts` models `distractor_likelihood` as an open `dict[str, Probability]` with no completeness constraint.
- **Decision.** None. Per the task instruction that produced this entry, P2 implementation **must not proceed with undocumented behavior** for either gap. A concrete choice (see the decision brief below) must be locked here, as a dated addition to this entry, before `feature/p2-learning`'s `mastery_engine` module is written.
- **References.** `PROTEGE_ARCHITECTURE.md` §10.2; `packages/contracts/src/protege/contracts/content.py` (`Misconception.distractor_likelihood`); `packages/contracts/src/protege/contracts/ids.py` (`EloRating`, `Probability`).

---

## Meaning-preserving typo fixes applied

- Roadmap §1.1 table: "LlangGraph" → "LangGraph" (quote of the retracted v1.0 rationale). No meaning change.
