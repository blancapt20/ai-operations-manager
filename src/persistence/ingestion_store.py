"""File-backed persistence for ingestion raw/normalized records."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.common.contracts import NormalizedEvent


def _serialize_datetime(value: datetime) -> str:
    return value.isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return _serialize_datetime(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


class IngestionStore:
    """Stores ingestion records as JSONL for local auditability."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.raw_path = self.base_dir / "raw_events.jsonl"
        self.normalized_path = self.base_dir / "normalized_events.jsonl"
        self.metadata_path = self.base_dir / "ingestion_metadata.jsonl"

    def has_event_id(self, event_id: str) -> bool:
        if not self.normalized_path.exists():
            return False
        with self.normalized_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if record.get("event_id") == event_id:
                    return True
        return False

    def persist_raw(self, source: str, payload: dict[str, Any]) -> None:
        envelope = {
            "ingested_at": datetime.utcnow().isoformat(),
            "source": source,
            "raw_payload": payload,
        }
        self._append_jsonl(self.raw_path, envelope)

    def persist_normalized(self, event: NormalizedEvent) -> None:
        record = asdict(event)
        self._append_jsonl(self.normalized_path, record)

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
        envelope = {
            "logged_at": datetime.utcnow().isoformat(),
            "event_id": event_id,
            "source": source,
            "timestamp": timestamp,
            "event_type": event_type,
            "status": status,
            "message": message,
        }
        self._append_jsonl(self.metadata_path, envelope)

    def read_jsonl(self, kind: str) -> list[dict[str, Any]]:
        target = {
            "raw": self.raw_path,
            "normalized": self.normalized_path,
            "metadata": self.metadata_path,
        }.get(kind)
        if target is None:
            raise ValueError("kind must be one of: raw, normalized, metadata")
        if not target.exists():
            return []

        records: list[dict[str, Any]] = []
        with target.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, default=_json_default) + "\n")
