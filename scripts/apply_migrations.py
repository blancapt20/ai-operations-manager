"""Apply SQL migrations to configured database."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import ConfigError, load_config
from src.persistence.db import build_engine, check_database_health
from src.persistence.migrations import apply_migrations


def main() -> int:
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"[apply_migrations] error: {exc}", file=sys.stderr)
        return 2

    engine = build_engine(config.database_url)
    try:
        check_database_health(engine)
    except Exception as exc:
        print(f"[apply_migrations] error: database unavailable ({exc})", file=sys.stderr)
        return 2

    applied = apply_migrations(engine, ROOT / "migrations")
    print(f"[apply_migrations] applied={applied}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
