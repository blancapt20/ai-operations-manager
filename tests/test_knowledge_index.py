"""RAG knowledge index tests for Sprint 3."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path

from sqlalchemy import text

from src.knowledge.service import KnowledgeIngestionService
from src.persistence.db import build_engine
from src.rag.embeddings import DeterministicEmbeddingModel
from src.rag.service import RetrievalService
from src.rag.store import KnowledgeIndexStore


ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "data" / "test_dataset"


class TestKnowledgeIndex(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.TemporaryDirectory()
        cls.database_url = f"sqlite:///{Path(cls._tmpdir.name) / 'knowledge_index.db'}"
        cls.embedding_provider = DeterministicEmbeddingModel()

        builder = KnowledgeIngestionService(
            cls.database_url,
            embedding_provider=cls.embedding_provider,
        )
        cls.build_result = builder.build_index(DATASET_ROOT, mode="full")
        builder.close()

        cls.retrieval_service = RetrievalService(
            cls.database_url,
            embedding_provider=cls.embedding_provider,
        )
        cls.engine = build_engine(cls.database_url)
        cls.store = KnowledgeIndexStore(cls.retrieval_service.session_factory)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.retrieval_service.close()
        cls.engine.dispose()
        cls._tmpdir.cleanup()

    def test_index_builds_from_sample_dataset_with_required_metadata(self) -> None:
        expected_files = len(list(DATASET_ROOT.rglob("*.json")))
        counts = self.store.counts()

        self.assertEqual(self.build_result.total_files, expected_files)
        self.assertEqual(counts["documents"], expected_files)
        self.assertEqual(counts["chunks"], counts["embeddings"])
        self.assertGreater(counts["chunks"], counts["documents"])

        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    "SELECT chunk_id, document_id, document_type, source, version, team, "
                    "created_at, valid_from, metadata "
                    "FROM knowledge_chunks ORDER BY chunk_id LIMIT 1"
                )
            ).mappings().first()

        self.assertIsNotNone(row)
        assert row is not None
        metadata = json.loads(row["metadata"])
        self.assertTrue(row["chunk_id"])
        self.assertTrue(row["document_id"])
        self.assertIn(row["document_type"], {"policy", "case", "runbook"})
        self.assertTrue(row["source"])
        self.assertTrue(row["version"])
        self.assertTrue(row["team"])
        self.assertIsNotNone(row["created_at"])
        self.assertIsNotNone(row["valid_from"])
        self.assertEqual(metadata["chunk_id"], row["chunk_id"])

    def test_incremental_reindex_is_idempotent_and_non_duplicating(self) -> None:
        builder = KnowledgeIngestionService(
            self.database_url,
            embedding_provider=self.embedding_provider,
        )
        try:
            first = builder.build_index(DATASET_ROOT, mode="incremental")
            second = builder.build_index(DATASET_ROOT, mode="incremental")
        finally:
            builder.close()

        counts = self.store.counts()
        expected_files = len(list(DATASET_ROOT.rglob("*.json")))

        self.assertEqual(first.indexed_documents, 0)
        self.assertEqual(second.indexed_documents, 0)
        self.assertEqual(first.skipped_documents, expected_files)
        self.assertEqual(second.skipped_documents, expected_files)
        self.assertEqual(counts["documents"], expected_files)

    def test_retrieval_returns_expected_chunk_in_top_k(self) -> None:
        result = self.retrieval_service.retrieve_context(
            "international parcel delayed in customs with perishable item",
            top_k=3,
        )

        self.assertEqual(result.status, "ok")
        self.assertGreaterEqual(len(result.chunks), 1)
        self.assertEqual(result.chunks[0].document_id, "case_1182_claims")

    def test_metadata_filtering_restricts_results(self) -> None:
        result = self.retrieval_service.retrieve_context(
            "company approved password manager privileged passwords not be stored in local browser",
            top_k=3,
            filters={
                "document_type": "policy",
                "team": "IT",
                "version": "2025-02-01",
            },
        )

        self.assertEqual(result.status, "ok")
        self.assertGreaterEqual(len(result.chunks), 1)
        self.assertEqual({chunk.document_id for chunk in result.chunks}, {"it_password_management_policy"})

    def test_no_relevant_documents_returns_no_context(self) -> None:
        result = self.retrieval_service.retrieve_context(
            "xylophone nebula quartzite hyperdrive foobar",
            top_k=3,
            min_similarity=0.2,
        )

        self.assertEqual(result.status, "no_context")
        self.assertEqual(result.chunks, [])
        self.assertEqual(result.scores, [])

    def test_low_similarity_returns_low_confidence(self) -> None:
        result = self.retrieval_service.retrieve_context(
            "review",
            top_k=3,
            min_similarity=0.01,
            low_confidence_threshold=0.5,
        )

        self.assertEqual(result.status, "low_confidence")
        self.assertGreaterEqual(len(result.chunks), 1)

    def test_same_query_is_deterministic(self) -> None:
        first = self.retrieval_service.retrieve_context(
            "customer requested supervisor after repeated service failures",
            top_k=5,
        )
        second = self.retrieval_service.retrieve_context(
            "customer requested supervisor after repeated service failures",
            top_k=5,
        )

        self.assertEqual(first.status, second.status)
        self.assertEqual([chunk.chunk_id for chunk in first.chunks], [chunk.chunk_id for chunk in second.chunks])
        self.assertEqual(first.scores, second.scores)

    def test_retrieval_trace_persists_chunk_ids_and_scores(self) -> None:
        case_id = "case-trace-001"
        result = self.retrieval_service.retrieve_context(
            "customer requested supervisor after repeated service failures",
            top_k=3,
            case_id=case_id,
        )

        with self.engine.begin() as connection:
            row = connection.execute(
                text(
                    "SELECT retrieval_status, retrieved_chunk_ids, scores "
                    "FROM retrieval_events WHERE case_id = :case_id "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"case_id": case_id},
            ).mappings().first()

        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["retrieval_status"], result.status)
        self.assertEqual(json.loads(row["retrieved_chunk_ids"]), [chunk.chunk_id for chunk in result.chunks])
        self.assertEqual(json.loads(row["scores"]), result.scores)

    def test_retrieval_latency_stays_within_local_threshold(self) -> None:
        started = time.perf_counter()
        self.retrieval_service.retrieve_context(
            "customer complaint escalation with repeated failures and legal threat",
            top_k=5,
        )
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 1.0)


if __name__ == "__main__":
    unittest.main()
