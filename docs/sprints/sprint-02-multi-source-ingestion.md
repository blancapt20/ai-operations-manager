# Sprint 02 - Multi-source Ingestion

## Goal
Implement ingestion simulation for all Milestone `0A` channels and persist raw + normalized events.

## Scope
- Build source adapters for:
  - email simulator
  - ticket simulator
  - internal event simulator
  - CLI/test JSON input
- Normalize all inputs into the shared canonical event contract.
- Validate and reject bad inputs with traceable error messages.
- Persist:
  - raw input payload
  - normalized event
  - ingestion metadata (`source`, `timestamp`, `event_type`, ingestion status)

## Deliverables
- `src/ingestion/` module with source-specific parsers/adapters.
- `scripts/run_ingestion.py` supporting single-event and batch simulation.
- Seed sample payloads in `data/samples/` for all sources.

## Test Gate (must pass before Sprint 03)
- Source parity tests:
  - at least one happy-path and one invalid-path test per source.
- Ingestion persistence tests:
  - raw and normalized records are both stored.
  - metadata fields are always present.
- Idempotency/basic dedup behavior test for repeated event IDs (or explicit duplicate policy test).
- End-to-end ingestion smoke test:
  - run ingestion script over mixed-source sample batch and verify persisted count.

## Exit Criteria
- All four input channels are processed consistently through a single normalized format.
- Ingestion data is queryable and auditable.
- Test gate is fully green before retrieval/RAG work starts.
