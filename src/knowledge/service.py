"""Knowledge document ingestion and indexing orchestration."""

from __future__ import annotations

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from src.knowledge.chunking import chunk_document
from src.knowledge.types import KnowledgeDocument, KnowledgeIndexBuildResult
from src.persistence.db import build_engine, build_session_factory
from src.persistence.migrations import apply_migrations
from src.rag.embeddings import EmbeddingProvider, build_embedding_provider
from src.rag.store import KnowledgeIndexStore


class KnowledgeIngestionService:
    """Builds a knowledge index from JSON source documents."""

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

    def build_index(
        self,
        dataset_path: str | Path,
        *,
        mode: str = "full",
        dry_run: bool = False,
    ) -> KnowledgeIndexBuildResult:
        dataset_root = Path(dataset_path)
        if not dataset_root.exists():
            raise FileNotFoundError(f"Knowledge dataset path does not exist: {dataset_root}")

        files = sorted(dataset_root.rglob("*.json"))
        if mode == "full" and not dry_run:
            self.store.reset_index()

        indexed_documents = 0
        skipped_documents = 0
        indexed_chunks = 0

        for file_path in files:
            document = load_knowledge_document(file_path, dataset_root)
            if mode == "incremental" and self.store.document_content_hash(document.document_id) == document.content_hash:
                skipped_documents += 1
                continue

            chunks = chunk_document(document)
            vectors = self.embedding_model.embed_many([chunk.text for chunk in chunks])
            embeddings = {
                chunk.chunk_id: vector
                for chunk, vector in zip(chunks, vectors, strict=True)
            }
            embedding_dimensions = len(vectors[0]) if vectors else 0

            if not dry_run:
                changed = self.store.upsert_document(
                    document,
                    chunks,
                    embeddings,
                    embedding_model=self.embedding_model.model_name,
                    embedding_dimensions=embedding_dimensions,
                )
                if not changed:
                    skipped_documents += 1
                    continue

            indexed_documents += 1
            indexed_chunks += len(chunks)

        return KnowledgeIndexBuildResult(
            mode=mode,
            total_files=len(files),
            indexed_documents=indexed_documents,
            skipped_documents=skipped_documents,
            indexed_chunks=indexed_chunks,
        )


def load_knowledge_document(file_path: str | Path, dataset_root: str | Path | None = None) -> KnowledgeDocument:
    path = Path(file_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    created_at = _parse_datetime(payload["created_at"])
    valid_from = _parse_valid_from(payload, created_at)
    valid_to = _parse_datetime(payload["valid_to"]) if payload.get("valid_to") else None
    canonical_payload = json.dumps(payload, sort_keys=True)

    source_path = path.as_posix()
    if dataset_root:
        source_path = path.relative_to(Path(dataset_root)).as_posix()

    return KnowledgeDocument(
        document_id=path.stem,
        document_type=_normalize_document_type(payload.get("document_type", "")),
        source=str(payload["source"]).strip(),
        source_path=source_path,
        version=str(payload["version"]).strip(),
        team=str(payload["team"]).strip(),
        created_at=created_at,
        valid_from=valid_from,
        valid_to=valid_to,
        content=str(payload["content"]).strip(),
        content_hash=sha256(canonical_payload.encode("utf-8")).hexdigest(),
    )


def _normalize_document_type(raw_value: str) -> str:
    value = raw_value.strip().lower()
    if value in {"policy", "knowledge base", "manual", "guide", "knowledge_base"}:
        return "policy"
    if value in {"historical case", "case"}:
        return "case"
    if value in {"runbook", "playbook", "procedure", "workflow", "sop"}:
        return "runbook"
    if "policy" in value or "manual" in value or "wiki" in value:
        return "policy"
    if "case" in value:
        return "case"
    if "runbook" in value or "playbook" in value or "procedure" in value:
        return "runbook"
    raise ValueError(f"Unsupported knowledge document_type: {raw_value}")


def _parse_datetime(value: Any) -> datetime:
    text = str(value).strip()
    if len(text) == 10:
        text = f"{text}T00:00:00"
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def _parse_valid_from(payload: dict[str, Any], created_at: datetime) -> datetime:
    if payload.get("valid_from"):
        return _parse_datetime(payload["valid_from"])
    version = payload.get("version")
    if version:
        try:
            return _parse_datetime(version)
        except ValueError:
            pass
    return created_at
