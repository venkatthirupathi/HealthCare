# AceIQ Health — Roadmap

v1 (this repo) delivers a complete vertical slice: ingest → RAG → answer → audit.
Future phases are described below; each is approximately one week of work.

| Phase | Name | Description |
|-------|------|-------------|
| **v1** *(done)* | Vertical slice | FastAPI + pgvector + local embeddings + Streamlit + eval |
| **Phase 5** | LangGraph multi-agent | Planner → retriever → writer → critic agent graph |
| **Phase 6** | Java auth gateway | Spring Boot or ASP.NET Core JWT gateway; RBAC for clinician vs student roles |
| **Phase 7** | React frontend | TypeScript + React replaces Streamlit; streaming responses via SSE |
| **Phase 8** | Streaming + semantic cache | Server-sent events; Redis-based semantic dedup cache; model router |
| **Phase 9** | Event-driven ingestion | Redis Streams + dedicated ingest worker; async DailyMed polling |
| **Phase 10** | Observability | Langfuse traces; Prometheus metrics; Grafana dashboard |
| **Phase 11** | CI/CD | GitHub Actions: lint + tests + eval-on-PR + Docker image push |
| **Phase 12** | Kubernetes | Helm chart; EKS or AKS; HPA on API pods |
| **Phase 13** | Indian-context corpus | ICMR guidelines; CDSCO drug data; NMC educational content |

## Phase 5 detail — LangGraph multi-agent

```
user query
    │
    ▼
[Planner agent]  — decides retrieval strategy, drug filter, sub-questions
    │
    ▼
[Retriever agent]  — runs hybrid search, applies filters
    │
    ▼
[Writer agent]  — generates cited answer using ONLY retrieved chunks
    │
    ▼
[Critic agent]  — reviews answer for factual grounding, flags hallucinations
    │
    ▼
final response
```

Enables multi-hop reasoning (e.g. "is the combination of metformin and ibuprofen safe?").

## Phase 11 detail — CI/CD pipeline

```yaml
on: [push, pull_request]
jobs:
  lint:    ruff check + ruff format --check
  test:    pytest tests/ --tb=short
  eval:    make seed && make api & make eval (runs against seeded DB)
  docker:  build + push image to ECR/ACR
```

Eval failures block merges — the 6 metrics are the project's merge gate.
