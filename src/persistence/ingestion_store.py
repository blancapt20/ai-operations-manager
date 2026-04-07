"""Database-backed persistence for ingestion records."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from src.common.contracts import NormalizedEvent
from src.persistence.models import (
    IngestionMetadataRecord,
    NormalizedEventRecord,
    RawEvent,
)


class IngestionStore:
    """Stores ingestion records in SQL tables."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def has_event_id(self, event_id: str) -> bool:
        with self.session_factory() as session:
            existing = session.execute(
                select(NormalizedEventRecord.id).where(NormalizedEventRecord.event_id == event_id)
            ).first()
            return existing is not None

    def persist_raw(self, source: str, payload: dict[str, Any]) -> None:
        with self.session_factory() as session:
            next_id = self._next_id(session, RawEvent)
            session.add(
                RawEvent(
                    id=next_id,
                    ingested_at=datetime.utcnow(),
                    source=source,
                    raw_payload=json.dumps(payload),
                )
            )
            session.commit()

    def persist_normalized(self, event: NormalizedEvent) -> None:
        with self.session_factory() as session:
            next_id = self._next_id(session, NormalizedEventRecord)
            session.add(
                NormalizedEventRecord(
                    id=next_id,
                    event_id=event.event_id,
                    source=event.source.value,
                    timestamp=event.timestamp,
                    event_type=event.event_type,
                    body=event.body,
                    subject=event.subject,
                    customer_id=event.customer_id,
                    metadata_json=json.dumps(event.metadata),
                    created_at=datetime.utcnow(),
                )
            )
            session.commit()

    def persist_metadata(
        self,
        *,
        event_id: str,
        source: str,
        event_type: str,
        timestamp: str,
        status: str,
        message: str | None = None,
    ) -> None:
        with self.session_factory() as session:
            next_id = self._next_id(session, IngestionMetadataRecord)
            session.add(
                IngestionMetadataRecord(
                    id=next_id,
                    logged_at=datetime.utcnow(),
                    event_id=event_id,
                    source=source,
                    timestamp=_parse_iso_datetime(timestamp),
                    event_type=event_type,
                    status=status,
                    message=message,
                )
            )
            session.commit()

    def read_records(self, kind: str) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            if kind == "raw":
                rows = session.execute(select(RawEvent).order_by(RawEvent.id)).scalars().all()
                return [
                    {
                        "id": row.id,
                        "ingested_at": row.ingested_at.isoformat(),
                        "source": row.source,
                        "raw_payload": json.loads(row.raw_payload),
                    }
                    for row in rows
                ]
            if kind == "normalized":
                rows = session.execute(
                    select(NormalizedEventRecord).order_by(NormalizedEventRecord.id)
                ).scalars().all()
                return [
                    {
                        "id": row.id,
                        "event_id": row.event_id,
                        "source": row.source,
                        "timestamp": row.timestamp.isoformat(),
                        "event_type": row.event_type,
                        "body": row.body,
                        "subject": row.subject,
                        "customer_id": row.customer_id,
                        "metadata": json.loads(row.metadata_json),
                    }
                    for row in rows
                ]
            if kind == "metadata":
                rows = session.execute(
                    select(IngestionMetadataRecord).order_by(IngestionMetadataRecord.id)
                ).scalars().all()
                return [
                    {
                        "id": row.id,
                        "logged_at": row.logged_at.isoformat(),
                        "event_id": row.event_id,
                        "source": row.source,
                        "timestamp": row.timestamp.isoformat(),
                        "event_type": row.event_type,
                        "status": row.status,
                        "message": row.message,
                    }
                    for row in rows
                ]
        raise ValueError("kind must be one of: raw, normalized, metadata")

    def _next_id(self, session: Any, model: Any) -> int:
        current_max = session.execute(select(func.max(model.id))).scalar_one()
        if current_max is None:
            return 1
        return int(current_max) + 1


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
