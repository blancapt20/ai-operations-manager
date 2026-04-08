"""Knowledge ingestion contracts used by the RAG layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


DocumentType = Literal["policy", "case", "runbook"]
RetrievalStatus = Literal["ok", "no_context", "low_confidence"]


@dataclass(slots=True)
class KnowledgeDocument:
    document_id: str
    document_type: DocumentType
    source: str
    source_path: str
    version: str
    team: str
    created_at: datetime
    valid_from: datetime
    valid_to: datetime | None
    content: str
    content_hash: str


@dataclass(slots=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    document_type: DocumentType
    source: str
    source_path: str
    version: str
    team: str
    created_at: datetime
    valid_from: datetime
    valid_to: datetime | None
    chunk_index: int
    text: str
    content_hash: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class KnowledgeIndexBuildResult:
    mode: str
    total_files: int
    indexed_documents: int
    skipped_documents: int
    indexed_chunks: int


@dataclass(slots=True)
class RetrievedChunk:
    chunk: KnowledgeChunk
    score: float


@dataclass(slots=True)
class RetrievalResult:
    status: RetrievalStatus
    chunks: list[KnowledgeChunk]
    scores: list[float]
    warnings: list[str] = field(default_factory=list)
