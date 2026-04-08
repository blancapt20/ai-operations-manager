"""Build or update the knowledge index."""

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
from src.knowledge.service import KnowledgeIngestionService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or update the RAG knowledge index."
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="Index build mode.",
    )
    parser.add_argument(
        "--dataset-path",
        default=str(ROOT / "data" / "test_dataset"),
        help="Path containing canonical JSON knowledge documents.",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override DATABASE_URL for local builds or tests.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be indexed without writing to the database.",
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
    embedding_model_name = config.embedding_model if config else os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    openai_api_key = config.openai_api_key if config else os.getenv("OPENAI_API_KEY")
    vector_db_provider = config.vector_db_provider if config else "pgvector"

    ingestion_service = KnowledgeIngestionService(
        database_url,
        embedding_model_name=embedding_model_name,
        embedding_api_key=openai_api_key,
    )
    try:
        summary = ingestion_service.build_index(
            args.dataset_path,
            mode=args.mode,
            dry_run=args.dry_run,
        )
        print(
            json.dumps(
                {
                    "mode": summary.mode,
                    "dry_run": args.dry_run,
                    "dataset_path": str(Path(args.dataset_path)),
                    "vector_db_provider": vector_db_provider,
                    "embedding_model": ingestion_service.embedding_model.model_name,
                    "total_files": summary.total_files,
                    "indexed_documents": summary.indexed_documents,
                    "skipped_documents": summary.skipped_documents,
                    "indexed_chunks": summary.indexed_chunks,
                },
                indent=2,
            )
        )
    finally:
        ingestion_service.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
