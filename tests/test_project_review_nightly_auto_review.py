from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from nightly_auto_review import run_nightly_review
from review_state_store import load_state


class ProjectReviewNightlyAutoReviewTest(unittest.TestCase):
    def test_run_nightly_review_collects_doc_updates_from_dirty_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            subprocess.run(["git", "-C", str(repo_root), "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "Codex"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "codex@example.com"], check=True, capture_output=True, text=True)

            (repo_root / "docs").mkdir()
            (repo_root / "docs" / "review.md").write_text("# Review\n", encoding="utf-8")
            (repo_root / "module.py").write_text("def health_check():\n    return True\n", encoding="utf-8")
            (repo_root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
            (repo_root / "pm.json").write_text(
                json.dumps(
                    {
                        "project": {"name": "PM工具链"},
                        "project_review": {
                            "nightly": {
                                "enabled": True,
                                "cron": "30 0 * * *",
                            }
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(repo_root), "add", "."], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "commit", "-m", "init"], check=True, capture_output=True, text=True)

            (repo_root / "docs" / "review.md").write_text(
                "# Review\n\n## Nightly Review\n- 自动拆长文件\n- 文档里说明具体补了什么\n",
                encoding="utf-8",
            )
            (repo_root / "module.py").write_text(
                "def health_check():\n    return True\n\n\ndef nightly_review():\n    return 'ok'\n",
                encoding="utf-8",
            )

            state_path = repo_root / ".pm" / "project-review-state.json"
            result = run_nightly_review(
                repo_root=str(repo_root),
                pm_config=str(repo_root / "pm.json"),
                state_path=str(state_path),
                reviewer_model="",
                auto_fix_mode="all",
                send_if_possible=False,
                dry_run=True,
            )

            self.assertTrue(result["ok"])
            self.assertEqual("PM工具链", result["project_name"])
            self.assertEqual("skipped", result["send_result"]["status"])
            self.assertEqual("any finding/docs drift", result["auto_fix_reason"])
            self.assertTrue(result["doc_updates"])
            summaries = [item["summary"] for item in result["doc_updates"]]
            self.assertTrue(any("Nightly Review" in summary for summary in summaries))

            state = load_state(state_path)
            stored = state["reviews"][0]
            card_preview = stored["card_preview"]
            self.assertIn("doc_updates", card_preview)
            self.assertIn("automation_updates", card_preview)
            self.assertIn("dry-run", card_preview["automation_updates"][0])


if __name__ == "__main__":
    unittest.main()
