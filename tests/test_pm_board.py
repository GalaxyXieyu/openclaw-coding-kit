from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PM_SCRIPT = REPO_ROOT / "skills" / "pm" / "scripts" / "pm.py"
SCRIPT_DIR = REPO_ROOT / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_api_board import build_board_task
from pm_api_board import parse_pm_event_block


class PmBoardTest(unittest.TestCase):
    def test_build_board_task_treats_zero_completed_at_as_unfinished(self) -> None:
        task = build_board_task(
            {
                "guid": "task-guid-1",
                "summary": "[T1] Verify board status",
                "description": "任务编号：T1",
                "status": "",
                "completed_at": "0",
                "tasklists": [],
                "members": [],
                "attachments": [],
            },
            comments=[],
        )
        self.assertEqual(task["status"], "todo")
        self.assertIsNone(task["completedAt"])

    def test_parse_pm_event_block_marks_invalid_progress_as_unparsed(self) -> None:
        parsed = parse_pm_event_block(
            """[[pm_event]]
schema: v1
kind: progress
task_type: development
progress: 120
[[/pm_event]]

正在补测试。"""
        )
        self.assertTrue(parsed["has_block"])
        self.assertFalse(parsed["parsed"])
        self.assertEqual(parsed["meta"]["kind"], "progress")
        self.assertIsNone(parsed["meta"]["progress"])
        self.assertEqual(parsed["content"], "正在补测试。")

    def test_local_cli_board_outputs_real_task_and_review_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            planning = root / ".planning"
            planning.mkdir(parents=True)
            for name in ("PROJECT.md", "REQUIREMENTS.md", "ROADMAP.md", "STATE.md"):
                (planning / name).write_text(f"# {name}\n", encoding="utf-8")

            config = {
                "repo_root": str(root),
                "project": {"name": "demo"},
                "task": {
                    "backend": "local",
                    "tasklist_name": "demo",
                    "prefix": "T",
                    "kind": "task",
                    "completion_due_mode": "if_missing",
                },
                "doc": {"backend": "repo", "folder_name": "demo"},
                "coder": {"backend": "codex-cli", "agent_id": "codex", "timeout": 60, "thinking": "high", "session_key": "main"},
            }
            config_path = root / "pm.json"
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

            def run(*args: str) -> dict:
                proc = subprocess.run(
                    ["python3", str(PM_SCRIPT), "--config", str(config_path), *args],
                    cwd=str(root),
                    text=True,
                    capture_output=True,
                    check=True,
                )
                return json.loads(proc.stdout)

            created = run("create", "--summary", "Implement board sync for RV-123abc456", "--request", "board adapter")
            self.assertEqual(created["task_id"], "T1")
            run(
                "comment",
                "--task-id",
                "T1",
                "--content",
                "[[pm_event]]\nschema: v1\nkind: progress\ntask_type: development\nstatus: in_progress\nprogress: 60\nstarted_at: 2026-04-17T10:00:00+08:00\n[[/pm_event]]\n\n已完成接口联调，正在补测试。",
            )

            run("create", "--summary", "Close completed task", "--request", "done")
            run("complete", "--task-id", "T2", "--content", "done")

            review_state = {
                "reviews": [
                    {
                        "review_id": "RV-123abc456",
                        "status": "sent",
                        "project_name": "demo",
                        "trigger_kind": "daily",
                        "created_at": "2026-04-17T09:00:00+08:00",
                        "updated_at": "2026-04-17T09:30:00+08:00",
                        "card_preview": {
                            "title": "每日项目回顾",
                            "review_summary": "今天把项目看板和评论进度协议打通了。",
                            "done_items": ["打通了项目看板聚合输出"],
                            "risk_items": [
                                {
                                    "title": "还缺前端联调",
                                    "summary": "如果不接前端页面，字段虽然稳定了但还看不到最终效果。",
                                }
                            ],
                            "next_action": "先把前端接口接上。",
                        },
                        "delivery": {
                            "chat_id": "oc_demo",
                            "message_id": "om_demo",
                        },
                    }
                ]
            }
            review_state_path = root / ".pm" / "project-review-state.json"
            review_state_path.parent.mkdir(parents=True, exist_ok=True)
            review_state_path.write_text(json.dumps(review_state, ensure_ascii=False, indent=2), encoding="utf-8")

            board = run("board", "--include-completed", "--limit", "10", "--comment-limit", "5")
            self.assertEqual(board["project"]["name"], "demo")
            self.assertEqual(board["scope"], "configured_tasklist")
            self.assertEqual(len(board["columns"]), 1)
            self.assertEqual(board["columns"][0]["title"], "demo")
            self.assertIn("T1", {item["taskId"] for item in board["columns"][0]["tasks"]})
            self.assertEqual(board["stats"]["totalTasks"], 2)
            self.assertEqual(board["stats"]["inProgressTasks"], 1)
            self.assertEqual(board["stats"]["doneTasks"], 1)
            board_task_t1 = next(item for item in board["tasks"] if item["taskId"] == "T1")
            self.assertEqual(board_task_t1["type"], "development")
            self.assertEqual(board_task_t1["progress"], 60)
            self.assertTrue(board_task_t1["latestEvent"]["parsed"])
            self.assertEqual(board["latestReview"]["reviewId"], "RV-123abc456")
            self.assertEqual(board["latestReview"]["summary"], "今天把项目看板和评论进度协议打通了。")

            all_visible_board = run("board", "--all-visible-tasklists", "--include-completed", "--limit", "10")
            self.assertEqual(all_visible_board["scope"], "all_visible_tasklists")
            self.assertEqual(len(all_visible_board["columns"]), 1)
            self.assertEqual(all_visible_board["columns"][0]["stats"]["totalTasks"], 2)

            detail = run("board-task", "--task-id", "T1", "--include-completed")
            self.assertEqual(detail["task"]["taskId"], "T1")
            self.assertEqual(detail["task"]["tasklistName"], "demo")
            self.assertEqual(detail["events"][0]["kind"], "progress")
            self.assertEqual(detail["events"][0]["content"], "已完成接口联调，正在补测试。")
            self.assertEqual(detail["relatedReviews"][0]["reviewId"], "RV-123abc456")


if __name__ == "__main__":
    unittest.main()
