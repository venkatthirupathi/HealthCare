# AceIQ Health — Architecture

## System diagram

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

## Query flow (single request)

1. **POST /api/v1/query** arrives with `{ question, filters? }`
2. **PII redaction** — regex masks emails, phones, Aadhaar, PAN, MRN, DOB, and names following trigger words
3. **Intent detection** — five prescribing-decision regex patterns; refuse with clinical-judgement reminder if matched
4. **Retrieval** — question embedded with `all-MiniLM-L6-v2`; pgvector cosine top-8 + pg_trgm top-8 fused via Reciprocal Rank Fusion (k=60); top candidates reranked with `ms-marco-MiniLM-L-6-v2`; return top-3
5. **Generation** — top-3 chunks formatted into prompt; Anthropic primary → OpenAI fallback → retrieval-only
6. **Verifier** — cheap second call with `claude-haiku-4-5-20251001` scores grounding 0–1
7. **Audit log** — every field written to `query_logs`
8. **Response** — answer + citations + verifier_score + latency_ms + disclaimer

## Key design choices

| Choice | Reason |
|--------|--------|
| pgvector over Pinecone | One DB to operate; free; sufficient for <10M vectors |
| Local embeddings | Zero per-query cost; fast on CPU |
| Anthropic + OpenAI fallback | Demonstrates "fallback and degradation strategies" |
| Regex-only PII | Auditable, deterministic, zero latency, no per-query cost |
| Sync SQLAlchemy | Simpler than async for initial DB layer; upgrade path clear |
| One section = one chunk | Sections are short (<400 tokens); sub-section splitting adds noise |

## Retrieval pipeline detail

```
question
  │
  ▼ embed_query()
query_vector (384-dim)
  │
  ├─ pgvector <=> cosine top-8  ─────────┐
  │                                       ▼
  └─ pg_trgm similarity() top-8  ──► RRF fusion (k=60)
                                         │
                                         ▼ top candidates
                                    cross-encoder rerank
                                         │
                                         ▼ top-3 chunks
```

## Database schema summary

```sql
documents  (id, source, external_id, title, drug_name, meta, created_at)
           UNIQUE (source, external_id)

chunks     (id, document_id FK, section, section_order, text, embedding vector(384), created_at)
           GIN index on text (gin_trgm_ops)
           IVFFlat index on embedding

jobs       (id, kind, status, payload, result, error, created_at, updated_at)

query_logs (id, question, redacted_question, answer, refused, refusal_reason,
            model_used, provider_used, retrieved_chunk_ids, verifier_score,
            latency_ms, tokens_in, tokens_out, created_at)
           INDEX on created_at
```
