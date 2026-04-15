from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from commit_window import build_git_log_command, collect_recent_commits, parse_git_log_output


class TaskReviewCommitWindowTest(unittest.TestCase):
    def test_build_git_log_command_includes_since_until(self) -> None:
        command = build_git_log_command(".", "24 hours ago", "now")
        self.assertIn("--since=24 hours ago", command)
        self.assertIn("--until=now", command)

    def test_parse_git_log_output(self) -> None:
        commits = parse_git_log_output(
            "abc123\t2026-04-14T09:00:00+08:00\tfix login\n"
            "def456\t2026-04-14T11:00:00+08:00\tupdate docs\n"
        )
        self.assertEqual(2, len(commits))
        self.assertEqual("abc123", commits[0]["hash"])
        self.assertEqual("update docs", commits[1]["subject"])

    @patch("commit_window.subprocess.run")
    def test_collect_recent_commits_uses_git_log(self, run_mock) -> None:
        run_mock.return_value.stdout = "abc123\t2026-04-14T09:00:00+08:00\tfix login\n"
        commits = collect_recent_commits(".", "24 hours ago")
        self.assertEqual(1, len(commits))
        self.assertEqual("fix login", commits[0]["subject"])
        run_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
