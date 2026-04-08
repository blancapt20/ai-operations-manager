"""Persistence helpers for knowledge chunks, embeddings, and retrieval traces."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import sessionmaker

from src.knowledge.types import KnowledgeChunk, KnowledgeDocument
from src.rag.embeddings import lexical_overlap
from src.persistence.models import (
    KnowledgeChunkEmbeddingRecord,
    KnowledgeChunkRecord,
    KnowledgeDocumentRecord,
    RetrievalEventRecord,
)


@dataclass(slots=True)
class IndexedChunkRow:
    chunk: KnowledgeChunk
    embedding: list[float]


class KnowledgeIndexStore:
    """Reads and writes knowledge-index records."""

    def __init__(self, session_factory: sessionmaker) -> None:
        self.session_factory = session_factory

    def reset_index(self) -> None:
        with self.session_factory() as session:
            session.execute(delete(KnowledgeChunkEmbeddingRecord))
            session.execute(delete(KnowledgeChunkRecord))
            session.execute(delete(KnowledgeDocumentRecord))
            session.commit()

    def document_content_hash(self, document_id: str) -> str | None:
        with self.session_factory() as session:
            return session.execute(
                select(KnowledgeDocumentRecord.content_hash).where(
                    KnowledgeDocumentRecord.document_id == document_id
                )
            ).scalar_one_or_none()

    def upsert_document(
        self,
        document: KnowledgeDocument,
        chunks: list[KnowledgeChunk],
        embeddings: dict[str, list[float]],
        *,
        embedding_model: str,
        embedding_dimensions: int,
    ) -> bool:
        with self.session_factory() as session:
            existing = session.execute(
                select(KnowledgeDocumentRecord).where(
                    KnowledgeDocumentRecord.document_id == document.document_id
                )
            ).scalar_one_or_none()
            if existing and existing.content_hash == document.content_hash:
                return False

            if existing:
                session.execute(
                    delete(KnowledgeChunkEmbeddingRecord).where(
                        KnowledgeChunkEmbeddingRecord.chunk_id.in_(
                            select(KnowledgeChunkRecord.chunk_id).where(
                                KnowledgeChunkRecord.document_id == document.document_id
                            )
                        )
                    )
                )
                session.execute(
                    delete(KnowledgeChunkRecord).where(
                        KnowledgeChunkRecord.document_id == document.document_id
                    )
                )
                existing.source = document.source
                existing.document_type = document.document_type
                existing.version = document.version
                existing.team = document.team
                existing.valid_from = document.valid_from
                existing.valid_to = document.valid_to
                existing.content_hash = document.content_hash
                existing.source_path = document.source_path
                existing.created_at = document.created_at
                existing.updated_at = datetime.utcnow()
            else:
                next_document_id = self._next_id(session, KnowledgeDocumentRecord)
                session.add(
                    KnowledgeDocumentRecord(
                        id=next_document_id,
                        document_id=document.document_id,
                        source=document.source,
                        document_type=document.document_type,
                        version=document.version,
                        team=document.team,
                        valid_from=document.valid_from,
                        valid_to=document.valid_to,
                        content_hash=document.content_hash,
                        source_path=document.source_path,
                        created_at=document.created_at,
                        updated_at=datetime.utcnow(),
                    )
                )
            session.flush()

            next_chunk_id = self._next_id(session, KnowledgeChunkRecord)
            next_embedding_id = self._next_id(session, KnowledgeChunkEmbeddingRecord)
            embedding_records: list[KnowledgeChunkEmbeddingRecord] = []
            for chunk in chunks:
                session.add(
                    KnowledgeChunkRecord(
                        id=next_chunk_id,
                        chunk_id=chunk.chunk_id,
                        document_id=chunk.document_id,
                        chunk_index=chunk.chunk_index,
                        text=chunk.text,
                        source=chunk.source,
                        document_type=chunk.document_type,
                        version=chunk.version,
                        team=chunk.team,
                        valid_from=chunk.valid_from,
                        valid_to=chunk.valid_to,
                        metadata_json=json.dumps(chunk.metadata),
                        content_hash=chunk.content_hash,
                        created_at=chunk.created_at,
                        updated_at=datetime.utcnow(),
                    )
                )
                next_chunk_id += 1
                embedding_records.append(
                    KnowledgeChunkEmbeddingRecord(
                        id=next_embedding_id,
                        chunk_id=chunk.chunk_id,
                        embedding_json=json.dumps(embeddings[chunk.chunk_id]),
                        embedding_model=embedding_model,
                        embedding_dimensions=embedding_dimensions,
                        content_hash=chunk.content_hash,
                        created_at=chunk.created_at,
                        updated_at=datetime.utcnow(),
                    )
                )
                next_embedding_id += 1
            session.flush()
            for embedding_record in embedding_records:
                session.add(embedding_record)
            session.flush()
            if self._supports_pgvector(session) and embedding_dimensions == 1536:
                session.execute(
                    text(
                        "UPDATE knowledge_chunk_embeddings "
                        "SET embedding_vector = CAST(:embedding_vector AS vector) "
                        "WHERE chunk_id = :chunk_id"
                    ),
                    [
                        {
                            "chunk_id": chunk.chunk_id,
                            "embedding_vector": _vector_literal(embeddings[chunk.chunk_id]),
                        }
                        for chunk in chunks
                    ],
                )

            session.commit()
            return True

    def fetch_indexed_chunks(self, filters: dict[str, Any] | None = None) -> list[IndexedChunkRow]:
        filters = filters or {}
        with self.session_factory() as session:
            statement = (
                select(KnowledgeChunkRecord, KnowledgeChunkEmbeddingRecord)
                .join(
                    KnowledgeChunkEmbeddingRecord,
                    KnowledgeChunkEmbeddingRecord.chunk_id == KnowledgeChunkRecord.chunk_id,
                )
                .order_by(KnowledgeChunkRecord.chunk_id)
            )
            if filters.get("document_type"):
                statement = statement.where(
                    KnowledgeChunkRecord.document_type == filters["document_type"]
                )
            if filters.get("version"):
                statement = statement.where(KnowledgeChunkRecord.version == filters["version"])
            if filters.get("team"):
                statement = statement.where(KnowledgeChunkRecord.team == filters["team"])

            rows = session.execute(statement).all()
            results: list[IndexedChunkRow] = []
            for chunk_record, embedding_record in rows:
                results.append(
                    IndexedChunkRow(
                        chunk=_build_chunk_from_record(chunk_record),
                        embedding=json.loads(embedding_record.embedding_json),
                    )
                )
            return results

    def fetch_candidate_chunks(
        self,
        query: str,
        filters: dict[str, Any] | None = None,
        *,
        candidate_limit: int = 60,
    ) -> list[KnowledgeChunk]:
        filters = filters or {}
        with self.session_factory() as session:
            statement = select(KnowledgeChunkRecord).order_by(KnowledgeChunkRecord.chunk_id)
            if filters.get("document_type"):
                statement = statement.where(
                    KnowledgeChunkRecord.document_type == filters["document_type"]
                )
            if filters.get("version"):
                statement = statement.where(KnowledgeChunkRecord.version == filters["version"])
            if filters.get("team"):
                statement = statement.where(KnowledgeChunkRecord.team == filters["team"])

            chunk_records = session.execute(statement).scalars().all()

        chunks = [_build_chunk_from_record(record) for record in chunk_records]
        if len(chunks) <= candidate_limit:
            return chunks

        scored = [
            (chunk, lexical_overlap(query, chunk.text))
            for chunk in chunks
        ]
        scored.sort(key=lambda item: (-item[1], item[0].chunk_id))

        positive_matches = [chunk for chunk, score in scored if score > 0]
        if positive_matches:
            return positive_matches[:candidate_limit]
        return [chunk for chunk, _score in scored[:candidate_limit]]

    def fetch_embeddings_for_chunk_ids(self, chunk_ids: list[str]) -> dict[str, list[float]]:
        if not chunk_ids:
            return {}
        with self.session_factory() as session:
            rows = session.execute(
                select(KnowledgeChunkEmbeddingRecord).where(
                    KnowledgeChunkEmbeddingRecord.chunk_id.in_(chunk_ids)
                )
            ).scalars().all()
        return {
            row.chunk_id: json.loads(row.embedding_json)
            for row in rows
        }

    def search_pgvector(
        self,
        query_embedding: list[float],
        filters: dict[str, Any] | None = None,
        *,
        limit: int,
    ) -> list[tuple[KnowledgeChunk, float]]:
        filters = filters or {}
        with self.session_factory() as session:
            if not self._supports_pgvector(session):
                return []

            sql_parts = [
                "SELECT",
                "  kc.chunk_id,",
                "  kc.document_id,",
                "  kc.chunk_index,",
                "  kc.text,",
                "  kc.source,",
                "  kc.document_type,",
                "  kc.version,",
                "  kc.team,",
                "  kc.valid_from,",
                "  kc.valid_to,",
                "  kc.metadata,",
                "  kc.content_hash,",
                "  kc.created_at,",
                "  (1 - (kce.embedding_vector <=> CAST(:query_vector AS vector))) AS similarity",
                "FROM knowledge_chunks kc",
                "JOIN knowledge_chunk_embeddings kce ON kce.chunk_id = kc.chunk_id",
                "WHERE kce.embedding_vector IS NOT NULL",
            ]
            params: dict[str, Any] = {
                "query_vector": _vector_literal(query_embedding),
                "limit": limit,
            }
            if filters.get("document_type"):
                sql_parts.append("AND kc.document_type = :document_type")
                params["document_type"] = filters["document_type"]
            if filters.get("version"):
                sql_parts.append("AND kc.version = :version")
                params["version"] = filters["version"]
            if filters.get("team"):
                sql_parts.append("AND kc.team = :team")
                params["team"] = filters["team"]

            sql_parts.append(
                "ORDER BY kce.embedding_vector <=> CAST(:query_vector AS vector) LIMIT :limit"
            )
            rows = session.execute(text("\n".join(sql_parts)), params).mappings().all()

        results: list[tuple[KnowledgeChunk, float]] = []
        for row in rows:
            chunk = _build_chunk_from_mapping(row)
            results.append((chunk, round(float(row["similarity"]), 6)))
        return results

    def log_retrieval_event(
        self,
        *,
        case_id: str,
        query_text: str,
        top_k: int,
        status: str,
        chunk_ids: list[str],
        scores: list[float],
    ) -> None:
        with self.session_factory() as session:
            next_retrieval_event_id = self._next_id(session, RetrievalEventRecord)
            session.add(
                RetrievalEventRecord(
                    id=next_retrieval_event_id,
                    case_id=case_id,
                    query_text=query_text,
                    top_k=top_k,
                    retrieval_status=status,
                    retrieved_chunk_ids_json=json.dumps(chunk_ids),
                    scores_json=json.dumps(scores),
                    created_at=datetime.utcnow(),
                )
            )
            session.commit()

    def counts(self) -> dict[str, int]:
        with self.session_factory() as session:
            documents = session.query(KnowledgeDocumentRecord).count()
            chunks = session.query(KnowledgeChunkRecord).count()
            embeddings = session.query(KnowledgeChunkEmbeddingRecord).count()
        return {"documents": documents, "chunks": chunks, "embeddings": embeddings}

    def _next_id(self, session: Any, model: Any) -> int:
        current_max = session.execute(select(func.max(model.id))).scalar_one()
        if current_max is None:
            return 1
        return int(current_max) + 1

    def _supports_pgvector(self, session: Any) -> bool:
        bind = session.get_bind()
        return bind is not None and bind.dialect.name == "postgresql"


def _metadata_source_path(metadata_json: str) -> str:
    metadata = json.loads(metadata_json or "{}")
    source_path = metadata.get("source_path")
    return str(source_path) if source_path else ""


def _build_chunk_from_record(chunk_record: KnowledgeChunkRecord) -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_record.chunk_id,
        document_id=chunk_record.document_id,
        document_type=(chunk_record.document_type or "policy"),
        source=chunk_record.source or "",
        source_path=_metadata_source_path(chunk_record.metadata_json),
        version=chunk_record.version or "",
        team=chunk_record.team or "",
        created_at=chunk_record.created_at,
        valid_from=chunk_record.valid_from or chunk_record.created_at,
        valid_to=chunk_record.valid_to,
        chunk_index=chunk_record.chunk_index,
        text=chunk_record.text,
        content_hash=chunk_record.content_hash or "",
        metadata=json.loads(chunk_record.metadata_json or "{}"),
    )


def _build_chunk_from_mapping(row: Any) -> KnowledgeChunk:
    metadata_json = row["metadata"] or "{}"
    return KnowledgeChunk(
        chunk_id=row["chunk_id"],
        document_id=row["document_id"],
        document_type=row["document_type"] or "policy",
        source=row["source"] or "",
        source_path=_metadata_source_path(metadata_json),
        version=row["version"] or "",
        team=row["team"] or "",
        created_at=row["created_at"],
        valid_from=row["valid_from"] or row["created_at"],
        valid_to=row["valid_to"],
        chunk_index=row["chunk_index"],
        text=row["text"],
        content_hash=row["content_hash"] or "",
        metadata=json.loads(metadata_json),
    )


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(value, ".12g") for value in values) + "]"
