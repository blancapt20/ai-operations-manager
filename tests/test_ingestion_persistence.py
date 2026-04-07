"""Persistence, dedup, and batch ingestion smoke tests for Sprint 2."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from src.common.contracts import EventSource
from src.ingestion.service import IngestionService, default_payload_for


ROOT = Path(__file__).resolve().parents[1]


class TestIngestionPersistence(unittest.TestCase):
    def test_strict_mode_requires_input_without_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database_url = f"sqlite:///{Path(tmp) / 'strict.db'}"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "run_ingestion.py"),
                "--source",
                "email",
            ]
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                env={**os.environ, "DATABASE_URL": database_url},
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("missing input", completed.stderr.lower())

    def test_use_defaults_flag_allows_demo_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database_url = f"sqlite:///{Path(tmp) / 'defaults.db'}"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "run_ingestion.py"),
                "--source",
                "email",
                "--use-defaults",
                "--run-migrations",
            ]
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                env={**os.environ, "DATABASE_URL": database_url},
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            service = IngestionService(database_url=database_url)
            try:
                normalized_records = service.store.read_records("normalized")
            finally:
                service.close()
            self.assertEqual(len(normalized_records), 1)

    def test_raw_and_normalized_records_are_persisted_with_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database_url = f"sqlite:///{Path(tmp) / 'records.db'}"
            service = IngestionService(database_url=database_url)
            try:
                result = service.ingest_payload(EventSource.EMAIL, default_payload_for(EventSource.EMAIL))
                self.assertEqual(result.status, "accepted")

                raw = service.store.read_records("raw")
                normalized = service.store.read_records("normalized")
                metadata = service.store.read_records("metadata")
            finally:
                service.close()

            self.assertEqual(len(raw), 1)
            self.assertEqual(len(normalized), 1)
            self.assertEqual(len(metadata), 1)

            meta = metadata[0]
            self.assertIn("source", meta)
            self.assertIn("timestamp", meta)
            self.assertIn("event_type", meta)
            self.assertIn("status", meta)
            self.assertEqual(meta["status"], "accepted")

    def test_duplicate_event_id_policy_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database_url = f"sqlite:///{Path(tmp) / 'duplicate.db'}"
            service = IngestionService(database_url=database_url)
            try:
                payload = default_payload_for(EventSource.CLI_JSON)
                first = service.ingest_payload(EventSource.CLI_JSON, payload)
                second = service.ingest_payload(EventSource.CLI_JSON, payload)

                self.assertEqual(first.status, "accepted")
                self.assertEqual(second.status, "duplicate_skipped")

                normalized = service.store.read_records("normalized")
                metadata = service.store.read_records("metadata")
            finally:
                service.close()
            self.assertEqual(len(normalized), 1)
            self.assertEqual(len(metadata), 2)
            self.assertEqual(metadata[-1]["status"], "duplicate_skipped")

    def test_e2e_mixed_source_batch_script_persists_expected_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database_url = f"sqlite:///{Path(tmp) / 'batch.db'}"
            batch_file = ROOT / "data" / "samples" / "mixed_source_batch.json"
            command = [
                sys.executable,
                str(ROOT / "scripts" / "run_ingestion.py"),
                "--batch-file",
                str(batch_file),
                "--run-migrations",
            ]
            completed = subprocess.run(
                command,
                cwd=str(ROOT),
                text=True,
                capture_output=True,
                env={**os.environ, "DATABASE_URL": database_url},
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)

            service = IngestionService(database_url=database_url)
            try:
                normalized_records = service.store.read_records("normalized")
            finally:
                service.close()
            self.assertEqual(len(normalized_records), 4)


if __name__ == "__main__":
    unittest.main()
