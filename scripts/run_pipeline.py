"""Run the end-to-end grounded processing pipeline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agent.service import PipelineService
from src.config import load_config
from src.rag.service import RetrievalService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the end-to-end processing pipeline over pending ingested events."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Maximum number of pending events to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate pipeline control flow without mutations.",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Optional retrieval query to exercise the grounded decision contract.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Maximum number of retrieved chunks when --query is provided.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    if args.query:
        retrieval_service = RetrievalService(
            config.database_url,
            embedding_model_name=config.embedding_model,
            embedding_api_key=config.openai_api_key,
        )
        try:
            result = retrieval_service.retrieve_context(
                args.query,
                top_k=args.top_k,
                case_id="pipeline-preview",
            )
        finally:
            retrieval_service.close()
        print(
            json.dumps(
                {
                    "limit": args.limit,
                    "dry_run": args.dry_run,
                    "model": config.model_name,
                    "database_url": config.database_url,
                    "retrieval": {
                        "status": result.status,
                        "scores": result.scores,
                        "chunk_ids": [chunk.chunk_id for chunk in result.chunks],
                    },
                },
                indent=2,
            )
        )
        return 0

    pipeline_service = PipelineService(
        config.database_url,
        embedding_model_name=config.embedding_model,
        embedding_api_key=config.openai_api_key,
    )
    try:
        summary = pipeline_service.process_pending_events(
            limit=args.limit,
            dry_run=args.dry_run,
        )
    finally:
        pipeline_service.close()

    print(
        json.dumps(
            {
                "limit": args.limit,
                "dry_run": args.dry_run,
                "model": config.model_name,
                "database_url": config.database_url,
                "processed": summary.processed,
                "cases": summary.cases,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
