# PROTÉGÉ — ZCode Project Instructions

## Source of truth

Read these documents before making architectural changes:

- docs/PROTEGE_ARCHITECTURE.md
- docs/PROTEGE_ENGINEERING_ADDENDUM.md
- docs/PROTEGE_IMPLEMENTATION_ROADMAP.md

Hierarchy:

1. Product decisions from PROTEGE_ARCHITECTURE.md
2. Engineering corrections from PROTEGE_ENGINEERING_ADDENDUM.md
3. Execution sequencing from PROTEGE_IMPLEMENTATION_ROADMAP.md

The engineering addendum supersedes conflicting engineering decisions in v1.0.

## Product

PROTÉGÉ is an AI-native learning system built around:

LEARN → TEACH → PROVE

The child:
1. learns
2. practices
3. explains
4. teaches Sprout
5. independently proves understanding

The product must feel like a coherent learning world, not a chatbot or developer demo.

## Architecture

Frontend:
- Next.js
- React
- TypeScript
- Tailwind
- Motion
- SVG-based interactions

Backend:
- Python
- FastAPI
- Pydantic
- SQLAlchemy
- PostgreSQL
- pgvector

Session orchestration:
- Plain Python FSM
- Server is authoritative
- Frontend mirrors state but never decides learning transitions

AI:
- ModelRouter
- LLMProvider abstraction
- NVIDIA runtime inference
- openai-python client for NVIDIA-compatible API
- Fable is development-only

Learning:
- BKT
- misconception Bayesian beliefs
- Elo
- FSRS
- deterministic validators

## Non-negotiable principles

- LLM proposes; deterministic systems verify.
- LLM must never directly determine mastery.
- LLM must never directly determine verification.
- LLM must never directly determine reward eligibility.
- LLM must never directly determine session transitions.
- Independent verification is LLM-free.
- Mastery decision is LLM-free.
- Structured learner state is authoritative.
- Vector memory never changes mastery probabilities.
- Parent-facing claims must resolve to evidence.
- Child-facing language must remain age appropriate.
- Failures should degrade gracefully.
- Preserve the distinction between product identity and reusable infrastructure.

## Coding rules

- Do not modify main directly.
- Work on feature branches.
- Inspect existing files before changing them.
- Prefer the existing architecture.
- Do not introduce a new framework, datastore, provider, or major abstraction without explaining why.
- Avoid unrelated refactors.
- Keep changes small and reviewable.
- Update tests whenever behavior changes.
- Run relevant tests before declaring work complete.
- Never commit secrets.
- Never create a second source of truth for state already represented elsewhere.

## Implementation workflow

For substantial tasks:

1. Read the relevant architecture sections.
2. Inspect the existing implementation.
3. State the intended changes.
4. Implement the smallest coherent change.
5. Run tests and validation.
6. Inspect git diff.
7. Report what changed and anything unresolved.

Do not start the next roadmap phase unless explicitly instructed.

## AI development workflow

Runtime providers:
- NVIDIA
- Deepgram
- Cartesia

Development tools:
- ZCode / GLM-5.3

- ChatGPT


Use model output only inside its bounded role.
Do not allow model-generated routing or mastery decisions to become authoritative.

## UX

The child experience is a first-class system.

Prioritize:
- warmth
- curiosity
- continuity
- tactile interaction
- accessibility
- expressive Sprout behavior
- coherent transitions
- graceful failure
- evidence-backed progression

Do not make the UI feel like a chatbot, form, dashboard, or generic AI tutor.

## Git

Before finalizing a task:

git status
git diff
tests
lint/typecheck as applicable

Use Conventional Commit messages.

Never push directly to main.