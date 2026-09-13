# PROTÉGÉ

AI-native learning system built around **LEARN → TEACH → PROVE**: a child learns, practices,
explains, teaches Sprout, and independently proves understanding.

**Current status: P0 — Repository & Development Foundation** (see
`docs/PROTEGE_IMPLEMENTATION_ROADMAP.md`). The learning engine, FSM, Sprout, NVIDIA integration,
and product UI do **not** exist yet — by design. P0 is scaffolding, local infrastructure, CI, and
developer tooling only.

## Documentation (source of truth, in hierarchy order)

1. `docs/PROTEGE_ARCHITECTURE.md` — product decisions (v1.0)
2. `docs/PROTEGE_ENGINEERING_ADDENDUM.md` — engineering corrections (v1.1)
3. `docs/PROTEGE_IMPLEMENTATION_ROADMAP.md` — execution sequencing (v2.0)
4. `docs/DECISIONS.md` — locked residual engineering decisions (21 states, embeddings, F1 bands,
   voice latency, calendar)

## Repository layout

```
apps/web/            Next.js 15 + React 19 + TypeScript frontend (boot page only)
services/session/    FastAPI session service (/healthz, settings, logging) + Alembic
packages/contracts/  Shared Pydantic contracts (scaffold; models land in P1)
content/             Versioned learning content (lands in P3)
evals/               Evaluation harness (lands in P24)
tools/authoring/     Offline authoring (Fable-assisted; lands in P3)
infra/               Deployment infrastructure (Terraform lands in P27+)
docs/                Architecture, addendum, roadmap, decision lock
```

## Prerequisites

- **uv** (Python 3.12 + workspace deps):
  `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Node.js 20+** (22 recommended)
- **Docker Desktop** (PostgreSQL 17 + pgvector; optional Langfuse)
- **GNU make** — Windows: `winget install -e --id ezwinports.make`
- **Playwright browser** (frontend smoke test): `cd apps/web && npx playwright install chromium`

## Quickstart (clean clone)

```bash
cp .env.example .env   # API keys optional — the stack boots without them
make dev               # Postgres + Alembic baseline + API + web
```

Local ports are chosen to coexist with other projects that commonly take the
defaults (3000/3100/5432/8000 were all busy on the original dev machine):

- Backend health: <http://localhost:8300/healthz>
- Frontend: <http://localhost:3101>
- PostgreSQL (host): `localhost:5433`
- Langfuse (optional): `make observability` → <http://localhost:3200>
- Playwright e2e server: <http://localhost:3111> (test-only)

## Commands

| Command | What it does |
| --- | --- |
| `make dev` | Start the full local stack (db + migrate + api + web) |
| `make test` | Backend unit tests (pytest) |
| `make test-e2e` | Playwright smoke test (builds + starts web) |
| `make lint` | Ruff (lint + format check) + ESLint + Prettier check |
| `make typecheck` | mypy (strict) + `tsc --noEmit` |
| `make eval` | Evaluation harness — intentional no-op until P24 |
| `make db-up` / `db-down` / `db-migrate` | Compose db lifecycle / Alembic |
| `make observability` | Start Langfuse on :3200 |
| `make clean` | Remove caches and build artifacts |

## P0 exit criteria

- Clean clone works; `make dev` starts the local stack
- Backend `/healthz` responds
- Frontend boots (Next.js 15 + React 19 + TypeScript)
- PostgreSQL 17 + pgvector verified (`pgvector/pgvector:pg17`; Alembic baseline enables the
  `vector` extension)
- Backend tests, lint, strict typecheck, and the Playwright smoke test pass locally and in CI
- No secrets committed (`.env` is git-ignored; `.env.example` documents every key)

**Manual Day-0 actions that are not code** (roadmap P0 / addendum §2.3):

- Create the NVIDIA account, request the credit increase immediately (it is not instant), and
  verify real metering + rate limits at `build.nvidia.com/settings`.
- Register a second free overflow provider (quota/rate-limit insurance).
- Link this repo to a Vercel project so PRs produce preview deployments (P0 exit criterion;
  requires a Vercel account).
- The ghcr.io package namespace materializes on the first image push (later phase); the AWS OIDC
  role stub lands with Terraform (P27+).

## Deliberately absent at P0

No BKT/mastery code, no FSM, no LLM roles or NVIDIA integration, no product UI, no
Redis/SQS/EventBridge/Aurora/ALB/CloudFront, no domain contracts (P1), no content (P3). Adding any
of these before their roadmap phase is out of scope.


