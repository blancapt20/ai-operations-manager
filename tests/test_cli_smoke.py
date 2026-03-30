"""CLI smoke tests for Sprint 1 scripts."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    ROOT / "scripts" / "run_ingestion.py",
    ROOT / "scripts" / "build_knowledge_index.py",
    ROOT / "scripts" / "run_pipeline.py",
)


class TestCliSmoke(unittest.TestCase):
    def test_help_commands_exit_zero(self) -> None:
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                completed = subprocess.run(
                    [sys.executable, str(script), "--help"],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("usage", completed.stdout.lower())


if __name__ == "__main__":
    unittest.main()
