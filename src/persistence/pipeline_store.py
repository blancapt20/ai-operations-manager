"""Persistence helpers for the processing pipeline."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from src.common.contracts import EventSource, ExecutionTraceStep, NormalizedEvent, ProcessingResult
from src.persistence.models import (
    CaseRecord,
    ExecutionTraceStepRecord,
    NormalizedEventRecord,
)


class PipelineStore:
    """Reads pending events and persists case/trace outputs."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def fetch_pending_events(self, limit: int) -> list[NormalizedEvent]:
        with self.session_factory() as session:
            statement = (
                select(NormalizedEventRecord)
                .outerjoin(CaseRecord, CaseRecord.event_id == NormalizedEventRecord.event_id)
                .where(CaseRecord.id.is_(None))
                .order_by(NormalizedEventRecord.created_at, NormalizedEventRecord.id)
                .limit(limit)
            )
            rows = session.execute(statement).scalars().all()

        return [
            NormalizedEvent(
                event_id=row.event_id,
                source=EventSource(row.source),
                timestamp=row.timestamp,
                event_type=row.event_type,
                body=row.body,
                subject=row.subject,
                customer_id=row.customer_id,
                metadata=json.loads(row.metadata_json or "{}"),
            )
            for row in rows
        ]

    def persist_processing_result(self, result: ProcessingResult, *, status: str) -> None:
        with self.session_factory() as session:
            next_id = self._next_id(session, CaseRecord)
            session.add(
                CaseRecord(
                    id=next_id,
                    case_id=result.case_id,
                    event_id=result.event_id,
                    status=status,
                    classification=result.classification,
                    action=result.action,
                    response_text=result.response_text,
                    created_at=result.created_at,
                    updated_at=datetime.utcnow(),
                )
            )
            session.commit()

    def persist_trace_step(self, step: ExecutionTraceStep) -> None:
        with self.session_factory() as session:
            next_id = self._next_id(session, ExecutionTraceStepRecord)
            session.add(
                ExecutionTraceStepRecord(
                    id=next_id,
                    case_id=step.case_id,
                    step_name=step.step_name,
                    status=step.status.value,
                    started_at=step.started_at,
                    finished_at=step.finished_at,
                    latency_ms=step.latency_ms,
                    details_json=json.dumps(step.details),
                )
            )
            session.commit()

    def list_cases(self) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            rows = session.execute(select(CaseRecord).order_by(CaseRecord.id)).scalars().all()
        return [
            {
                "case_id": row.case_id,
                "event_id": row.event_id,
                "status": row.status,
                "classification": row.classification,
                "action": row.action,
                "response_text": row.response_text,
            }
            for row in rows
        ]

    def _next_id(self, session: Any, model: Any) -> int:
        current_max = session.execute(select(func.max(model.id))).scalar_one()
        if current_max is None:
            return 1
        return int(current_max) + 1
