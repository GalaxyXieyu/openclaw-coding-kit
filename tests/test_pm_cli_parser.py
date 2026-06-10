from __future__ import annotations

import sys
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_cli import build_parser


def _build_handlers() -> dict[str, object]:
    names = (
        "init",
        "lark",
        "context",
        "next",
        "plan",
        "refine",
        "coder_context",
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
    def test_init_parser_accepts_repo_local_binding_args(self) -> None:
        handlers = _build_handlers()
        parser = build_parser(handlers=handlers)
        args = parser.parse_args(
            [
                "init",
                "--project-name",
                "demo",
                "--repo-root",
                ".",
                "--task-backend",
                "local",
                "--doc-backend",
                "repo",
            ]
        )
        self.assertEqual(args.command, "init")
        self.assertEqual(args.project_name, "demo")
        self.assertEqual(args.task_backend, "local")
        self.assertEqual(args.doc_backend, "repo")
        self.assertIs(args.func, handlers["init"])

    def test_lark_parser_accepts_status_doctor_and_login(self) -> None:
        handlers = _build_handlers()
        parser = build_parser(handlers=handlers)
        status = parser.parse_args(["lark", "status"])
        doctor = parser.parse_args(["lark", "doctor"])
        login = parser.parse_args(["lark", "login", "--exec"])
        self.assertEqual(status.action, "status")
        self.assertEqual(doctor.action, "doctor")
        self.assertEqual(login.action, "login")
        self.assertTrue(login.exec)
        self.assertIs(status.func, handlers["lark"])

    def test_removed_openclaw_and_dispatch_commands_are_not_accepted(self) -> None:
        parser = build_parser(handlers=_build_handlers())
        removed = [
            ["workspace-init", "--project-name", "demo"],
            ["workspace-delete", "--repo-root", "."],
            ["auth"],
            ["auth-link", "--scopes", "drive:drive"],
            ["permission-bundle", "--list-presets"],
            ["run", "--task-id", "T1"],
        ]
        with redirect_stderr(StringIO()):
            for argv in removed:
                with self.assertRaises(SystemExit, msg=str(argv)):
                    parser.parse_args(argv)

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
