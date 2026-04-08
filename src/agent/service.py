"""Orchestration service for the end-to-end processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from src.common.contracts import ProcessingResult, StepStatus
from src.common.validation import validate_execution_trace_step, validate_processing_result
from src.persistence.db import build_engine, build_session_factory
from src.persistence.migrations import apply_migrations
from src.persistence.pipeline_store import PipelineStore
from src.rag.embeddings import EmbeddingProvider
from src.rag.service import RetrievalService


@dataclass(slots=True)
class PipelineRunSummary:
    processed: int
    cases: list[dict[str, object]]


class PipelineService:
    """Processes pending ingested events using grounded retrieval."""

    def __init__(
        self,
        database_url: str,
        *,
        embedding_model_name: str = "text-embedding-3-small",
        embedding_api_key: str | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.engine = build_engine(database_url)
        apply_migrations(self.engine, Path(__file__).resolve().parents[2] / "migrations")
        self.session_factory = build_session_factory(self.engine)
        self.store = PipelineStore(self.session_factory)
        self.retrieval_service = RetrievalService(
            database_url,
            embedding_model_name=embedding_model_name,
            embedding_api_key=embedding_api_key,
            embedding_provider=embedding_provider,
        )

    def close(self) -> None:
        self.retrieval_service.close()
        self.engine.dispose()

    def process_pending_events(self, *, limit: int = 10, dry_run: bool = False) -> PipelineRunSummary:
        events = self.store.fetch_pending_events(limit)
        if dry_run:
            return PipelineRunSummary(
                processed=0,
                cases=[
                    {
                        "event_id": event.event_id,
                        "query": build_query_from_event(event.subject, event.body, event.event_type),
                    }
                    for event in events
                ],
            )

        processed_cases: list[dict[str, object]] = []
        for event in events:
            case_id = f"case-{event.event_id}"
            query = build_query_from_event(event.subject, event.body, event.event_type)

            retrieval_started = datetime.utcnow()
            retrieval_result = self.retrieval_service.retrieve_context(
                query,
                top_k=5,
                case_id=case_id,
            )
            retrieval_finished = datetime.utcnow()
            self.store.persist_trace_step(
                validate_execution_trace_step(
                    {
                        "case_id": case_id,
                        "step_name": "retrieve_context",
                        "status": StepStatus.SUCCESS.value,
                        "started_at": retrieval_started.isoformat(),
                        "finished_at": retrieval_finished.isoformat(),
                        "latency_ms": _latency_ms(retrieval_started, retrieval_finished),
                        "details": {
                            "query": query,
                            "retrieval_status": retrieval_result.status,
                            "chunk_ids": [chunk.chunk_id for chunk in retrieval_result.chunks],
                            "scores": retrieval_result.scores,
                            "warnings": retrieval_result.warnings,
                        },
                    }
                )
            )

            decision_started = datetime.utcnow()
            processing_result, status = grounded_decision_for_event(
                case_id=case_id,
                event_id=event.event_id,
                event_type=event.event_type,
                query=query,
                retrieval_status=retrieval_result.status,
                chunk_ids=[chunk.chunk_id for chunk in retrieval_result.chunks],
                top_chunk_text=retrieval_result.chunks[0].text if retrieval_result.chunks else None,
                warnings=retrieval_result.warnings,
            )
            decision_finished = datetime.utcnow()

            self.store.persist_processing_result(processing_result, status=status)
            self.store.persist_trace_step(
                validate_execution_trace_step(
                    {
                        "case_id": case_id,
                        "step_name": "grounded_decision",
                        "status": StepStatus.SUCCESS.value,
                        "started_at": decision_started.isoformat(),
                        "finished_at": decision_finished.isoformat(),
                        "latency_ms": _latency_ms(decision_started, decision_finished),
                        "details": {
                            "classification": processing_result.classification,
                            "action": processing_result.action,
                            "status": status,
                            "warnings": retrieval_result.warnings,
                        },
                    }
                )
            )

            processed_cases.append(
                {
                    "case_id": case_id,
                    "event_id": event.event_id,
                    "retrieval_status": retrieval_result.status,
                    "classification": processing_result.classification,
                    "action": processing_result.action,
                    "retrieved_chunk_ids": [chunk.chunk_id for chunk in retrieval_result.chunks],
                }
            )

        return PipelineRunSummary(processed=len(processed_cases), cases=processed_cases)


def build_query_from_event(subject: str | None, body: str, event_type: str) -> str:
    if subject and subject.strip():
        return subject.strip()
    if event_type.strip():
        return event_type.strip()
    return body.strip()


def grounded_decision_for_event(
    *,
    case_id: str,
    event_id: str,
    event_type: str,
    query: str,
    retrieval_status: str,
    chunk_ids: list[str],
    top_chunk_text: str | None,
    warnings: list[str],
) -> tuple[ProcessingResult, str]:
    if retrieval_status == "no_context":
        result = validate_processing_result(
            {
                "case_id": case_id,
                "event_id": event_id,
                "classification": "needs_context",
                "rationale": f"No grounded context found for query: {query}",
                "action": "manual_review",
                "response_text": "No reliable knowledge context was found. Route the case for manual review.",
                "confidence": 0.0,
                "flags": ["no_context"],
            }
        )
        return result, "no_context"

    flags = [retrieval_status]
    flags.extend(warnings)
    if retrieval_status == "low_confidence" or warnings:
        result = validate_processing_result(
            {
                "case_id": case_id,
                "event_id": event_id,
                "classification": f"{event_type}_needs_review",
                "rationale": (
                    "Retrieved context exists but requires human validation due to "
                    f"status={retrieval_status} warnings={warnings} chunk_ids={chunk_ids}"
                ),
                "action": "manual_review",
                "response_text": "Relevant knowledge was found, but the case should be reviewed before final action.",
                "confidence": 0.4,
                "flags": flags,
            }
        )
        return result, "needs_review"

    snippet = (top_chunk_text or "").splitlines()[0][:180]
    result = validate_processing_result(
        {
            "case_id": case_id,
            "event_id": event_id,
            "classification": f"{event_type}_grounded",
            "rationale": f"Grounded on retrieved chunks {chunk_ids}. Lead evidence: {snippet}",
            "action": "grounded_response_ready",
            "response_text": (
                "Grounded context found. Use the retrieved knowledge to continue with a "
                "customer-facing response or downstream tool action."
            ),
            "confidence": 0.8,
            "flags": flags,
        }
    )
    return result, "processed"


def _latency_ms(started_at: datetime, finished_at: datetime) -> int:
    return int((finished_at - started_at).total_seconds() * 1000)
