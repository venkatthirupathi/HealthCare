# AceIQ Health — Project Brief

**Read this end-to-end before writing any code.** Every decision is here.

---

## 1. Problem statement

Medical students and junior doctors in teaching hospitals frequently need to
look up drug information — dosing, contraindications, interactions, adverse
reactions. They reach for UpToDate, Lexicomp, BNF, or just Google. The results
are slow, paywalled, or unreliable.

**AceIQ Health** is an AI-native reference assistant that answers grounded,
cited questions about drug labels in 2–3 seconds. It is explicitly **not a
clinical decision-support system** — it refuses prescribing-decision
questions and routes users back to clinical judgement.

### Primary user

A junior resident in a tertiary-care hospital, asking questions like:

- "What is the renal dosing for vancomycin?"
- "Can atorvastatin be used during pregnancy?"
- "What are the contraindications for metformin?"

### Non-users (out of scope for v1)

- Patients seeking self-diagnosis
- Pharmacists doing dispensing checks
- Anyone needing prescription-writing assistance

### Why this project

This is a portfolio project for the **Cognizant Ace Team — Full Stack AI
Engineer** graduate role. The architecture is designed to demonstrate
*every* skill listed in the JD: Python, REST APIs, SQL, RAG, prompt
engineering, structured outputs, LLM orchestration, vector DB concepts,
evaluation metrics, monitoring, guardrails, cost optimization, fallback
strategies, FastAPI, containers, CI/CD, event-driven architectures.

See `JD_CONTEXT.md` for the full role description.

---

## 2. What v1 delivers (this brief)

v1 = "Week 1–2 vertical slice." A complete, runnable system that:

1. Ingests drug labels (FDA SPL XML format) into a vector database
2. Answers natural-language questions via hybrid retrieval + LLM generation
3. Cites the source section for every claim
4. Redacts PII before any LLM call
5. Refuses prescribing-decision questions
6. Verifies each answer is grounded in retrieved sources
7. Logs every query for audit and eval
8. Comes with a Streamlit demo UI and a 12-question eval suite

v2 features (multi-agent LangGraph, React frontend, Java auth gateway,
Kubernetes deployment, RAGAS integration) are described in section 14
"Roadmap" but **not in scope for v1**.

---

## 3. Tech stack

| Layer            | Choice                                              | Version    |
|------------------|-----------------------------------------------------|------------|
| Language         | Python                                              | 3.10+      |
| Web framework    | FastAPI                                             | 0.115.x    |
| ORM              | SQLAlchemy                                          | 2.0.x      |
| DB               | Postgres + pgvector + pg_trgm                       | pg 16      |
| Embeddings       | sentence-transformers/all-MiniLM-L6-v2 (local)      | 3.x        |
| Reranker         | cross-encoder/ms-marco-MiniLM-L-6-v2 (local)        | —          |
| LLM (primary)    | Anthropic Claude (model: `claude-sonnet-4-6`)       | SDK 0.39+  |
| LLM (light)      | Anthropic (model: `claude-haiku-4-5-20251001`)       | —          |
| LLM (fallback)   | OpenAI `gpt-4o-mini`                                | SDK 1.51+  |
| Demo UI          | Streamlit                                           | 1.39.x     |
| XML parsing      | lxml                                                | 5.x        |
| Config           | pydantic-settings                                   | 2.x        |
| Tests            | pytest                                              | 8.x        |
| Lint             | ruff                                                | 0.6.x      |
| Containers       | Docker + docker-compose                             | —          |

**Why these choices** — short version:

- **pgvector over Pinecone/Weaviate**: one DB to operate, free, sufficient
  for <10M vectors.
- **Local embeddings**: free, fast on CPU, no per-query cost. Frontier
  models are only worth it for generation.
- **Anthropic primary, OpenAI fallback**: demonstrates explicit "fallback
  and degradation strategies" from the JD.
- **Streamlit for demo**: ships in hours; React replaces it in v2.
- **No LangChain in v1**: keeps the LLM layer thin and debuggable.
  LangGraph comes in v2 for the multi-agent flow.

---

## 4. Architecture

```
   ┌──────────────────────┐
   │ Streamlit demo UI    │   (placeholder for React in v2)
   └──────────┬───────────┘
              │  HTTP / JSON
   ┌──────────▼───────────┐
   │ FastAPI backend      │
   │                      │
   │  ┌────────────────┐  │
   │  │ /api/v1/query  │  │ ──► guardrails ──► retrieval ──► LLM ──► verifier ──► log
   │  └────────────────┘  │
   │  ┌────────────────┐  │
   │  │ /api/v1/docs   │  │ ──► async ingest job ──► parse → chunk → embed → store
   │  └────────────────┘  │
   │  ┌────────────────┐  │
   │  │ /health        │  │
   │  └────────────────┘  │
   └──────────┬───────────┘
              │
   ┌──────────▼───────────┐         ┌────────────────────┐
   │ Postgres 16          │◄────────│ LLM provider chain │
   │ + pgvector           │         │  1) Anthropic      │
   │ + pg_trgm            │         │  2) OpenAI         │
   │                      │         │  3) Retrieval-only │
   │  Tables:             │         └────────────────────┘
   │   documents          │
   │   chunks (+ vec idx) │
   │   jobs               │
   │   query_logs         │
   └──────────────────────┘
```

### Query flow (end-to-end, single request)

1. POST `/api/v1/query` arrives with `{ question: str, filters?: dict }`
2. **PII redaction**: regex masks names, emails, phones, Aadhaar, PAN, MRN, DOB
3. **Intent detection**: regex checks for prescribing-decision phrasing →
   refuse with a clinical-judgement reminder if matched
4. **Retrieval**: question embedded with sentence-transformers; vector top-8
   + trigram top-8 fused via Reciprocal Rank Fusion (RRF); top-3 reranked
   with cross-encoder
5. **Generation**: top-3 chunks formatted into a structured prompt; Anthropic
   primary call (falls back to OpenAI if Anthropic fails, then to
   "retrieval-only" mode if no provider works)
6. **Verifier**: cheap second LLM call scores grounding 0–1 against the
   retrieved chunks
7. **Audit log**: every field above written to `query_logs`
8. Response returned: `{ answer, citations[], model_used, verifier_score,
   latency_ms, disclaimer }`

---

## 5. File structure (exact)

Create this layout exactly. Do not invent new directories.

```
aceiq-health/
├── README.md
├── ARCHITECTURE.md
├── ROADMAP.md
├── CLAUDE.md
├── .env.example
├── .gitignore
├── Makefile
├── requirements.txt
├── docker-compose.yml
├── backend/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app entrypoint
│   ├── config.py                        # pydantic-settings
│   ├── db.py                            # SQLAlchemy engine + session
│   ├── models.py                        # ORM models
│   ├── schemas.py                       # Pydantic request/response
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py                    # GET  /health
│   │   ├── documents.py                 # GET  /api/v1/documents
│   │   │                                # POST /api/v1/documents/upload
│   │   ├── jobs.py                      # GET  /api/v1/jobs/{id}
│   │   └── query.py                     # POST /api/v1/query
│   ├── services/
│   │   ├── __init__.py
│   │   ├── parser.py                    # SPL XML → ParsedLabel
│   │   ├── chunker.py                   # ParsedLabel → list[ChunkOut]
│   │   ├── embeddings.py                # local embedding wrapper
│   │   ├── retrieval.py                 # hybrid + RRF + rerank
│   │   ├── llm.py                       # provider chain with fallback
│   │   ├── guardrails.py                # PII + intent refusal
│   │   └── verifier.py                  # post-hoc grounding check
│   └── jobs/
│       ├── __init__.py
│       └── ingest.py                    # parse → chunk → embed → persist
├── streamlit_app/
│   └── app.py                           # demo UI
├── scripts/
│   ├── __init__.py
│   ├── init.sql                         # CREATE EXTENSION vector, pg_trgm
│   └── seed.py                          # load sample_data into DB
├── sample_data/
│   ├── README.md
│   ├── metformin.xml                    # (provided in this brief)
│   ├── atorvastatin.xml                 # (provided in this brief)
│   └── amoxicillin.xml                  # (provided in this brief)
├── eval/
│   ├── __init__.py
│   ├── README.md
│   ├── questions.json                   # (provided in this brief)
│   └── run_eval.py                      # runs the suite, prints metrics
└── tests/
    ├── __init__.py
    ├── test_parser.py
    ├── test_chunker.py
    └── test_guardrails.py
```

---

## 6. Database schema

Four tables. Use SQLAlchemy 2.0 mapped style with `Mapped[...]` and
`mapped_column(...)`.

### `documents`
| Column        | Type           | Notes                                       |
|---------------|----------------|---------------------------------------------|
| id            | UUID           | primary key                                 |
| source        | varchar(64)    | `'dailymed'` \| `'pubmed'` \| `'upload'`    |
| external_id   | varchar(128)   | upstream ID (DailyMed setId, etc.)          |
| title         | varchar(512)   |                                             |
| drug_name     | varchar(256)   | nullable, indexed                           |
| meta          | JSON           | section count, ingest timestamp, etc.       |
| created_at    | timestamptz    |                                             |

Unique constraint on `(source, external_id)` — ingestion is idempotent.

### `chunks`
| Column         | Type              | Notes                              |
|----------------|-------------------|------------------------------------|
| id             | UUID              | primary key                        |
| document_id    | UUID FK           | → documents.id, cascade delete     |
| section        | varchar(128)      | e.g. `'Contraindications'`         |
| section_order  | integer           |                                    |
| text           | text              |                                    |
| embedding      | vector(384)       | pgvector                           |
| created_at     | timestamptz       |                                    |

GIN trigram index on `text`. IVFFlat index on `embedding` built post-seed
(needs data to cluster).

### `jobs`
| Column      | Type          | Notes                                       |
|-------------|---------------|---------------------------------------------|
| id          | UUID          | primary key                                 |
| kind        | varchar(64)   | `'ingest_spl'`                              |
| status      | varchar(32)   | `'queued'` \| `'running'` \| `'done'` \| `'failed'` |
| payload     | JSON          |                                             |
| result      | JSON          |                                             |
| error       | text          | nullable                                    |
| created_at  | timestamptz   |                                             |
| updated_at  | timestamptz   | auto-update on change                       |

### `query_logs`
| Column                | Type           | Notes                              |
|-----------------------|----------------|------------------------------------|
| id                    | UUID           | primary key                        |
| question              | text           | raw input                          |
| redacted_question     | text           | after PII redaction                |
| answer                | text           |                                    |
| refused               | boolean        | true if guardrail refused          |
| refusal_reason        | varchar(256)   | nullable                           |
| model_used            | varchar(128)   | e.g. `'claude-sonnet-4-6'`         |
| provider_used         | varchar(32)    | `'anthropic'` \| `'openai'` \| `'none'` \| `'guardrail'` |
| retrieved_chunk_ids   | JSON (list)    | strings                            |
| verifier_score        | float          | 0–1, nullable                      |
| latency_ms            | integer        |                                    |
| tokens_in             | integer        |                                    |
| tokens_out            | integer        |                                    |
| created_at            | timestamptz    | indexed                            |

---

## 7. API contracts

All paths are exact. Pydantic v2 models. All responses are JSON.

### `GET /health`

```json
{
  "status": "ok",
  "app_env": "development",
  "has_anthropic": true,
  "has_openai": false,
  "document_count": 3,
  "chunk_count": 47
}
```

### `GET /api/v1/documents`

Returns list of `DocumentSummary`:

```json
[
  {
    "id": "uuid",
    "source": "dailymed",
    "external_id": "metformin",
    "title": "Metformin Hydrochloride Tablets",
    "drug_name": "Metformin",
    "created_at": "2026-..."
  }
]
```

### `POST /api/v1/documents/upload`

Multipart form upload, `.xml` only. Creates a `Job`, runs ingestion in a
FastAPI `BackgroundTasks`, returns the job. Poll `/api/v1/jobs/{id}`.

### `GET /api/v1/jobs/{job_id}`

Returns `{ id, kind, status, result, error, created_at, updated_at }`.

### `POST /api/v1/query`

Request:
```json
{
  "question": "What is the renal dosing for metformin?",
  "filters": { "drugs": ["metformin"] }  // optional
}
```

Response:
```json
{
  "answer": "Metformin is contraindicated when eGFR is below 30 mL/min/1.73m² [Contraindications]...",
  "refused": false,
  "refusal_reason": null,
  "citations": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "drug_name": "Metformin",
      "section": "Contraindications",
      "source": "dailymed",
      "external_id": "metformin",
      "excerpt": "Metformin hydrochloride is contraindicated in patients with..."
    }
  ],
  "model_used": "claude-sonnet-4-6",
  "provider_used": "anthropic",
  "verifier_score": 0.92,
  "latency_ms": 1850,
  "disclaimer": "Educational reference only; not clinical advice. Verify against primary sources before patient care."
}
```

When the guardrail refuses, return the same shape with `refused: true`,
`answer` = the refusal message, `refusal_reason` populated, empty
`citations`, `model_used: "refusal"`, `provider_used: "guardrail"`.

---

## 8. Prompt templates (use verbatim)

### 8.1 Answer generation system prompt

```
You are AceIQ Health, a clinical reference assistant for medical students
and junior doctors. You answer questions using ONLY the drug-label and
clinical evidence excerpts provided to you.

Rules — non-negotiable:
1. Answer strictly from the provided excerpts. If the excerpts do not
contain the answer, say so explicitly. Do not use outside knowledge.
2. Cite the section name (in square brackets) for every clinical claim
you make. Example: "Metformin is contraindicated in patients with
eGFR <30 mL/min/1.73m² [Contraindications]."
3. Never provide individualized prescribing advice. If asked "what
should I prescribe for patient X," redirect to the label excerpts and
remind the user to consult appropriate clinical judgement.
4. Use precise clinical language. Do not soften factual
contraindications or warnings to be reassuring.
5. Keep answers concise — typically 3–6 sentences. Bullet points are fine
for lists of adverse reactions or contraindications.
6. End every answer with: "Source: drug labels and provided excerpts only."
```

### 8.2 Answer generation user message format

```
Drug-label excerpts:

[Excerpt 1 — drug: <drug_name>, section: <section>]
<chunk text>

[Excerpt 2 — drug: <drug_name>, section: <section>]
<chunk text>

...

---
Question: <user question after PII redaction>

Answer using only the excerpts above. Cite section names in [brackets].
If the answer is not in the excerpts, say "The provided excerpts do not
address this question."
```

### 8.3 Verifier system prompt

```
You are a strict fact-checker. You are given:
  (A) drug-label EXCERPTS
  (B) an ANSWER generated from those excerpts

Score the ANSWER on grounding from 0.0 to 1.0:
  - 1.0 = every clinical claim in the ANSWER is directly supported by
    the EXCERPTS
  - 0.5 = roughly half is supported, the rest is plausible-but-unsupported
  - 0.0 = the ANSWER contains specific claims contradicted by or absent
    from EXCERPTS

Respond with ONLY a JSON object:
  {"score": 0.0-1.0, "unsupported": ["..."], "reason": "<one sentence>"}
No prose, no markdown, no code fences.
```

---

## 9. Safety guardrails

### 9.1 PII patterns (regex, in `services/guardrails.py`)

| Label      | Pattern                                                                 |
|------------|-------------------------------------------------------------------------|
| EMAIL      | `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`                        |
| PHONE      | `(?<!\d)(?:\+?\d{1,3}[\s-]?)?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}(?!\d)` |
| AADHAAR    | `\b\d{4}\s?\d{4}\s?\d{4}\b`                                              |
| PAN        | `\b[A-Z]{5}\d{4}[A-Z]\b`                                                 |
| MRN        | `\bMRN[:\s#-]*\d{4,10}\b` (case-insensitive)                            |
| DOB        | `\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b`                                      |

Plus a "name after trigger word" pattern:

```
\b(?:patient|mr|mrs|ms|dr|doctor|name(?:d)?|called)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b
```

Replace each match with `[REDACTED:LABEL]`. For the name pattern, keep
the trigger word ("patient", "Mr", etc.) and redact only the name.

### 9.2 Prescribing-intent patterns (refuse these queries)

```python
[
    r"\bwhat (?:should|do) (?:i|we) (?:prescribe|give|order|recommend)\b",
    r"\bbest (?:drug|antibiotic|medication|treatment) for\b",
    r"\b(?:can|should) i (?:start|give|switch|stop)\b",
    r"\bdiagnose|diagnosis for\b",
    r"\bmy patient (?:has|is|with)\b",
]
```

All case-insensitive. If any matches, refuse with:

> "This appears to be a prescribing-decision question. AceIQ Health is a
> reference tool, not a clinical decision-support system. Try rephrasing as
> a label-lookup question, e.g. 'What does the metformin label say about
> renal dosing?'"

### 9.3 Disclaimer

Append to every answer (including refusals):

> *Educational reference only; not clinical advice. Verify against primary
> sources before patient care.*

---

## 10. Configuration (`.env.example`)

```
# Database
DATABASE_URL=postgresql+psycopg://aceiq:aceiq@localhost:5432/aceiq

# LLM providers (at least one recommended; system runs in retrieval-only mode if both empty)
ANTHROPIC_API_KEY=
OPENAI_API_KEY=

# Model routing
PRIMARY_MODEL=claude-sonnet-4-6
LIGHT_MODEL=claude-haiku-4-5-20251001
FALLBACK_PROVIDER=openai
FALLBACK_MODEL=gpt-4o-mini

# Embeddings (local, no API key needed)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIM=384

# Retrieval
TOP_K_RETRIEVE=8
TOP_K_RERANK=3
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
USE_RERANKER=true

# Safety
ENABLE_PII_REDACTION=true
ENABLE_VERIFIER=true
REFUSE_PRESCRIBING_QUERIES=true

# App
APP_ENV=development
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:8501
```

---

## 11. Phased build plan + acceptance criteria

### Phase 0 — Foundation (~2 hours)

**Deliverables**:
- Repo structure exactly per section 5
- `requirements.txt` with pinned versions
- `docker-compose.yml` with pgvector image
- `scripts/init.sql` enabling `vector` + `pg_trgm` extensions
- `Makefile` with all targets (install, up, down, seed, api, ui, eval, test, lint, clean)
- `.env.example`, `.gitignore`
- `backend/config.py` (pydantic-settings)
- `backend/db.py` (engine + session)
- Empty (but importable) modules in `backend/`, `tests/`

**Acceptance**:
- `make up` starts Postgres and the container is healthy
- `psql` into the DB shows `vector` and `pg_trgm` extensions installed
- `python -c "from backend.config import get_settings; get_settings()"` works

### Phase 1 — RAG vertical slice (~4 hours)

**Deliverables**:
- `models.py`, `schemas.py`
- `services/parser.py` parses the 3 sample XML files
- `services/chunker.py` produces section-aware chunks
- `services/embeddings.py` wraps sentence-transformers, lazy load
- `services/retrieval.py` does hybrid + RRF + rerank
- `services/llm.py` provider chain with fallback to retrieval-only mode
- `jobs/ingest.py` parse → chunk → embed → persist
- `routes/health.py`, `routes/documents.py`, `routes/jobs.py`, `routes/query.py`
- `main.py` wires everything up
- `scripts/seed.py` loads `sample_data/*.xml` into the DB

**Acceptance**:
- `make seed` ingests 3 documents and ~30–50 chunks
- `GET /health` returns counts > 0
- `POST /api/v1/query` with `{"question": "renal dosing for metformin"}` returns ≥1 citation with section `"Contraindications"` or `"Dosage and Administration"`
- Running with no API keys returns retrieval-only mode with raw chunk excerpts (no crash)

### Phase 2 — Safety layer (~2 hours)

**Deliverables**:
- `services/guardrails.py` with all PII patterns and intent detection from section 9
- `services/verifier.py` with the verifier prompt from section 8.3
- `routes/query.py` wires both into the query flow
- `tests/test_guardrails.py` covering each PII pattern + intent case

**Acceptance**:
- `make test` passes
- A query containing "Aadhaar 1234 5678 9012" never has those digits reach the LLM (verify via `query_logs.redacted_question` field)
- "What should I prescribe for UTI in pregnancy?" returns `refused: true`
- When API keys are present, `verifier_score` is between 0.0 and 1.0 on every non-refused query

### Phase 3 — Eval framework (~2 hours)

**Deliverables**:
- `eval/questions.json` (copy from this brief's `eval/questions.json`)
- `eval/run_eval.py` that POSTs each question against `/api/v1/query`
  and prints a metrics table
- `eval/README.md` documenting metrics and how to interpret them

**Acceptance**:
- `make eval` runs without errors against a running API
- Output includes the 6 metrics from section 12
- All 12 questions return either a valid answer or a valid refusal

### Phase 4 — Demo UI + audit (~2 hours)

**Deliverables**:
- `streamlit_app/app.py` with:
  - Sidebar showing system health and 7 sample questions (clickable)
  - Main pane: input box, answer display, metrics row, citation expanders
  - Disclaimer prominently shown
- `query_logs` writes confirmed on every request (refusals included)
- `README.md`, `ARCHITECTURE.md`, `ROADMAP.md` populated

**Acceptance**:
- `make ui` opens Streamlit at `:8501`
- Clicking a sample question populates the input and returns an answer
- After running 5 queries, `SELECT COUNT(*) FROM query_logs` returns 5
- README's quickstart actually works on a fresh clone

---

## 12. Eval metrics

`eval/run_eval.py` must compute and display these six metrics:

| Metric                | Formula                                                              | Target (v1) |
|-----------------------|----------------------------------------------------------------------|-------------|
| Retrieval drug match  | fraction of questions where the expected drug appears in citations   | ≥ 90%       |
| Section match         | fraction where ≥1 expected section appears in citations              | ≥ 80%       |
| Must-mention coverage | average fraction of `must_mention` terms found in the answer text    | ≥ 75%       |
| Refusal correctness   | fraction where `refused == should_refuse`                            | 100%        |
| Avg verifier score    | mean of verifier_score across non-refused questions                  | ≥ 0.75      |
| Avg latency           | mean of latency_ms across all questions                              | ≤ 3000 ms   |

If any metric is below target after Phase 3, the project is **not done**.

---

## 13. The exact files to copy

In this briefing folder:

- `sample_data/*.xml` (3 files) → copy to project's `sample_data/` directory
- `eval/questions.json` (1 file) → copy to project's `eval/` directory
- `CLAUDE.md` → copy to project root (so future Claude Code sessions
  auto-load context)

Do not modify the sample XML or the eval questions during Phase 1–4. They
are the project's ground truth.

---

## 14. Roadmap (out of scope for v1)

These are the v2/v3 phases. Document them in `ROADMAP.md` but **do not build
them** unless the user asks.

- **Phase 5** — LangGraph multi-agent layer (planner → retriever → writer → critic)
- **Phase 6** — Java/.NET auth gateway (Spring Boot or ASP.NET Core, JWT)
- **Phase 7** — React + TypeScript frontend (replaces Streamlit)
- **Phase 8** — Streaming responses (SSE) + semantic cache + model router
- **Phase 9** — Event-driven ingestion via Redis Streams + dedicated worker
- **Phase 10** — Observability (Langfuse traces + Prometheus + Grafana)
- **Phase 11** — CI/CD (GitHub Actions: lint + tests + eval-on-PR)
- **Phase 12** — Kubernetes deployment (Helm chart, EKS or AKS)
- **Phase 13** — Indian-context corpus (ICMR guidelines, CDSCO data)

Each phase is roughly one week of work.

---

## 15. What to do when stuck

- **The brief is ambiguous?** Pick the simpler option and document the
  choice in `ARCHITECTURE.md`.
- **The brief contradicts itself?** Ask the user.
- **A library doesn't work as expected?** Read its current docs (you may
  have a stale version pinned — update `requirements.txt` and document
  why).
- **The eval doesn't pass?** Don't game it. Look at which specific
  questions fail, inspect the retrieved chunks, and fix the underlying
  issue (prompt, chunking, retrieval).

---

## 16. What "done" means

Phase 0–4 is "done" when a freshly-cloned repository can run:

```bash
cp .env.example .env
make install
make up
make seed
make api &
make ui &
make eval
```

…and the eval output shows all 6 metrics meeting their v1 targets.
