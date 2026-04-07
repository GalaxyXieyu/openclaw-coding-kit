from __future__ import annotations

import unittest
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_context import build_context_payload


class PmContextTest(unittest.TestCase):
    def test_build_context_payload_includes_repo_local_contract_fields(self) -> None:
        root = Path("/tmp/demo-repo")
        tasklist = {"guid": "local-tasklist-guid"}
        current_task = {
            "summary": "T1 Implement local backend",
            "normalized_summary": "T1 Implement local backend",
            "status": "in_progress",
            "guid": "task-guid-1",
            "url": "local://tasks/T1",
            "description": "Task detail for T1",
            "updated_at": "2026-04-07T10:00:00Z",
            "completed_at": "",
            "attachments": [{"name": "evidence.txt", "path": "/tmp/demo-repo/evidence.txt"}],
            "tasklists": [{"guid": "local-tasklist-guid"}],
        }
        comment_calls: list[tuple[str, int]] = []

        def parse_task_summary(summary: str) -> dict[str, str]:
            summary = str(summary)
            if summary.startswith("T1"):
                return {"task_id": "T1", "normalized_summary": "T1 Implement local backend"}
            if summary.startswith("T2"):
                return {"task_id": "T2", "normalized_summary": "T2 Write docs"}
            return {}

        def list_task_comments(task_guid: str, limit: int) -> list[dict[str, str]]:
            comment_calls.append((task_guid, limit))
            return [{"author": "pm", "content": "Please keep it repo-local."}]

        payload = build_context_payload(
            active_config={
                "_config_path": str(root / "pm.json"),
                "task": {"backend": "local", "tasklist_name": "demo-tasklist"},
                "doc": {
                    "backend": "repo",
                    "folder_name": ".planning/docs",
                    "project_doc_url": "repo://PROJECT.md",
                    "requirements_doc_url": "repo://REQUIREMENTS.md",
                },
            },
            project_root_path=lambda: root,
            ensure_tasklist=lambda: tasklist,
            task_pool=lambda **kwargs: [
                {
                    "summary": "T2 Write docs",
                    "normalized_summary": "T2 Write docs",
                    "status": "todo",
                    "guid": "task-guid-2",
                    "url": "local://tasks/T2",
                    "created_at": "2026-04-07T10:05:00Z",
                },
                {
                    "summary": "T1 Implement local backend",
                    "normalized_summary": "T1 Implement local backend",
                    "status": "in_progress",
                    "guid": "task-guid-1",
                    "url": "local://tasks/T1",
                    "created_at": "2026-04-07T10:00:00Z",
                },
            ],
            extract_task_number=lambda summary: int(str(summary).split()[0].replace("T", "")) if str(summary).startswith("T") else 0,
            get_task_record_by_guid=lambda guid: current_task if guid == "task-guid-1" else {},
            list_task_comments=list_task_comments,
            project_name=lambda: "demo",
            tasklist_name=lambda: "demo-tasklist",
            task_prefix=lambda: "T",
            task_kind=lambda: "task",
            repo_scan=lambda repo_root: {"repo_root": str(repo_root), "docs": ["README.md"]},
            build_bootstrap_info=lambda repo_root: {"project_mode": "brownfield", "recommended_action": "map-codebase"},
            detect_gsd_assets=lambda repo_root: {"state_doc": ".planning/STATE.md"},
            parse_task_summary=parse_task_summary,
            parse_task_id_from_description=lambda description: "T1",
            now_iso=lambda: "2026-04-07T10:10:00Z",
        )

        self.assertEqual(payload["project"]["task_backend"], "local")
        self.assertEqual(payload["project"]["doc_backend"], "repo")
        self.assertEqual(payload["project"]["tasklist_guid"], "local-tasklist-guid")
        self.assertEqual(payload["doc_index"]["folder_name"], ".planning/docs")
        self.assertEqual(payload["doc_index"]["project_doc_url"], "repo://PROJECT.md")
        self.assertEqual(payload["next_task"]["task_id"], "T1")
        self.assertEqual(payload["current_task"]["task_id"], "T1")
        self.assertEqual(payload["current_task"]["attachments"][0]["name"], "evidence.txt")
        self.assertEqual(payload["current_task"]["tasklists"][0]["guid"], "local-tasklist-guid")
        self.assertEqual(payload["recent_comments"][0]["content"], "Please keep it repo-local.")
        self.assertEqual(comment_calls, [("task-guid-1", 10)])


if __name__ == "__main__":
    unittest.main()
