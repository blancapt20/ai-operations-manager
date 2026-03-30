"""Schema validation tests for Sprint 1 contracts."""

from __future__ import annotations

import unittest

from src.common.contracts import EventSource, StepStatus
from src.common.validation import (
    ValidationError,
    validate_execution_trace_step,
    validate_normalized_event,
    validate_processing_result,
)


class TestNormalizedEventValidation(unittest.TestCase):
    def test_accepts_valid_events_from_all_sources(self) -> None:
        for source in EventSource:
            with self.subTest(source=source.value):
                payload = {
                    "event_id": f"evt-{source.value}",
                    "source": source.value,
                    "timestamp": "2026-03-30T12:00:00Z",
                    "event_type": "billing_dispute",
                    "body": "I was charged twice.",
                    "metadata": {"channel_id": "sample-1"},
                }
                event = validate_normalized_event(payload)
                self.assertEqual(event.source, source)
                self.assertEqual(event.event_id, f"evt-{source.value}")

    def test_rejects_malformed_payload(self) -> None:
        payload = {
            "event_id": "evt-invalid",
            "source": "email",
            "timestamp": "not-a-timestamp",
            "event_type": "billing_dispute",
            "body": "bad timestamp test",
        }
        with self.assertRaisesRegex(ValidationError, "ISO-8601"):
            validate_normalized_event(payload)


class TestProcessingContracts(unittest.TestCase):
    def test_processing_result_contract(self) -> None:
        payload = {
            "case_id": "case-1",
            "event_id": "evt-1",
            "classification": "refund_candidate",
            "rationale": "duplicate charge evidence found",
            "action": "refund_service",
            "response_text": "We have initiated a refund.",
            "confidence": 0.91,
            "flags": ["needs_audit_log"],
            "created_at": "2026-03-30T12:00:00Z",
        }
        result = validate_processing_result(payload)
        self.assertEqual(result.case_id, "case-1")
        self.assertEqual(result.flags, ["needs_audit_log"])

    def test_trace_step_contract(self) -> None:
        payload = {
            "case_id": "case-1",
            "step_name": "ingestion",
            "status": StepStatus.SUCCESS.value,
            "started_at": "2026-03-30T12:00:00Z",
            "finished_at": "2026-03-30T12:00:01Z",
            "latency_ms": 1000,
            "details": {"records_written": 1},
        }
        step = validate_execution_trace_step(payload)
        self.assertEqual(step.step_name, "ingestion")
        self.assertEqual(step.status, StepStatus.SUCCESS)


if __name__ == "__main__":
    unittest.main()
