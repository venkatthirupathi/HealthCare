# AceIQ Health — Claude Code project context

You are helping the user build **AceIQ Health**, a full-stack AI-native
application: a drug-information and clinical-evidence assistant for medical
students and junior doctors.

## How to work on this project

1. **Read `PROJECT_BRIEF.md` first.** It is the single source of truth. Every
   technical decision, file path, API contract, and prompt template is in
   there. Do not improvise where the brief is explicit.

2. **Read `JD_CONTEXT.md` for motivation.** This project is a portfolio piece
   for the Cognizant Ace Team graduate role. The brief is structured to map
   onto the specific skills the JD lists. Keep that mapping intact.

3. **Work in phases.** The brief defines 4 phases:
   - **Phase 0** — Repo setup, Docker, Postgres+pgvector, CI scaffolding
   - **Phase 1** — RAG vertical slice: ingest → embed → retrieve → answer → cite
   - **Phase 2** — Safety: PII redaction, intent refusal, post-hoc verifier
   - **Phase 3** — Eval framework: 12-question suite + metrics dashboard
   - **Phase 4** — Streamlit demo UI + audit log + observability hooks

   Default to **Phase 0 + 1 + 2 + 3 + 4** in one shot unless the user asks
   otherwise. Later phases (multi-agent, React, Java auth gateway, K8s) are
   in the brief's "Roadmap" section and explicitly out of scope for v1.

4. **Use the data in `sample_data/`.** Do not download anything. The three
   synthetic XML files are sufficient to exercise every code path.

5. **Verify with `eval/questions.json`.** When you finish Phase 3, run the
   eval set and show the user the metrics table. This is your acceptance
   test.

## Coding conventions

- **Python 3.10+** with type hints everywhere. Use `from __future__ import
  annotations`.
- **Pydantic v2** for all request/response schemas and settings.
- **SQLAlchemy 2.0** style (`Mapped`, `mapped_column`, not legacy `Column`).
- **FastAPI** with router-per-resource pattern (one router file per logical
  resource).
- **No global state.** Use FastAPI `Depends` for DB sessions, settings, etc.
- **No `print`** — use `logging` or `structlog`.
- **Tests via `pytest`** in a top-level `tests/` directory.
- **Lint with `ruff`** — `make lint` should pass before "done".
- **Format with `ruff format`** (or `black` if you prefer; pick one).
- **Imports**: standard lib → third party → local, separated by blank lines.
- **Docstrings** on every public function and class. One-line summary plus
  a "Why" sentence if the choice isn't obvious.

## Stack constraints (do not deviate without asking)

- Postgres 16 with `pgvector` and `pg_trgm` (run via docker-compose)
- `sentence-transformers/all-MiniLM-L6-v2` for embeddings (384 dim, local)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` for reranking
- LLM: Anthropic primary (model `claude-sonnet-4-6`), OpenAI fallback
  (`gpt-4o-mini`). Light model for verifier: `claude-haiku-4-5-20251001`.
- Streamlit for the demo UI (React comes later)

## Things to refuse

- **Do not use LLM-based PII detection in v1.** Use regex. The brief explains
  why — auditability and speed.
- **Do not add a real auth system in v1.** The auth gateway is Phase 6 in the
  roadmap. v1 endpoints are unauthenticated.
- **Do not skip the eval suite.** It is the project's main quality signal.
- **Do not use vibes-based completion.** "Done" means `make test` passes,
  `make lint` passes, `make eval` produces metrics above target.

## When in doubt

- File path conflict? Follow the file tree in `PROJECT_BRIEF.md`.
- Prompt template question? Use the exact prompts in `PROJECT_BRIEF.md`
  section "Prompt Templates".
- Acceptance criteria question? See `PROJECT_BRIEF.md` section "Phase
  acceptance criteria".
- Anything else? Ask the user.
