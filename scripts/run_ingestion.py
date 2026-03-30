"""Run multi-source ingestion simulation and persistence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_config
from src.common.contracts import EventSource
from src.ingestion.service import IngestionService, count_statuses, default_payload_for


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run multi-source ingestion simulation."
    )
    parser.add_argument(
        "--source",
        choices=["email", "tickets", "internal_events", "cli_json", "all"],
        default="all",
        help="Input source to simulate.",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Path to JSON payload used when --source is a single source.",
    )
    parser.add_argument(
        "--batch-file",
        type=str,
        default=None,
        help="Path to JSON array with records: [{'source': ..., 'payload': {...}}].",
    )
    parser.add_argument(
        "--storage-dir",
        type=str,
        default="data",
        help="Directory where ingestion JSONL artifacts are written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned ingestion records without writing to persistence.",
    )
    parser.add_argument(
        "--use-defaults",
        action="store_true",
        help="Allow built-in sample payloads when input files are not provided.",
    )
    return parser


def _load_json_file(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _build_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.batch_file:
        loaded = _load_json_file(args.batch_file)
        if not isinstance(loaded, list):
            raise ValueError("--batch-file must contain a JSON array")
        return loaded

    if args.source == "all":
        if not args.use_defaults:
            raise ValueError(
                "missing input: use --batch-file for source=all or pass --use-defaults"
            )
        return [
            {"source": source.value, "payload": default_payload_for(source)}
            for source in EventSource
        ]

    source = EventSource(args.source)
    if args.input_file:
        payload = _load_json_file(args.input_file)
    elif args.use_defaults:
        payload = default_payload_for(source)
    else:
        raise ValueError(
            "missing input: pass --input-file for single source or pass --use-defaults"
        )
    if not isinstance(payload, dict):
        raise ValueError("--input-file must contain a JSON object")
    return [{"source": source.value, "payload": payload}]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()
    try:
        records = _build_records(args)
    except ValueError as exc:
        print(f"[run_ingestion] error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(
            f"[run_ingestion] dry_run records={len(records)} source={args.source} "
            f"db={config.database_url}"
        )
        print(f"[run_ingestion] statuses_preview={{'pending': {len(records)}}}")
        return 0

    service = IngestionService(storage_dir=Path(args.storage_dir))
    results = service.ingest_records(records)
    status_summary = count_statuses(results)
    print(
        f"[run_ingestion] records={len(records)} source={args.source} "
        f"db={config.database_url} vector={config.vector_db_provider}"
    )
    print(f"[run_ingestion] statuses={status_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
