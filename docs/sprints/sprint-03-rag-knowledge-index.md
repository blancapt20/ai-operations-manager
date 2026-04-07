# Sprint 03 - RAG Knowledge Ingestion and Grounded Retrieval

## Goal

Deliver a production-grade knowledge retrieval layer that:

- indexes structured and unstructured business knowledge
- retrieves relevant context deterministically
- enforces grounding for all downstream agent decisions

## Core Principle (new - very important)

No decision can be made without retrieved context.

The RAG layer is not optional. It is a hard dependency of the decision pipeline.

## Scope

### Knowledge ingestion

Implement ingestion pipeline for:

- policy documents (refund rules, SLAs, eligibility)
- historical cases (resolved examples)
- runbooks/procedures (operational actions)

### Chunking strategy (upgraded)

- Chunk documents into semantically meaningful units (not fixed-size only).
- Preserve:
  - rule boundaries
  - condition-action structures
- Avoid splitting critical logic across chunks.

### Metadata schema (strict)

Each chunk must include:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "document_type": "policy | case | runbook",
  "source": "...",
  "version": "...",
  "team": "...",
  "created_at": "...",
  "valid_from": "...",
  "valid_to": "... (optional)"
}
```

This enables:

- filtering
- versioning
- auditability

### Embeddings and storage

- Generate embeddings for each chunk.
- Store vectors in Postgres + pgvector.
- Ensure:
  - idempotent indexing
  - no duplication on re-index

### Retrieval layer (critical upgrade)

Implement retrieval API:

```python
retrieve_context(
    query: str,
    top_k: int = 5,
    filters: dict = {},
    min_similarity: float = ?
) -> List[Chunk]
```

### Retrieval requirements (new)

- Deterministic behavior:
  - same query should produce stable results (within tolerance)
- Similarity threshold:
  - if no chunk passes threshold, return empty
- Metadata filtering support for:
  - `document_type`
  - `version`
  - `team`
- Ranking quality:
  - most relevant chunks must appear in top-k

### Failure modes (new - very important)

The system must handle:

- no results found
- low-confidence retrieval
- conflicting documents

Return structured signal:

```json
{
  "status": "ok | no_context | low_confidence",
  "chunks": [...],
  "scores": [...]
}
```

This will later drive:

- human-in-the-loop review
- fallback logic

### Traceability (upgraded)

Persist:

- retrieved chunk IDs
- similarity scores

Ensure every decision can be traced back to exact knowledge used.

## Deliverables

- `src/knowledge/` for ingestion, chunking, and metadata.
- `src/rag/` for embedding and retrieval logic.
- `scripts/build_knowledge_index.py` supporting:
  - full rebuild
  - incremental updates
  - idempotent execution
- Retrieval service contract:
  - used by decision pipeline
  - returns context plus retrieval status

## Test Gate (upgraded)

### Index build tests

- Index creation from sample dataset works.
- Re-indexing verifies:
  - no duplication
  - metadata preserved
  - versioning respected

### Retrieval relevance tests (important)

Fixture-based:

- known queries return expected chunks in top-k
- ranking correctness is validated (not just presence)

### Retrieval failure tests (new)

- no relevant documents returns `no_context`
- low similarity returns `low_confidence`

### Metadata integrity tests

- all chunks include required metadata
- filtering works correctly

### Determinism test (new)

- same query run multiple times returns consistent results

### Performance sanity check

- retrieval latency remains within acceptable local threshold

## Exit Criteria (upgraded)

- RAG layer can be built and queried via CLI/scripts.
- Retrieval is deterministic, testable, and traceable.
- System explicitly handles:
  - missing context
  - low confidence
- Retrieval outputs are ready for decision engine consumption.
- Test gate is green.

