"""Database migration and constraint tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text

from src.persistence.db import build_engine
from src.persistence.migrations import apply_migrations


ROOT = Path(__file__).resolve().parents[1]


class TestDbMigrations(unittest.TestCase):
    def test_migrations_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database_url = f"sqlite:///{Path(tmp) / 'migrations.db'}"
            engine = build_engine(database_url)

            first = apply_migrations(engine, ROOT / "migrations")
            second = apply_migrations(engine, ROOT / "migrations")
            engine.dispose()

            self.assertIn("001_initial_schema", first)
            self.assertEqual(second, [])

    def test_normalized_event_unique_constraint_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database_url = f"sqlite:///{Path(tmp) / 'constraints.db'}"
            engine = build_engine(database_url)
            apply_migrations(engine, ROOT / "migrations")

            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO normalized_events "
                        "(event_id, source, timestamp, event_type, body, metadata) "
                        "VALUES (:event_id, :source, :timestamp, :event_type, :body, :metadata)"
                    ),
                    {
                        "event_id": "evt-1",
                        "source": "email",
                        "timestamp": "2026-04-07 00:00:00",
                        "event_type": "billing_dispute",
                        "body": "sample",
                        "metadata": "{}",
                    },
                )

                with self.assertRaises(Exception):
                    connection.execute(
                        text(
                            "INSERT INTO normalized_events "
                            "(event_id, source, timestamp, event_type, body, metadata) "
                            "VALUES (:event_id, :source, :timestamp, :event_type, :body, :metadata)"
                        ),
                        {
                            "event_id": "evt-1",
                            "source": "email",
                            "timestamp": "2026-04-07 00:00:00",
                            "event_type": "billing_dispute",
                            "body": "sample2",
                            "metadata": "{}",
                        },
                    )
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
