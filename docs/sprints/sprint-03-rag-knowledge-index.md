# Sprint 03 - RAG Knowledge Ingestion and Retrieval

## Goal
Deliver the knowledge indexing and retrieval layer used by the agent before decision making.

## Scope
- Implement knowledge ingestion pipeline for:
  - policy documents
  - historical cases
  - runbooks/procedures
- Chunk and attach metadata (`source`, `document_type`, `version`, `team`, `created_at`).
- Generate embeddings and store vectors in chosen backend.
- Implement retrieval API for top-k context with optional metadata filters.
- Persist retrieved chunk IDs for traceability hooks in later sprints.

## Deliverables
- `src/knowledge/` and `src/rag/` modules for ingestion, chunking, embedding, retrieval.
- `scripts/build_knowledge_index.py` for full and incremental index updates.
- Retrieval service contract consumed by the pipeline.

## Test Gate (must pass before Sprint 04)
- Index build tests:
  - index creation works from sample knowledge set.
  - repeated build/update is stable and does not corrupt metadata.
- Retrieval relevance tests (fixture-based):
  - known queries return expected chunk IDs in top-k.
- Metadata integrity tests:
  - every stored chunk includes required metadata fields.
- Performance sanity check:
  - retrieval returns within agreed local latency threshold for sample corpus.

## Exit Criteria
- RAG layer can be built and queried from CLI/scripts.
- Retrieval is deterministic enough on fixtures to support decision tests.
- Test gate is green before agent decision logic is implemented.
