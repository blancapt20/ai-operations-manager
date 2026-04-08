"""Semantic chunking helpers for business knowledge documents."""

from __future__ import annotations

import re
from hashlib import sha256

from src.knowledge.types import KnowledgeChunk, KnowledgeDocument


HEADING_PREFIXES = (
    "purpose",
    "scope",
    "procedure",
    "steps taken",
    "resolution",
    "follow-up",
    "approval requirements",
    "communication standards",
    "completion criteria",
    "entries",
    "related documents",
    "when to use",
    "responsible roles",
    "password requirements",
    "multi-factor authentication",
    "reset and recovery",
    "service accounts and rotation",
    "compliance and enforcement",
    "user awareness",
    "credential reporting",
)


def chunk_document(
    document: KnowledgeDocument,
    *,
    max_chunk_chars: int = 900,
) -> list[KnowledgeChunk]:
    """Split a document into heading-aware chunks without breaking key rules."""

    blocks = [_normalize_block(block) for block in re.split(r"\n\s*\n", document.content) if block.strip()]
    chunks: list[KnowledgeChunk] = []
    active_heading: str | None = None
    bucket: list[str] = []

    for block in blocks:
        if _looks_like_heading(block):
            if bucket:
                chunks.append(_build_chunk(document, len(chunks), active_heading, bucket))
                bucket = []
            active_heading = block.strip()
            continue

        candidate_parts = list(bucket)
        if active_heading and not candidate_parts:
            candidate_parts.append(active_heading)
        candidate_parts.append(block)
        candidate_text = "\n\n".join(candidate_parts)

        if bucket and len(candidate_text) > max_chunk_chars:
            chunks.append(_build_chunk(document, len(chunks), active_heading, bucket))
            bucket = [block]
        else:
            bucket.append(block)

        if _should_flush(block):
            chunks.append(_build_chunk(document, len(chunks), active_heading, bucket))
            bucket = []

    if bucket:
        chunks.append(_build_chunk(document, len(chunks), active_heading, bucket))

    return chunks


def _build_chunk(
    document: KnowledgeDocument,
    chunk_index: int,
    heading: str | None,
    blocks: list[str],
) -> KnowledgeChunk:
    parts = list(blocks)
    if heading:
        parts.insert(0, heading)
    text = "\n\n".join(part for part in parts if part.strip())
    content_hash = sha256(f"{document.document_id}:{chunk_index}:{text}".encode("utf-8")).hexdigest()
    return KnowledgeChunk(
        chunk_id=f"{document.document_id}::chunk::{chunk_index:03d}",
        document_id=document.document_id,
        document_type=document.document_type,
        source=document.source,
        source_path=document.source_path,
        version=document.version,
        team=document.team,
        created_at=document.created_at,
        valid_from=document.valid_from,
        valid_to=document.valid_to,
        chunk_index=chunk_index,
        text=text,
        content_hash=content_hash,
        metadata={
            "chunk_id": f"{document.document_id}::chunk::{chunk_index:03d}",
            "document_id": document.document_id,
            "document_type": document.document_type,
            "source": document.source,
            "version": document.version,
            "team": document.team,
            "created_at": document.created_at.isoformat(),
            "valid_from": document.valid_from.isoformat(),
            "valid_to": document.valid_to.isoformat() if document.valid_to else None,
            "source_path": document.source_path,
            "chunk_index": chunk_index,
            "heading": heading,
        },
    )


def _normalize_block(block: str) -> str:
    lines = [line.strip() for line in block.splitlines()]
    return "\n".join(line for line in lines if line)


def _looks_like_heading(block: str) -> bool:
    lines = block.splitlines()
    if len(lines) > 2:
        return False
    text = " ".join(lines).strip()
    lowered = text.lower().rstrip(":")
    if lowered.startswith(HEADING_PREFIXES):
        return True
    if len(text.split()) > 8:
        return False
    if text.endswith((".", "?", "!")):
        return False
    return text == text.title() or text == text.upper() or text.endswith(":")


def _should_flush(block: str) -> bool:
    lowered = block.lower()
    if lowered.startswith("step 1:") or lowered.startswith("1. q:"):
        return False
    if lowered.startswith(("step ", "q:", "a:", "- ", "1.", "2.", "3.", "4.", "5.")):
        return True
    return False
