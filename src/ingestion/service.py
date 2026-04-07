"""Ingestion orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.contracts import EventSource, NormalizedEvent
from src.common.validation import ValidationError, validate_normalized_event
from src.ingestion.adapters import ADAPTERS
from src.persistence.db import build_engine, build_session_factory
from src.persistence.ingestion_store import IngestionStore
from src.persistence.migrations import apply_migrations


@dataclass(slots=True)
class IngestionResult:
    event_id: str
    source: str
    status: str
    reason: str | None = None


class IngestionService:
    """Ingests source payloads, normalizes, validates, and persists them."""

    def __init__(self, database_url: str) -> None:
        self.engine = build_engine(database_url)
        apply_migrations(self.engine, Path(__file__).resolve().parents[2] / "migrations")
        session_factory = build_session_factory(self.engine)
        self.store = IngestionStore(session_factory)

    def close(self) -> None:
        self.engine.dispose()

    def ingest_payload(self, source: EventSource, payload: dict[str, Any]) -> IngestionResult:
        adapter = ADAPTERS[source]
        # Persist raw payload regardless of outcome for traceability.
        self.store.persist_raw(source.value, payload)

        try:
            canonical = adapter(payload)
            event = validate_normalized_event(canonical)
        except ValidationError as exc:
            fallback_id = payload.get("event_id") or payload.get("id") or payload.get("ticket_id")
            event_id = str(fallback_id) if fallback_id else "unknown"
            self.store.persist_metadata(
                event_id=event_id,
                source=source.value,
                event_type=payload.get("event_type", "unknown"),
                timestamp=payload.get("timestamp", datetime.utcnow().isoformat()),
                status="rejected",
                message=str(exc),
            )
            return IngestionResult(
                event_id=event_id,
                source=source.value,
                status="rejected",
                reason=str(exc),
            )

        if self.store.has_event_id(event.event_id):
            self.store.persist_metadata(
                event_id=event.event_id,
                source=event.source.value,
                event_type=event.event_type,
                timestamp=event.timestamp.isoformat(),
                status="duplicate_skipped",
                message="duplicate event_id detected",
            )
            return IngestionResult(
                event_id=event.event_id,
                source=event.source.value,
                status="duplicate_skipped",
                reason="duplicate event_id detected",
            )

        self.store.persist_normalized(event)
        self.store.persist_metadata(
            event_id=event.event_id,
            source=event.source.value,
            event_type=event.event_type,
            timestamp=event.timestamp.isoformat(),
            status="accepted",
        )
        return IngestionResult(event_id=event.event_id, source=event.source.value, status="accepted")

    def ingest_records(self, records: list[dict[str, Any]]) -> list[IngestionResult]:
        results: list[IngestionResult] = []
        for record in records:
            source_raw = record.get("source")
            payload = record.get("payload")
            if not isinstance(source_raw, str):
                results.append(
                    IngestionResult(
                        event_id="unknown",
                        source="unknown",
                        status="rejected",
                        reason="'source' must be provided for batch record",
                    )
                )
                continue
            if not isinstance(payload, dict):
                results.append(
                    IngestionResult(
                        event_id="unknown",
                        source=source_raw,
                        status="rejected",
                        reason="'payload' must be an object",
                    )
                )
                continue

            try:
                source = EventSource(source_raw)
            except ValueError:
                results.append(
                    IngestionResult(
                        event_id="unknown",
                        source=source_raw,
                        status="rejected",
                        reason=f"unsupported source '{source_raw}'",
                    )
                )
                continue
            results.append(self.ingest_payload(source, payload))
        return results


def default_payload_for(source: EventSource) -> dict[str, Any]:
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    if source == EventSource.EMAIL:
        return {
            "id": "email-default-001",
            "received_at": now,
            "subject": "Billing question",
            "body": "I believe I was charged twice.",
            "customer_id": "cust-001",
            "sender": "customer@example.com",
        }
    if source == EventSource.TICKETS:
        return {
            "ticket_id": "ticket-default-001",
            "created_at": now,
            "title": "Duplicate charge incident",
            "issue_type": "billing_dispute",
            "description": "User reports duplicate invoice line.",
            "requester_id": "cust-002",
            "priority": "high",
        }
    if source == EventSource.INTERNAL_EVENTS:
        return {
            "event_id": "internal-default-001",
            "timestamp": now,
            "event_name": "billing_alert",
            "message": "Payment processor emitted duplicate_charge signal.",
            "service": "payments",
            "severity": "warning",
        }
    return {
        "event_id": "cli-default-001",
        "timestamp": now,
        "event_type": "billing_dispute",
        "body": "CLI generated customer charge dispute event.",
        "subject": "CLI test",
        "customer_id": "cust-003",
        "metadata": {"channel": "cli_json"},
    }


def count_statuses(results: list[IngestionResult]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for result in results:
        summary[result.status] = summary.get(result.status, 0) + 1
    return summary


def normalized_from_source(source: EventSource, payload: dict[str, Any]) -> NormalizedEvent:
    """Utility for tests that need direct adapter + validator path."""

    canonical = ADAPTERS[source](payload)
    return validate_normalized_event(canonical)
