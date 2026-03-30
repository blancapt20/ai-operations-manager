"""Canonical contracts used across the Milestone 0A pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EventSource(str, Enum):
    EMAIL = "email"
    TICKETS = "tickets"
    INTERNAL_EVENTS = "internal_events"
    CLI_JSON = "cli_json"


class StepStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"


@dataclass(slots=True)
class NormalizedEvent:
    """Canonical input event format for all ingestion sources."""

    event_id: str
    source: EventSource
    timestamp: datetime
    event_type: str
    body: str
    subject: str | None = None
    customer_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessingResult:
    """Contract for agent decision outputs."""

    case_id: str
    event_id: str
    classification: str
    rationale: str
    action: str
    response_text: str
    confidence: float | None = None
    flags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class ExecutionTraceStep:
    """A single step in pipeline execution trace metadata."""

    case_id: str
    step_name: str
    status: StepStatus
    started_at: datetime
    finished_at: datetime
    latency_ms: int
    details: dict[str, Any] = field(default_factory=dict)
