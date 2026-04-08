"""SQL migration runner."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine


def apply_migrations(engine: Engine, migrations_dir: Path) -> list[str]:
    migrations_dir = Path(migrations_dir)
    migration_files = sorted(migrations_dir.glob("*.sql"))
    if not migration_files:
        return []

    applied: list[str] = []
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version VARCHAR(64) PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"
            )
        )

        for migration_file in migration_files:
            if not _migration_matches_dialect(migration_file.name, engine.dialect.name):
                continue
            version = _migration_version(migration_file.name)
            existing = connection.execute(
                text("SELECT version FROM schema_migrations WHERE version = :version"),
                {"version": version},
            ).first()
            if existing:
                continue

            sql_text = migration_file.read_text(encoding="utf-8")
            statements = [chunk.strip() for chunk in sql_text.split(";") if chunk.strip()]
            for statement in statements:
                connection.execute(text(statement))

            connection.execute(
                text("INSERT INTO schema_migrations (version) VALUES (:version)"),
                {"version": version},
            )
            applied.append(version)
    return applied


def _migration_matches_dialect(filename: str, dialect_name: str) -> bool:
    if ".postgres." in filename:
        return dialect_name == "postgresql"
    if ".sqlite." in filename:
        return dialect_name == "sqlite"
    return True


def _migration_version(filename: str) -> str:
    for suffix in (".postgres.sql", ".sqlite.sql", ".sql"):
        if filename.endswith(suffix):
            return filename[: -len(suffix)]
    return Path(filename).stem
