"""Sprint 1 knowledge index entry point (smoke CLI)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build or update knowledge vector index (Sprint 1 smoke CLI)."
    )
    parser.add_argument(
        "--mode",
        choices=["full", "incremental"],
        default="full",
        help="Index build mode.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate command options without index writes.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    print(
        f"[build_knowledge_index] mode={args.mode} dry_run={args.dry_run} "
        f"embedding={config.embedding_model} vector={config.vector_db_provider}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
