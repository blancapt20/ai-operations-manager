"""Sprint 1 pipeline entry point (smoke CLI)."""

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
        description="Run end-to-end processing pipeline (Sprint 1 smoke CLI)."
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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    print(
        f"[run_pipeline] limit={args.limit} dry_run={args.dry_run} "
        f"model={config.model_name} db={config.database_url}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
