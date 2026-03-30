# Sprint 01 - Foundation and Contracts

## Goal
Establish the baseline project skeleton, canonical schemas, and local developer workflow required to implement Milestone `0A`.

## Scope
- Create initial project structure for `src/`, `scripts/`, `data/`, `logs/`, and `tests/`.
- Define canonical event schema for all input sources (`email`, `tickets`, `internal`, `cli_json`).
- Define case-processing contract for pipeline outputs (classification, rationale, action, metadata).
- Define configuration contract (`.env.example`) for model, storage, and vector settings.
- Add minimal smoke CLI entry points (no business logic yet) for:
  - `scripts/run_ingestion.py`
  - `scripts/build_knowledge_index.py`
  - `scripts/run_pipeline.py`

## Deliverables
- Typed schemas or dataclasses for:
  - normalized input event
  - processing result
  - execution trace step
- Shared validation utilities and error model.
- Documented development commands for setup and local execution.

## Test Gate (must pass before Sprint 02)
- Unit tests validating schema acceptance/rejection:
  - valid events from every source are accepted.
  - malformed payloads are rejected with explicit errors.
- CLI smoke tests:
  - each script runs with `--help` and exits `0`.
- Lint/type checks pass for newly added files.

## Exit Criteria
- Contracts are stable and approved.
- Team can generate and validate normalized events without implementing ingestion logic yet.
- No downstream sprint starts until test gate is green in CI/local.
