from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
PM_SCRIPT_DIR = REPO_ROOT / "skills" / "pm" / "scripts"
if str(PM_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(PM_SCRIPT_DIR))

import pm_api_tasks
from pm_config import ACTIVE_CONFIG, default_config


class PmLarkReadPathTest(unittest.TestCase):
    def setUp(self) -> None:
        self._active_config = dict(ACTIVE_CONFIG)
        self._env = {name: os.environ.get(name) for name in ("PM_FEISHU_PROVIDER",)}
        ACTIVE_CONFIG.clear()
        ACTIVE_CONFIG.update(default_config())
        ACTIVE_CONFIG["task"] = {"backend": "feishu", "tasklist_name": "PM"}
        os.environ.pop("PM_FEISHU_PROVIDER", None)

    def tearDown(self) -> None:
        ACTIVE_CONFIG.clear()
        ACTIVE_CONFIG.update(self._active_config)
        for name, value in self._env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_feishu_read_path_uses_direct_lark_helpers_not_bridge(self) -> None:
        with patch("pm_api_tasks.search_lark_tasklists", return_value=[{"guid": "tl1", "name": "PM"}]) as tasklists:
            with patch("pm_api_tasks.list_lark_tasklist_tasks", return_value=[{"guid": "t1", "summary": "[PM1] Read"}]) as tasks:
                with patch("pm_api_tasks.run_bridge", side_effect=AssertionError("bridge should not be used")):
                    rows = pm_api_tasks.task_pool(include_completed=False)

        self.assertEqual(rows, [{"guid": "t1", "summary": "[PM1] Read"}])
        tasklists.assert_called_once_with()
        tasks.assert_called_once_with("tl1", completed=False)

    def test_feishu_get_by_guid_uses_direct_lark_helper_not_bridge(self) -> None:
        with patch("pm_api_tasks.get_lark_task", return_value={"guid": "t1", "summary": "[PM1] Read"}) as get_task:
            with patch("pm_api_tasks.run_bridge", side_effect=AssertionError("bridge should not be used")):
                task = pm_api_tasks.get_task_record_by_guid("t1")

        self.assertEqual(task["guid"], "t1")
        self.assertEqual(task["summary"], "[PM1] Read")
        get_task.assert_called_once_with("t1")

    def test_feishu_create_and_comment_use_direct_lark_helpers_not_bridge(self) -> None:
        with patch("pm_api_tasks.create_lark_task", return_value={"guid": "t1", "summary": "Write"}) as create_task:
            with patch("pm_api_tasks.create_lark_task_comment", return_value={"id": "c1"}) as create_comment:
                with patch("pm_api_tasks.run_bridge", side_effect=AssertionError("bridge should not be used")):
                    task = pm_api_tasks.create_task(summary="Write", description="Body", tasklists=[{"guid": "tl1"}])
                    comment = pm_api_tasks.create_task_comment("t1", "done")

        self.assertEqual(task, {"guid": "t1", "summary": "Write"})
        self.assertEqual(comment, {"id": "c1"})
        create_task.assert_called_once()
        create_comment.assert_called_once_with("t1", "done")

    def test_feishu_patch_uses_direct_lark_helper_not_bridge(self) -> None:
        changes = {"summary": "Updated", "completed_at": "2026-06-10T00:00:00Z"}
        with patch("pm_api_tasks.update_lark_task", return_value={"guid": "t1", "summary": "Updated"}) as update_task:
            with patch("pm_api_tasks.run_bridge", side_effect=AssertionError("bridge should not be used")):
                task = pm_api_tasks.patch_task("t1", changes)

        self.assertEqual(task, {"guid": "t1", "summary": "Updated"})
        update_task.assert_called_once_with("t1", changes)

    def test_completion_changes_patch_uses_direct_lark_helper_not_bridge(self) -> None:
        changes = pm_api_tasks.build_completion_changes({"guid": "t1"}, completed_at="2026-06-10T00:00:00Z")
        with patch("pm_api_tasks.update_lark_task", return_value={"guid": "t1", "completed_at": changes["completed_at"]}) as update_task:
            with patch("pm_api_tasks.run_bridge", side_effect=AssertionError("bridge should not be used")):
                task = pm_api_tasks.patch_task("t1", changes)

        self.assertEqual(task["completed_at"], "2026-06-10T00:00:00Z")
        update_task.assert_called_once_with("t1", {"completed_at": "2026-06-10T00:00:00Z"})

    def test_local_backend_stays_independent_from_lark_helpers(self) -> None:
        ACTIVE_CONFIG["task"] = {"backend": "local"}
        with patch("pm_api_tasks.search_lark_tasklists", side_effect=AssertionError("lark should not be used")):
            with patch("pm_api_tasks.ensure_local_tasklist", return_value={"guid": "local", "name": "Local"}) as local:
                tasklist = pm_api_tasks.ensure_tasklist("Local")

        self.assertEqual(tasklist, {"guid": "local", "name": "Local"})
        local.assert_called_once()


if __name__ == "__main__":
    unittest.main()
