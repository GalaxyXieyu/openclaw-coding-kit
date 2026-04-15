from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_HEALTH = REPO_ROOT / "scripts" / "source_health.py"


def _write_lines(path: Path, count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"line {index}\n" for index in range(count)), encoding="utf-8")


class SourceHealthTest(unittest.TestCase):
    def test_json_report_lists_only_real_source_offenders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_lines(root / "src" / "large.py", 5)
            _write_lines(root / "src" / "small.ts", 2)
            _write_lines(root / "screenshots" / "ignored.py", 50)
            _write_lines(root / "dist" / "bundle.js", 100)
            _write_lines(root / "docs" / "README.md", 200)

            completed = subprocess.run(
                [sys.executable, str(SOURCE_HEALTH), str(root), "--threshold", "3", "--json"],
                text=True,
                capture_output=True,
                check=True,
            )
            report = json.loads(completed.stdout)

            self.assertEqual(report["scanned_files"], 2)
            self.assertEqual(report["offender_count"], 1)
            self.assertEqual(report["offenders"], [{"path": "src/large.py", "lines": 5}])

    def test_text_report_is_warn_only_when_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_lines(root / "app.py", 3)

            completed = subprocess.run(
                [sys.executable, str(SOURCE_HEALTH), str(root), "--threshold", "10"],
                text=True,
                capture_output=True,
                check=True,
            )

            self.assertIn("Scanned 1 source files; 0 exceed 10 lines.", completed.stdout)
            self.assertIn("No source files exceed the threshold.", completed.stdout)


if __name__ == "__main__":
    unittest.main()
