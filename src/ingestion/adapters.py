"""Source-specific ingestion adapters for canonical normalization."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.common.contracts import EventSource
from src.common.validation import ValidationError


def _require_str(payload: Mapping[str, Any], key: str, source: EventSource) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{source.value}: '{key}' must be a non-empty string")
    return value.strip()


def from_email(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = EventSource.EMAIL
    event_id = _require_str(payload, "id", source)
    timestamp = _require_str(payload, "received_at", source)
    body = _require_str(payload, "body", source)
    subject = _require_str(payload, "subject", source)

    canonical: dict[str, Any] = {
        "event_id": event_id,
        "source": source.value,
        "timestamp": timestamp,
        "event_type": payload.get("event_type", "customer_email"),
        "subject": subject,
        "body": body,
        "customer_id": payload.get("customer_id"),
        "metadata": {
            "channel": "email",
            "sender": payload.get("sender"),
            "thread_id": payload.get("thread_id"),
        },
    }
    return canonical


def from_tickets(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = EventSource.TICKETS
    event_id = _require_str(payload, "ticket_id", source)
    timestamp = _require_str(payload, "created_at", source)
    event_type = _require_str(payload, "issue_type", source)
    body = _require_str(payload, "description", source)

    canonical: dict[str, Any] = {
        "event_id": event_id,
        "source": source.value,
        "timestamp": timestamp,
        "event_type": event_type,
        "subject": payload.get("title") or event_type,
        "body": body,
        "customer_id": payload.get("requester_id"),
        "metadata": {
            "channel": "tickets",
            "priority": payload.get("priority"),
            "queue": payload.get("queue"),
        },
    }
    return canonical


def from_internal_events(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = EventSource.INTERNAL_EVENTS
    event_id = _require_str(payload, "event_id", source)
    timestamp = _require_str(payload, "timestamp", source)
    event_type = _require_str(payload, "event_name", source)
    body = _require_str(payload, "message", source)

    canonical: dict[str, Any] = {
        "event_id": event_id,
        "source": source.value,
        "timestamp": timestamp,
        "event_type": event_type,
        "subject": payload.get("title") or event_type,
        "body": body,
        "customer_id": payload.get("customer_id"),
        "metadata": {
            "channel": "internal_events",
            "service": payload.get("service"),
            "severity": payload.get("severity"),
        },
    }
    return canonical


def from_cli_json(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = EventSource.CLI_JSON
    event_type = _require_str(payload, "event_type", source)
    canonical: dict[str, Any] = {
        "event_id": _require_str(payload, "event_id", source),
        "source": source.value,
        "timestamp": _require_str(payload, "timestamp", source),
        "event_type": event_type,
        "subject": payload.get("subject") or event_type,
        "body": _require_str(payload, "body", source),
        "customer_id": payload.get("customer_id"),
        "metadata": payload.get("metadata", {"channel": "cli_json"}),
    }
    return canonical


ADAPTERS = {
    EventSource.EMAIL: from_email,
    EventSource.TICKETS: from_tickets,
    EventSource.INTERNAL_EVENTS: from_internal_events,
    EventSource.CLI_JSON: from_cli_json,
}
