# Cognizant Ace Team — Full Stack AI Engineer (2026 graduate role)

This is the original job description that AceIQ Health is designed to map
onto. Each skill in the JD has a corresponding feature in the project.

---

## About the role

Cognizant Ace Team is Cognizant's most selective engineering program — a
handpicked cohort of high-potential AI builders chosen to work on real client
challenges using AI-native tools, modern architectures, and outcome-driven
methods.

As an Ace — Full Stack AI Engineer, you will:

- Work on production codebases from week one
- Build AI-native capabilities such as RAG pipelines, agentic workflows,
  and LLM-integrated applications
- Present working solutions to client stakeholders
- Rotate across domains, technology stacks, and problem types

---

## Areas of responsibility

### AI-native engineering

- Build UI components, REST APIs, and end-to-end workflows leveraging
  LLMs, code assistants, and AI agents
- Design prompt templates, structured outputs, and tool-calling patterns
  for production use
- Engineer AI-first workflows: RAG pipelines, agentic systems, tool
  orchestration
- Integrate fine-tuned or hosted AI models into enterprise application
  stacks

### Solution design & architecture

- Rapidly absorb unfamiliar client codebases, team contexts, and problem
  spaces — within days
- Translate business requirements into AI-native solution designs with
  clear API and data-flow specifications
- Make informed decisions on model selection, RAG vs agentic approaches,
  and cost-accuracy trade-offs
- Contribute to architecture discussions; document technical trade-offs
  and assumptions

### Quality & governance

- Validate AI outputs for correctness, safety, and relevance; flag
  hallucinations and bias early
- Design and run continuous test automation for AI-enabled features
- Implement monitoring, logging, and AI guardrails to support
  auditability
- Follow and promote secure-by-design and responsible AI practices

### Delivery & client impact

- Ship working AI-native features and production-grade systems at
  accelerated pace
- Deliver short-cycle POCs, prototypes, and live client demos
- Produce handover documentation so client teams can sustain and scale
  independently

### Communication & collaboration

- Communicate technical concepts clearly to both technical and
  non-technical stakeholders
- Lead demos, technical walkthroughs, and client-facing showcases
- Collaborate across cross-functional teams; mentor peers on engagements

---

## Skills & technologies

### Languages & frameworks
Python, Java / .NET, JavaScript / TypeScript, React / Angular, REST APIs, SQL

### AI & LLM
LLMs & embeddings, RAG pipelines, prompt engineering & structured outputs,
LLM orchestration (LangChain / LangGraph / CrewAI / AutoGen), AI coding
assistants (GitHub Copilot, Claude)

### Cloud & DevOps
AWS / Azure / GCP, Git, CI/CD pipelines, containers & cloud-native services

### AI evaluation & ops
AI quality metrics, monitoring & guardrails, cost & latency optimisation,
fallback and degradation strategies

### Good to have
Vector DB concepts, Streamlit / FastAPI, RAGAS / DeepEval, Kubernetes,
event-driven architectures

---

## Skill → AceIQ Health feature map

This is the map an interviewer should be able to walk through. Every JD skill
has a concrete location in the codebase.

| JD skill                                  | Where in AceIQ Health (v1 + roadmap)           |
|-------------------------------------------|------------------------------------------------|
| Python                                    | All backend code                               |
| Java / .NET                               | Auth gateway (roadmap Phase 6)                 |
| JavaScript / TypeScript + React           | Frontend (roadmap Phase 7)                     |
| REST APIs                                 | All FastAPI routes; OpenAPI auto-generated     |
| SQL                                       | Postgres for `documents`, `chunks`, `query_logs` |
| LLMs & embeddings                         | sentence-transformers + Claude/GPT             |
| RAG pipelines                             | `services/retrieval.py` — hybrid + RRF + rerank |
| Prompt engineering & structured outputs   | `services/llm.py` system prompt; Pydantic schemas |
| LLM orchestration (LangGraph / etc.)      | `backend/agents/` (roadmap Phase 5)            |
| AI coding assistants                      | Build the project with Claude Code itself — track velocity in README |
| AWS / Azure / GCP                         | Deploy via Helm (roadmap Phase 12)             |
| Git + CI/CD                               | GitHub Actions (roadmap Phase 11)              |
| Containers                                | `docker-compose.yml` for local; Dockerfile per service |
| Kubernetes                                | Helm chart (roadmap Phase 12)                  |
| AI quality metrics                        | `eval/run_eval.py` — 6 metrics                 |
| Monitoring & guardrails                   | `services/guardrails.py` + Langfuse (roadmap Phase 10) |
| Cost & latency optimisation               | Model router + semantic cache (roadmap Phase 8) |
| Fallback & degradation strategies         | `services/llm.py` — explicit provider chain    |
| Vector DB concepts                        | pgvector with IVFFlat index                    |
| Streamlit / FastAPI                       | Both present in v1                             |
| RAGAS / DeepEval                          | `eval/ragas_eval.py` (roadmap)                 |
| Event-driven architectures                | Redis Streams ingestion (roadmap Phase 9)      |

---

## Why AceIQ Health, specifically

Most candidates for this role show generic projects: a chatbot, a Q&A app,
maybe a Streamlit demo. AceIQ Health is designed to show something more:

1. **A real product mindset.** It refuses unsafe questions, redacts PII,
   logs everything for audit. The safety story is the *product*, not an
   afterthought.

2. **Trade-offs documented in writing.** `ARCHITECTURE.md` makes every
   decision (pgvector vs Pinecone, regex vs LLM guardrails, etc.)
   defensible in an interview.

3. **Quality measured, not vibed.** A 12-question eval set with 6 metrics
   that an interviewer can run themselves.

4. **A clear roadmap.** v1 ships in two weeks; v2+ has 9 more phases
   documented. The candidate can credibly say "I shipped X; here's
   exactly what comes next, in what order."

5. **Local relevance.** The PII patterns include Aadhaar and PAN; the
   roadmap includes ICMR guideline ingestion. The candidate built
   something that genuinely understands Indian clinical practice — not
   a Western project they Googled.
