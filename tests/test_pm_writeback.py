from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
PM_SCRIPT_DIR = REPO_ROOT / "skills" / "pm" / "scripts"
if str(PM_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(PM_SCRIPT_DIR))

import pm_api_tasks
from pm_config import ACTIVE_CONFIG
from pm_flow_commands import build_flow_command_handlers
from pm_task_commands import build_task_command_handlers
from pm_writeback import enqueue_pending_writeback
from pm_writeback import load_pending_writebacks


class PmWritebackTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        ACTIVE_CONFIG.clear()
        ACTIVE_CONFIG.update(
            {
                "repo_root": str(self.root),
                "task": {
                    "backend": "feishu",
                    "tasklist_name": "demo",
                    "prefix": "T",
                    "kind": "task",
                },
            }
        )

    def tearDown(self) -> None:
        ACTIVE_CONFIG.clear()
        self.tmp.cleanup()

    def pending_items(self) -> list[dict]:
        return load_pending_writebacks(self.root / ".pm" / "pending-writebacks.json")["items"]

    def test_create_comment_defers_retryable_network_error(self) -> None:
        with mock.patch.object(pm_api_tasks, "run_bridge", side_effect=SystemExit("network_error: [Errno 1] Operation not permitted")):
            result = pm_api_tasks.create_task_comment("task-guid", "progress")

        self.assertTrue(result["deferred"])
        self.assertEqual(result["action"], "comment")
        items = self.pending_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["payload"], {"content": "progress"})

    def test_patch_task_defers_retryable_network_error(self) -> None:
        with mock.patch.object(pm_api_tasks, "run_bridge", side_effect=SystemExit("network_error: [Errno 1] Operation not permitted")):
            result = pm_api_tasks.patch_task("task-guid", {"completed_at": "2026-04-20T11:00:00+08:00"})

        self.assertTrue(result["deferred"])
        self.assertEqual(result["action"], "patch_task")
        items = self.pending_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["payload"]["changes"]["completed_at"], "2026-04-20T11:00:00+08:00")

    def test_flush_replays_comment_and_patch(self) -> None:
        enqueue_pending_writeback(action="comment", task_guid="task-guid", payload={"content": "progress"}, error="network_error")
        enqueue_pending_writeback(
            action="patch_task",
            task_guid="task-guid",
            payload={"changes": {"completed_at": "2026-04-20T11:00:00+08:00"}},
            error="network_error",
        )
        calls: list[tuple[str, str, dict]] = []

        def fake_run_bridge(tool: str, action: str, args: dict) -> dict:
            calls.append((tool, action, args))
            if tool == "feishu_task_comment" and action == "list":
                return {"details": {"comments": []}}
            if tool == "feishu_task_comment" and action == "create":
                return {"details": {"comment": {"id": "comment-id", "content": args["content"]}}}
            if tool == "feishu_task_task" and action == "patch":
                return {"details": {"task": {"guid": args["task_guid"], **args}}}
            raise AssertionError(f"unexpected bridge call: {tool}.{action}")

        with mock.patch.object(pm_api_tasks, "run_bridge", side_effect=fake_run_bridge):
            result = pm_api_tasks.flush_pending_writebacks()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["replayed_count"], 2)
        self.assertEqual(self.pending_items(), [])
        self.assertTrue(any(tool == "feishu_task_comment" and action == "create" for tool, action, _ in calls))
        self.assertTrue(any(tool == "feishu_task_task" and action == "patch" for tool, action, _ in calls))

    def test_flush_skips_duplicate_comment(self) -> None:
        enqueue_pending_writeback(action="comment", task_guid="task-guid", payload={"content": "progress"}, error="network_error")
        calls: list[tuple[str, str, dict]] = []

        def fake_run_bridge(tool: str, action: str, args: dict) -> dict:
            calls.append((tool, action, args))
            if tool == "feishu_task_comment" and action == "list":
                return {"details": {"comments": [{"content": "progress"}]}}
            if tool == "feishu_task_comment" and action == "create":
                raise AssertionError("duplicate comment should not be created")
            raise AssertionError(f"unexpected bridge call: {tool}.{action}")

        with mock.patch.object(pm_api_tasks, "run_bridge", side_effect=fake_run_bridge):
            result = pm_api_tasks.flush_pending_writebacks()

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(self.pending_items(), [])
        self.assertFalse(any(tool == "feishu_task_comment" and action == "create" for tool, action, _ in calls))

    def test_get_command_reports_replay_summary(self) -> None:
        api = SimpleNamespace(
            flush_pending_writebacks=lambda: {"status": "ok", "replayed_count": 1, "after_count": 0},
            is_retryable_writeback_error=lambda error: False,
            pending_writebacks_path=lambda: self.root / ".pm" / "pending-writebacks.json",
            should_report_replay_result=lambda result: result.get("status") != "empty",
            get_task_record_by_guid=lambda guid: {},
            get_task_record=lambda task_id, include_completed=False: {
                "summary": "[T1] Demo",
                "guid": "task-guid",
                "description": "desc",
            },
            list_task_comments=lambda guid, limit: [],
            parse_task_summary=lambda summary: {"task_id": "T1", "normalized_summary": summary},
            normalize_task_key=lambda task_id: str(task_id).upper(),
        )
        handler = build_task_command_handlers(api)["get"]
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            handler(argparse.Namespace(task_guid="", task_id="T1", include_completed=False))

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["task_id"], "T1")
        self.assertEqual(payload["writeback_replay"]["replayed_count"], 1)

    def test_context_refresh_reports_replay_summary(self) -> None:
        api = SimpleNamespace(
            flush_pending_writebacks=lambda: {"status": "ok", "replayed_count": 2, "after_count": 0},
            is_retryable_writeback_error=lambda error: False,
            pending_writebacks_path=lambda: self.root / ".pm" / "pending-writebacks.json",
            should_report_replay_result=lambda result: result.get("status") != "empty",
            refresh_context_cache=lambda task_id="", task_guid="": {"current_task": {"task_id": "T1"}, "next_task": {"task_id": "T2"}},
        )
        handler = build_flow_command_handlers(api)["context"]
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            handler(argparse.Namespace(refresh=True, task_id="", task_guid=""))

        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["current_task"]["task_id"], "T1")
        self.assertEqual(payload["writeback_replay"]["replayed_count"], 2)


if __name__ == "__main__":
    unittest.main()
