"""Validation helpers for canonical contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from src.common.contracts import (
    EventSource,
    ExecutionTraceStep,
    NormalizedEvent,
    ProcessingResult,
    StepStatus,
)


class ValidationError(ValueError):
    """Raised when incoming data does not satisfy contract requirements."""


def _required_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"'{key}' must be a non-empty string")
    return value.strip()


def _optional_str(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(f"'{key}' must be a string when provided")
    return value.strip() or None


def _required_datetime(payload: Mapping[str, Any], key: str) -> datetime:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValidationError(f"'{key}' must be an ISO-8601 string")
    raw = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValidationError(f"'{key}' must be a valid ISO-8601 datetime") from exc


def validate_normalized_event(payload: Mapping[str, Any]) -> NormalizedEvent:
    """Build and validate a normalized event from a generic payload."""

    event_id = _required_str(payload, "event_id")
    event_type = _required_str(payload, "event_type")
    body = _required_str(payload, "body")
    source_raw = _required_str(payload, "source")
    timestamp = _required_datetime(payload, "timestamp")

    try:
        source = EventSource(source_raw)
    except ValueError as exc:
        valid = ", ".join(item.value for item in EventSource)
        raise ValidationError(f"'source' must be one of: {valid}") from exc

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValidationError("'metadata' must be a dictionary when provided")

    return NormalizedEvent(
        event_id=event_id,
        source=source,
        timestamp=timestamp,
        event_type=event_type,
        body=body,
        subject=_optional_str(payload, "subject"),
        customer_id=_optional_str(payload, "customer_id"),
        metadata=metadata,
    )


def validate_processing_result(payload: Mapping[str, Any]) -> ProcessingResult:
    """Build and validate a processing result contract."""

    confidence = payload.get("confidence")
    if confidence is not None and not isinstance(confidence, (float, int)):
        raise ValidationError("'confidence' must be a number when provided")

    flags = payload.get("flags", [])
    if not isinstance(flags, list) or not all(isinstance(item, str) for item in flags):
        raise ValidationError("'flags' must be a list of strings")

    created_at_raw = payload.get("created_at")
    if created_at_raw is None:
        created_at = datetime.utcnow()
    else:
        created_at = _required_datetime(payload, "created_at")

    return ProcessingResult(
        case_id=_required_str(payload, "case_id"),
        event_id=_required_str(payload, "event_id"),
        classification=_required_str(payload, "classification"),
        rationale=_required_str(payload, "rationale"),
        action=_required_str(payload, "action"),
        response_text=_required_str(payload, "response_text"),
        confidence=float(confidence) if confidence is not None else None,
        flags=flags,
        created_at=created_at,
    )


def validate_execution_trace_step(payload: Mapping[str, Any]) -> ExecutionTraceStep:
    """Build and validate a trace step contract."""

    status_raw = _required_str(payload, "status")
    try:
        status = StepStatus(status_raw)
    except ValueError as exc:
        valid = ", ".join(item.value for item in StepStatus)
        raise ValidationError(f"'status' must be one of: {valid}") from exc

    latency_ms = payload.get("latency_ms")
    if not isinstance(latency_ms, int) or latency_ms < 0:
        raise ValidationError("'latency_ms' must be a non-negative integer")

    details = payload.get("details", {})
    if not isinstance(details, dict):
        raise ValidationError("'details' must be a dictionary when provided")

    started_at = _required_datetime(payload, "started_at")
    finished_at = _required_datetime(payload, "finished_at")
    if finished_at < started_at:
        raise ValidationError("'finished_at' must be greater than or equal to 'started_at'")

    return ExecutionTraceStep(
        case_id=_required_str(payload, "case_id"),
        step_name=_required_str(payload, "step_name"),
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        latency_ms=latency_ms,
        details=details,
    )
