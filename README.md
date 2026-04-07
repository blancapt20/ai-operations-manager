# AI Operations Manager

Autonomous case/event processing system that simulates a real-world enterprise AI product.

The system ingests events from multiple simulated sources, decides and executes actions through an agent core, and records everything with traceability and measurable performance.

## Table of Contents

- [Overall Goal](#overall-goal)
- [High-Level Architecture (Phase 0)](#high-level-architecture-phase-0)
- [Phase 0 Scope and Milestones](#phase-0-scope-and-milestones)
- [Getting Started (Planned)](#getting-started-planned)
- [Project Status](#project-status)

## Overall Goal

Build an autonomous core system where inputs come from heterogeneous channels and are processed end-to-end in a way that is:

- **Traceable**: every action and decision is auditable.
- **Evaluable**: performance and quality are measurable.
- **Observable**: logs and execution metadata are available for analysis.
- **Practical**: runs entirely from CLI/scripts with no UI dependency.

This phase demonstrates:

- Solid backend architecture
- Agent-based reasoning and orchestration
- Data integration from multiple sources
- Metrics and evaluation
- Observability and auditability

## High-Level Architecture (Phase 0)

```text
[Input Simulators]
  |-- email events
  |-- ticket events
  |-- internal events
  |-- CLI/test JSON
          |
          v
[Ingestion Layer] -> normalize + validate -> persist raw event
          |
          v
[Retrieval Layer (RAG)] -> embed + retrieve policies/history
          |
          v
[Agent Decision Core] -> classify + decide + generate output
          |
          v
[Action Layer] -> simulated tools/services
          |
          v
[Persistence + Logs + Metrics]
  |-- case history
  |-- execution trace
  |-- latency/cost/accuracy KPIs
```

## Phase 0 Scope and Milestones

Phase 0 focuses on delivering a complete, interview-friendly backend prototype.

### Milestone 0A - Core Pipeline

- Multi-source ingestion simulation (`email`, `tickets`, `internal events`, `CLI/test JSON`)
- RAG ingestion/indexing pipeline for policy and historical case knowledge
- Agentic classification and decision flow (LLM + deterministic logic)
- Simulated action execution (`refund_service`, `email_service`, `logging`)
- Persistence of inputs, decisions, outputs, and execution metadata
- Structured local observability logs (JSON/JSONL) to keep each case auditable

### Milestone 0B - Reliability and Evaluation

- Evaluation scripts and benchmark dataset comparisons
- KPI tracking (accuracy, latency, cost, trace completeness)
- Retrieval quality metrics (`hit@k`, context relevance, answer-grounding checks)
- Detailed observability logs for each processing step
- Repeatable CLI workflow for testability and auditing
- Database-backed observability/metrics layer built from 0A telemetry

#### Telemetry strategy across milestones

- **0A**: Store step-level traces in structured log files (for example `logs/*.jsonl`) with stable fields (`case_id`, `event_id`, `step`, `status`, timestamps, `latency_ms`).
- **0B**: Move or replicate telemetry into a database for aggregate KPI reporting, benchmark analysis, and historical trend queries.

## Detailed Objectives (Phase 0)

### 1) Multi-source ingestion simulation

**What it does**

Simulates incoming data from different channels, for example:

- Customer emails (mock or real)
- Incident tickets
- Internal system events
- CLI commands or test JSON payloads

**Why it matters**

Real enterprise systems must process heterogeneous event flows from multiple tools and teams.

**Observable outcome**

Each input is persisted with metadata such as:

- `source`
- `timestamp`
- `event_type`

### 2) Agent-based decision core

**What it does**

An agent (LLM + deterministic logic) processes each input and decides how to act:

- Classify the case
- Generate a response
- Trigger a simulated tool (`refund_service`, `email_service`, `logging`, etc.)

**Why it matters**

Shows autonomous reasoning, prioritization, and integration capability with external services.

**Observable outcome**

Each input generates a persisted decision and output.

**Implementation notes (to avoid ambiguity)**

- Runtime pattern: `input -> normalize -> retrieve context (RAG) -> decide -> act -> persist -> log`
- API keys are required when using real LLM/embedding providers.
- Suggested env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `MODEL_NAME`, `EMBEDDING_MODEL`
- MCP/tool integrations are optional in Phase 0; start with local simulated tools and later replace/extend with MCP-backed tools.
- RAG retrieves prior similar cases and policy snippets before final decision.

### 3) Persistence and tracking

**What it does**

Stores:

- Inputs
- Agent decisions
- Generated outputs
- Execution metadata (`latency`, `cost`, `steps`)

**Why it matters**

Prevents black-box behavior and enables internal auditing and debugging.

**Observable outcome**

A complete case history can be queried and analyzed.

**Storage and retrieval notes**

- RAG stores embeddings in a vector index and links chunks to case/source metadata.
- Suggested vector options:
  - Local prototype: `Chroma` or `FAISS`
  - SQL-friendly: `Postgres + pgvector`
  - Managed: `Pinecone` or `Qdrant Cloud`
- Common persistence env vars: `DATABASE_URL`, `VECTOR_DB_PROVIDER`

### 4) RAG implementation plan

The project will implement production-style RAG behavior using simulated enterprise data sources.

#### Knowledge sources (simulated but realistic)

- Policy documents (refund policy, escalation policy, SLA rules)
- Historical resolved cases
- Internal runbooks and standard procedures

#### Ingestion and indexing workflow

1. Normalize documents and case records into canonical JSON.
2. Chunk documents with metadata (`source`, `document_type`, `version`, `team`, `created_at`).
3. Generate embeddings for chunks.
4. Store vectors plus metadata in the selected vector DB.

#### Retrieval and decision workflow

1. Build query from incoming case + extracted intent.
2. Retrieve top-k relevant chunks with metadata filters.
3. Add retrieved context to agent prompt.
4. Produce classification, rationale, response, and tool action.
5. Persist retrieved chunk ids for traceability.

#### RAG evaluation workflow

- Track retrieval metrics (`hit@k`, context precision)
- Track decision quality with and without retrieval
- Log grounding evidence (which chunks supported the final answer)

#### Minimum scripts to implement

- `scripts/build_knowledge_index.py` -> build/update vector index
- `scripts/run_pipeline.py` -> ingest, retrieve, decide, act, persist
- `scripts/run_evaluation.py` -> compute decision and retrieval KPIs

### 5) Evaluation and metrics

**What it does**

Implements measurable KPIs for the agent, including:

- Decision accuracy against a labeled test dataset
- Execution latency
- Processing cost (tokens / time / resources)

**Why it matters**

Demonstrates engineering maturity: the system is tested and optimized, not just functional.

**Observable outcome**

Evaluation scripts output KPI reports and comparisons versus expected outcomes.

### 6) Observability

**What it does**

Logs each processing step in detail:

- Input received
- Transformations applied
- Final decision
- Action executed
- Time spent per step

**Why it matters**

Production-grade AI systems require traceability, incident analysis, and compliance-ready records.

**Observable outcome**

Structured JSON logs or log database entries that can later feed dashboards.

### 7) Simplicity of implementation

**What it does**

Runs entirely via CLI/Python scripts, without a UI.

**Why it matters**

Keeps focus on backend and AI orchestration quality, which is often the core interview signal.

## Planned Repository Structure

As implementation evolves, a structure like this is recommended:

```text
ai-operations-manager/
  src/
    ingestion/
    agent/
    rag/
    knowledge/
    actions/
    integrations/
    persistence/
    observability/
    evaluation/
  scripts/
    run_ingestion.py
    run_pipeline.py
    run_evaluation.py
  data/
    samples/
    test_dataset/
  logs/
  tests/
  README.md
```

## Getting Started (Planned)

> The repository is currently in definition/bootstrap stage. Commands below describe the intended workflow.

### Prerequisites

- Python 3.10+
- `pip` or `poetry`
- SQLite or PostgreSQL for persistence
- A vector store backend (`Chroma`, `FAISS`, `pgvector`, `Qdrant`, or `Pinecone`)

### Setup

```bash
# 1) Clone
git clone <your-repo-url>
cd ai-operations-manager

# 2) Create virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate

# 3) Install dependencies
pip install -r requirements.txt

# 4) Configure database connection (Supabase/Postgres recommended)
# PowerShell example:
$env:DATABASE_URL="postgresql+psycopg://<user>:<password>@<host>:5432/<db>"

# 5) Apply migrations
python scripts/apply_migrations.py
```

### Run (target workflow)

```bash
# Simulate ingestion
python scripts/run_ingestion.py --source email --input-file data/samples/email_event.json

# Simulate mixed batch ingestion
python scripts/run_ingestion.py --batch-file data/samples/mixed_source_batch.json

# Build/update RAG index
python scripts/build_knowledge_index.py

# Process pending cases through the agent core
python scripts/run_pipeline.py

# Evaluate KPIs
python scripts/run_evaluation.py
```

## Project Status

- Current status: **Phase 0 architecture and scope finalized; implementation in progress**
- Next status target: **Phase 0 runnable end-to-end pipeline with RAG, metrics, and observability**

## KPIs to Track

- **Accuracy**: percentage of correct decisions vs. labeled dataset
- **Latency**: average and p95 processing time per case
- **Cost**: token/time/resource usage per case and per batch
- **Retrieval hit@k**: percentage of cases where relevant context appears in top-k retrieved chunks
- **Context precision**: fraction of retrieved chunks that are actually useful to the decision
- **Grounding rate**: percentage of responses/actions supported by retrieved evidence
- **Trace completeness**: % of cases with full step-level logs

## Phase 0 Deliverables

By the end of Phase 0, the project should be able to:

1. Simulate multi-source data ingestion.
2. Automatically process inputs with an agent that decides and triggers actions.
3. Build and query a RAG knowledge layer using a vector database.
4. Persist all events, decisions, outputs, and execution metadata.
5. Evaluate performance and quality through measurable KPIs (decision + retrieval).
6. Maintain detailed observability logs for auditing.
7. Run end-to-end through scripts in a repeatable way.

## Non-Goals (Phase 0)

- No frontend/UI
- No production deployment requirements

## Roadmap

- **Phase 0**: Core simulation, RAG + vector DB retrieval, agent decisions, persistence, evaluation, logs
- **Phase 1**: Hardening, modularization, improved datasets and test coverage
- **Phase 2**: Real integrations, dashboarding, deployment-ready architecture

## Contributing

Contributions are welcome. Suggested flow:

1. Create a feature branch from `dev`.
2. Add/modify code with tests where applicable.
3. Open a PR with clear description and expected impact.

## License

Choose and add a license file (`MIT`, `Apache-2.0`, etc.) before public release.