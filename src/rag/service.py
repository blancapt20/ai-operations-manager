"""Retrieval service contract used by downstream decision logic."""

from __future__ import annotations

from pathlib import Path

from src.knowledge.types import KnowledgeChunk, RetrievalResult
from src.persistence.db import build_engine, build_session_factory
from src.persistence.migrations import apply_migrations
from src.rag.embeddings import EmbeddingProvider, build_embedding_provider, combined_similarity
from src.rag.store import KnowledgeIndexStore


class RetrievalService:
    """Provides filterable retrieval over indexed knowledge chunks."""

    def __init__(
        self,
        database_url: str,
        *,
        embedding_model_name: str = "text-embedding-3-small",
        embedding_api_key: str | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.engine = build_engine(database_url)
        apply_migrations(self.engine, Path(__file__).resolve().parents[2] / "migrations")
        self.session_factory = build_session_factory(self.engine)
        self.store = KnowledgeIndexStore(self.session_factory)
        self.embedding_model = embedding_provider or build_embedding_provider(
            model_name=embedding_model_name,
            openai_api_key=embedding_api_key,
        )

    def close(self) -> None:
        self.engine.dispose()

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        min_similarity: float = 0.18,
        *,
        low_confidence_threshold: float = 0.25,
        candidate_limit: int | None = None,
        case_id: str | None = None,
    ) -> RetrievalResult:
        filters = filters or {}
        query_vector = self.embedding_model.embed(query)
        ranked = self.store.search_pgvector(
            query_vector,
            filters,
            limit=max(top_k * 5, 25),
        )
        if not ranked:
            candidate_limit = candidate_limit or max(top_k * 12, 60)
            candidate_chunks = self.store.fetch_candidate_chunks(
                query,
                filters,
                candidate_limit=candidate_limit,
            )
            if not candidate_chunks:
                result = RetrievalResult(status="no_context", chunks=[], scores=[])
                self._trace(case_id, query, top_k, result)
                return result

            embeddings_by_chunk_id = self.store.fetch_embeddings_for_chunk_ids(
                [chunk.chunk_id for chunk in candidate_chunks]
            )
            ranked = [
                (
                    chunk,
                    combined_similarity(
                        query,
                        chunk.text,
                        query_vector,
                        embeddings_by_chunk_id.get(chunk.chunk_id, []),
                    ),
                )
                for chunk in candidate_chunks
                if chunk.chunk_id in embeddings_by_chunk_id
            ]
        ranked = [item for item in ranked if item[1] >= min_similarity]
        ranked.sort(key=lambda item: (-item[1], item[0].chunk_id))
        selected = ranked[:top_k]

        if not selected:
            result = RetrievalResult(status="no_context", chunks=[], scores=[])
            self._trace(case_id, query, top_k, result)
            return result

        chunks = [chunk for chunk, _score in selected]
        scores = [round(score, 6) for _chunk, score in selected]
        status = "ok" if scores[0] >= low_confidence_threshold else "low_confidence"
        warnings = []
        if _has_conflicting_documents(chunks, scores):
            warnings.append("conflicting_documents")

        result = RetrievalResult(status=status, chunks=chunks, scores=scores, warnings=warnings)
        self._trace(case_id, query, top_k, result)
        return result

    def _trace(self, case_id: str | None, query: str, top_k: int, result: RetrievalResult) -> None:
        if not case_id:
            return
        self.store.log_retrieval_event(
            case_id=case_id,
            query_text=query,
            top_k=top_k,
            status=result.status,
            chunk_ids=[chunk.chunk_id for chunk in result.chunks],
            scores=result.scores,
        )


def _has_conflicting_documents(chunks: list[KnowledgeChunk], scores: list[float]) -> bool:
    if len(chunks) < 2 or len(scores) < 2:
        return False
    if abs(scores[0] - scores[1]) > 0.03:
        return False
    return chunks[0].document_id != chunks[1].document_id
