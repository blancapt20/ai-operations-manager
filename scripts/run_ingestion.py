"""Sprint 1 ingestion entry point (smoke CLI)."""

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
        description="Run multi-source ingestion simulation (Sprint 1 smoke CLI)."
    )
    parser.add_argument(
        "--source",
        choices=["email", "tickets", "internal_events", "cli_json", "all"],
        default="all",
        help="Input source to simulate.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate CLI flow without writing data.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    print(
        f"[run_ingestion] source={args.source} dry_run={args.dry_run} "
        f"db={config.database_url} vector={config.vector_db_provider}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
