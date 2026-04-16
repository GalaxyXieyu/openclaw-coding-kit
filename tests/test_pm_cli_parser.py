from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_cli import build_parser


def _build_handlers() -> dict[str, object]:
    names = (
        "auth",
        "auth_link",
        "permission_bundle",
        "init",
        "sync_gsd_docs",
        "sync_gsd_progress",
        "materialize_gsd_tasks",
        "route_gsd",
        "plan_phase",
        "context",
        "next",
        "plan",
        "refine",
        "coder_context",
        "run",
        "create",
        "get",
        "comment",
        "complete",
        "update_description",
        "list",
        "normalize_titles",
        "search",
        "backfill_assignees",
        "attachments",
        "upload_attachments",
    )
    return {name: (lambda args, command=name: command) for name in names}


class PmCliParserTest(unittest.TestCase):
    def test_workspace_init_keeps_init_handler_and_deprecated_marker(self) -> None:
        handlers = _build_handlers()
        parser = build_parser(handlers=handlers)
        args = parser.parse_args(
            [
                "workspace-init",
                "--project-name",
                "demo",
                "--group-id",
                "group-1",
                "--repo-root",
                ".",
            ]
        )
        self.assertEqual(args.command, "workspace-init")
        self.assertIs(args.func, handlers["init"])
        self.assertEqual(args._deprecated_command, "workspace-init")

    def test_upload_attachments_parser_still_accepts_task_and_file(self) -> None:
        handlers = _build_handlers()
        parser = build_parser(handlers=handlers)
        args = parser.parse_args(
            [
                "upload-attachments",
                "--task-id",
                "T1",
                "--file",
                "evidence.txt",
            ]
        )
        self.assertEqual(args.command, "upload-attachments")
        self.assertEqual(args.task_id, "T1")
        self.assertEqual(args.file, ["evidence.txt"])
        self.assertIs(args.func, handlers["upload_attachments"])


if __name__ == "__main__":
    unittest.main()
