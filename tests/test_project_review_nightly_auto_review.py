from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from nightly_auto_review import run_nightly_review
from review_state_store import load_state


class ProjectReviewNightlyAutoReviewTest(unittest.TestCase):
    def test_run_nightly_review_filters_noise_and_collects_business_doc_updates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            subprocess.run(["git", "-C", str(repo_root), "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "Codex"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "codex@example.com"], check=True, capture_output=True, text=True)

            (repo_root / "docs").mkdir()
            (repo_root / "docs" / "interaction-board" / "demo" / "screenshots").mkdir(parents=True)
            (repo_root / "docs" / "interaction-board" / "demo" / "scenarios").mkdir(parents=True)
            (repo_root / "docs" / "review.md").write_text("# Review\n", encoding="utf-8")
            (repo_root / "docs" / "interaction-board" / "README.md").write_text("# Interaction Board\n", encoding="utf-8")
            (repo_root / "docs" / "interaction-board" / "demo" / "inventory.md").write_text("# Inventory\n", encoding="utf-8")
            (repo_root / "docs" / "interaction-board" / "demo" / "board.drawio").write_text("drawio", encoding="utf-8")
            (repo_root / "docs" / "interaction-board" / "demo" / "screenshots" / "page.png").write_text("png", encoding="utf-8")
            (repo_root / "docs" / "interaction-board" / "demo" / "scenarios" / "flow.json").write_text("{}", encoding="utf-8")
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
            (repo_root / "docs" / "interaction-board" / "demo" / "inventory.md").write_text(
                "# Inventory\n\n- generated snapshot\n",
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
            self.assertTrue(any("复盘规则说明" in summary for summary in summaries))
            self.assertFalse(any("Nightly Review" in summary for summary in summaries))
            self.assertFalse(any("自动拆长文件" in summary for summary in summaries))
            self.assertIn("docs/review.md", result["changed_files"])
            self.assertIn("module.py", result["changed_files"])
            self.assertNotIn("docs/interaction-board/demo/inventory.md", result["changed_files"])
            self.assertNotIn("docs/interaction-board/demo/board.drawio", result["changed_files"])
            self.assertNotIn(".pm/", result["changed_files"])

            state = load_state(state_path)
            stored = state["reviews"][0]
            card_preview = stored["card_preview"]
            self.assertEqual("synced", card_preview["docs_sync"]["status"])
            self.assertTrue(any("业务文档已补充" in item for item in card_preview["docs_sync"]["items"]))
            self.assertNotIn("automation_updates", card_preview)

    def test_run_nightly_review_still_sends_when_auto_fix_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            subprocess.run(["git", "-C", str(repo_root), "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "Codex"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "codex@example.com"], check=True, capture_output=True, text=True)

            (repo_root / "docs").mkdir()
            (repo_root / "docs" / "review.md").write_text("# Review\n", encoding="utf-8")
            (repo_root / "module.py").write_text("def health_check():\n    return True\n", encoding="utf-8")
            (repo_root / "pm.json").write_text(
                json.dumps(
                    {
                        "project": {"name": "PM工具链", "group_id": "oc_demo"},
                        "project_review": {
                            "nightly": {
                                "enabled": True,
                                "cron": "30 0 * * *",
                                "channel_id": "oc_demo",
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

            (repo_root / "module.py").write_text(
                "def health_check():\n    return True\n\n\ndef nightly_review():\n    return 'ok'\n",
                encoding="utf-8",
            )

            state_path = repo_root / ".pm" / "project-review-state.json"
            captured: dict[str, str] = {}

            def fake_send(review_id: str, **kwargs):
                captured["review_id"] = review_id
                return {
                    "ok": True,
                    "review_id": review_id,
                    "chat_id": "oc_demo",
                    "delivery": {
                        "tool": "openclaw.message.send",
                        "chat_id": "oc_demo",
                        "message_id": "om_ready",
                    },
                }

            with patch(
                "nightly_auto_review.execute_fix_flow",
                return_value={
                    "status": "coder_failed",
                    "task_id": "T12",
                    "coder_error": "codex exec timed out after 1800s",
                    "fix_files": ["module.py"],
                    "docs_update_expected": False,
                },
            ):
                with patch("nightly_auto_review.send_review_card", side_effect=fake_send):
                    result = run_nightly_review(
                        repo_root=str(repo_root),
                        pm_config=str(repo_root / "pm.json"),
                        state_path=str(state_path),
                        reviewer_model="",
                        auto_fix_mode="all",
                        send_if_possible=True,
                        dry_run=False,
                    )

            self.assertTrue(result["ok"])
            self.assertEqual("sent", result["send_result"]["status"])
            self.assertEqual("coder_failed", result["auto_fix_result"]["status"])
            self.assertEqual("deterministic_fallback", result["reviewer_status"])
            self.assertEqual(result["review_id"], captured["review_id"])
            stored = load_state(state_path)["reviews"][0]
            self.assertIn("docs_sync", stored["card_preview"])
            self.assertTrue(stored["llm_ready"])

    def test_run_nightly_review_falls_back_when_reviewer_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            subprocess.run(["git", "-C", str(repo_root), "init"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "Codex"], check=True, capture_output=True, text=True)
            subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "codex@example.com"], check=True, capture_output=True, text=True)

            (repo_root / "docs").mkdir()
            (repo_root / "docs" / "review.md").write_text("# Review\n", encoding="utf-8")
            (repo_root / "module.py").write_text("def nightly_review():\n    return 'ok'\n", encoding="utf-8")
            (repo_root / "pm.json").write_text(
                json.dumps(
                    {
                        "project": {"name": "PM工具链", "group_id": "oc_demo"},
                        "project_review": {
                            "nightly": {
                                "enabled": True,
                                "cron": "0 6 * * *",
                                "channel_id": "oc_demo",
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

            state_path = repo_root / ".pm" / "project-review-state.json"

            with patch("nightly_auto_review.execute_review_with_codex", side_effect=SystemExit("codex exec timed out after 1200s")):
                with patch(
                    "nightly_auto_review.send_review_card",
                    return_value={"ok": True, "review_id": "RV-demo", "chat_id": "oc_demo", "delivery": {"message_id": "om_demo"}},
                ):
                    result = run_nightly_review(
                        repo_root=str(repo_root),
                        pm_config=str(repo_root / "pm.json"),
                        state_path=str(state_path),
                        reviewer_model="codex",
                        auto_fix_mode="off",
                        send_if_possible=True,
                        dry_run=False,
                    )

            self.assertTrue(result["ok"])
            self.assertEqual("sent", result["send_result"]["status"])
            self.assertEqual("failed_fallback", result["reviewer_status"])
            self.assertIn("reviewer 执行失败", result["reviewer_note"])
            stored = load_state(state_path)["reviews"][0]
            self.assertTrue(stored["llm_ready"])
            automation_updates = stored["card_preview"].get("automation_updates") or []
            self.assertTrue(any("reviewer 执行失败" in item for item in automation_updates))


if __name__ == "__main__":
    unittest.main()
