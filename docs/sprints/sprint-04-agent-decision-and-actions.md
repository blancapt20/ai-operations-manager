# Sprint 04 - Agent Decision Core and Simulated Actions

## Goal
Implement the decision engine (`classify -> decide -> respond -> act`) using retrieved context and deterministic guardrails.

## Scope
- Build agent orchestration flow:
  - accept normalized event
  - call retrieval layer
  - run LLM + deterministic policy checks
  - produce classification, rationale, response, and action
- Implement simulated action tools:
  - `refund_service`
  - `email_service`
  - `logging`
- Add policy/guardrail logic for disallowed or ambiguous actions.
- Capture intermediate reasoning metadata needed for traceability (without leaking sensitive chain-of-thought text).

## Deliverables
- `src/agent/` orchestration and policy layer.
- `src/actions/` simulated tool execution layer.
- Initial runnable `scripts/run_pipeline.py` path for single-case processing.

## Test Gate (must pass before Sprint 05)
- Decision contract tests:
  - output always includes classification, rationale summary, selected action, and confidence/flags.
- Tool routing tests:
  - correct action service is triggered for labeled fixture cases.
- Guardrail tests:
  - policy-violating requests are blocked or escalated correctly.
- Deterministic replay tests:
  - fixed fixtures with mocked model responses produce expected actions.

## Exit Criteria
- Core autonomous decision flow runs with retrieval-augmented context.
- Simulated actions execute with predictable behavior.
- Test gate is green before full persistence/trace closure sprint begins.
