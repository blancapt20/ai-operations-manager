"""Query the existing knowledge index without rebuilding it."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.rag.service import RetrievalService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Query the existing RAG knowledge index."
    )
    parser.add_argument(
        "--query",
        required=True,
        help="Retrieval query to run against the indexed knowledge base.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL for local queries or tests.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of chunks to return.",
    )
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.18,
        help="Minimum similarity threshold for retrieved chunks.",
    )
    parser.add_argument(
        "--document-type",
        choices=["policy", "case", "runbook"],
        default=None,
        help="Optional metadata filter for retrieval queries.",
    )
    parser.add_argument(
        "--team",
        default=None,
        help="Optional team metadata filter for retrieval queries.",
    )
    parser.add_argument(
        "--version",
        default=None,
        help="Optional version metadata filter for retrieval queries.",
    )
    parser.add_argument(
        "--case-id",
        default="cli-query",
        help="Case identifier used when persisting retrieval trace records.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        config = load_config()
    except Exception:
        if not args.database_url:
            raise
        config = None

    database_url = args.database_url or (config.database_url if config else "")
    embedding_model_name = (
        config.embedding_model if config else os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    )
    openai_api_key = config.openai_api_key if config else os.getenv("OPENAI_API_KEY")

    retrieval_service = RetrievalService(
        database_url,
        embedding_model_name=embedding_model_name,
        embedding_api_key=openai_api_key,
    )
    try:
        result = retrieval_service.retrieve_context(
            args.query,
            top_k=args.top_k,
            min_similarity=args.min_similarity,
            filters={
                key: value
                for key, value in {
                    "document_type": args.document_type,
                    "team": args.team,
                    "version": args.version,
                }.items()
                if value is not None
            },
            case_id=args.case_id,
        )
    finally:
        retrieval_service.close()

    print(
        json.dumps(
            {
                "query": args.query,
                "status": result.status,
                "scores": result.scores,
                "warnings": result.warnings,
                "chunks": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "document_type": chunk.document_type,
                        "team": chunk.team,
                        "version": chunk.version,
                        "text": chunk.text,
                    }
                    for chunk in result.chunks
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
