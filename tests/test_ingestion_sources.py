"""Source adapter parity tests for Sprint 2."""

from __future__ import annotations

import unittest

from src.common.contracts import EventSource
from src.common.validation import ValidationError
from src.ingestion.service import normalized_from_source


class TestSourceParity(unittest.TestCase):
    def test_email_happy_path(self) -> None:
        payload = {
            "id": "email-test-1",
            "received_at": "2026-03-30T15:00:00Z",
            "subject": "Charge discrepancy",
            "body": "I see two charges for one plan.",
            "customer_id": "cust-e1",
        }
        event = normalized_from_source(EventSource.EMAIL, payload)
        self.assertEqual(event.event_id, "email-test-1")
        self.assertEqual(event.source, EventSource.EMAIL)

    def test_email_invalid_path(self) -> None:
        payload = {
            "id": "email-bad-1",
            "subject": "Missing timestamp/body",
        }
        with self.assertRaises(ValidationError):
            normalized_from_source(EventSource.EMAIL, payload)

    def test_tickets_happy_path(self) -> None:
        payload = {
            "ticket_id": "ticket-test-1",
            "created_at": "2026-03-30T15:01:00Z",
            "issue_type": "billing_dispute",
            "description": "Duplicate invoice line.",
            "requester_id": "cust-t1",
        }
        event = normalized_from_source(EventSource.TICKETS, payload)
        self.assertEqual(event.event_id, "ticket-test-1")
        self.assertEqual(event.source, EventSource.TICKETS)

    def test_tickets_invalid_path(self) -> None:
        payload = {"ticket_id": "ticket-bad-1", "created_at": "2026-03-30T15:01:00Z"}
        with self.assertRaises(ValidationError):
            normalized_from_source(EventSource.TICKETS, payload)

    def test_internal_events_happy_path(self) -> None:
        payload = {
            "event_id": "internal-test-1",
            "timestamp": "2026-03-30T15:02:00Z",
            "event_name": "billing_alert",
            "message": "Potential duplicate charge.",
        }
        event = normalized_from_source(EventSource.INTERNAL_EVENTS, payload)
        self.assertEqual(event.event_id, "internal-test-1")
        self.assertEqual(event.source, EventSource.INTERNAL_EVENTS)

    def test_internal_events_invalid_path(self) -> None:
        payload = {"event_id": "internal-bad-1", "timestamp": "2026-03-30T15:02:00Z"}
        with self.assertRaises(ValidationError):
            normalized_from_source(EventSource.INTERNAL_EVENTS, payload)

    def test_cli_json_happy_path(self) -> None:
        payload = {
            "event_id": "cli-test-1",
            "timestamp": "2026-03-30T15:03:00Z",
            "event_type": "billing_dispute",
            "body": "Synthetic event",
        }
        event = normalized_from_source(EventSource.CLI_JSON, payload)
        self.assertEqual(event.event_id, "cli-test-1")
        self.assertEqual(event.source, EventSource.CLI_JSON)

    def test_cli_json_invalid_path(self) -> None:
        payload = {"event_id": "cli-bad-1", "timestamp": "2026-03-30T15:03:00Z"}
        with self.assertRaises(ValidationError):
            normalized_from_source(EventSource.CLI_JSON, payload)


if __name__ == "__main__":
    unittest.main()
