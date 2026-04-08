"""End-to-end pipeline tests for grounded retrieval orchestration."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text

from src.agent.service import PipelineService
from src.common.contracts import EventSource
from src.ingestion.service import IngestionService
from src.knowledge.service import KnowledgeIngestionService
from src.persistence.db import build_engine
from src.rag.embeddings import DeterministicEmbeddingModel


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "data" / "test_dataset"


class TestPipelineFlow(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.database_url = f"sqlite:///{Path(self._tmpdir.name) / 'pipeline.db'}"
        self.embedding_provider = DeterministicEmbeddingModel()

        index_builder = KnowledgeIngestionService(
            self.database_url,
            embedding_provider=self.embedding_provider,
        )
        index_builder.build_index(DATASET_ROOT, mode="full")
        index_builder.close()

        ingestion_service = IngestionService(database_url=self.database_url)
        try:
            payload = {
                "id": "email-pipeline-1",
                "received_at": "2026-04-08T10:00:00Z",
                "subject": "Duplicate charge complaint",
                "body": "I was charged twice for my subscription and want this fixed.",
                "customer_id": "cust-pipeline-1",
            }
            result = ingestion_service.ingest_payload(EventSource.EMAIL, payload)
            self.assertEqual(result.status, "accepted")
        finally:
            ingestion_service.close()

        self.engine = build_engine(self.database_url)

    def tearDown(self) -> None:
        self.engine.dispose()
        self._tmpdir.cleanup()

    def test_pipeline_processes_pending_event_with_retrieval_trace(self) -> None:
        pipeline_service = PipelineService(
            self.database_url,
            embedding_provider=self.embedding_provider,
        )
        try:
            summary = pipeline_service.process_pending_events(limit=5)
        finally:
            pipeline_service.close()

        self.assertEqual(summary.processed, 1)
        self.assertEqual(len(summary.cases), 1)
        self.assertEqual(summary.cases[0]["event_id"], "email-pipeline-1")
        self.assertGreaterEqual(len(summary.cases[0]["retrieved_chunk_ids"]), 1)

        with self.engine.begin() as connection:
            case_row = connection.execute(
                text("SELECT case_id, event_id, status, classification, action FROM cases")
            ).mappings().first()
            trace_rows = connection.execute(
                text("SELECT step_name, details FROM execution_trace_steps ORDER BY id")
            ).mappings().all()
            retrieval_row = connection.execute(
                text(
                    "SELECT query_text, retrieval_status, retrieved_chunk_ids, scores "
                    "FROM retrieval_events ORDER BY id DESC LIMIT 1"
                )
            ).mappings().first()

        self.assertIsNotNone(case_row)
        self.assertIsNotNone(retrieval_row)
        assert case_row is not None
        assert retrieval_row is not None
        self.assertEqual(case_row["event_id"], "email-pipeline-1")
        self.assertIn(case_row["status"], {"processed", "needs_review", "no_context"})
        self.assertEqual([row["step_name"] for row in trace_rows], ["retrieve_context", "grounded_decision"])
        self.assertIn("Duplicate charge complaint", retrieval_row["query_text"])
        self.assertGreaterEqual(len(json.loads(retrieval_row["retrieved_chunk_ids"])), 1)
        self.assertGreaterEqual(len(json.loads(retrieval_row["scores"])), 1)

    def test_pipeline_dry_run_previews_queries_without_creating_cases(self) -> None:
        pipeline_service = PipelineService(
            self.database_url,
            embedding_provider=self.embedding_provider,
        )
        try:
            summary = pipeline_service.process_pending_events(limit=5, dry_run=True)
        finally:
            pipeline_service.close()

        self.assertEqual(summary.processed, 0)
        self.assertEqual(len(summary.cases), 1)
        self.assertIn("Duplicate charge complaint", str(summary.cases[0]["query"]))

        with self.engine.begin() as connection:
            case_count = connection.execute(text("SELECT COUNT(*) FROM cases")).scalar_one()
        self.assertEqual(case_count, 0)


if __name__ == "__main__":
    unittest.main()
