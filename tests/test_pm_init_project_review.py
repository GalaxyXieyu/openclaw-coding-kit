from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_commands import build_command_handlers


def _args(root: Path, config_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(root),
        project_name="演示项目",
        tasklist_guid="",
        agent="",
        timeout=0,
        thinking="",
        session_key="",
        skip_bootstrap_task=False,
        skip_auto_run=False,
        write_config=False,
        english_name="",
        doc_folder_token="",
        task_backend="",
        doc_backend="",
        task_prefix="T",
        default_worker="codex",
        reviewer_worker="reviewer",
        no_auth_bundle=False,
        no_main_review_source=False,
        no_main_digest_source=False,
        dry_run=True,
        tasklist_name="",
        doc_folder_name="",
        config=str(config_path),
    )


class PmInitProjectReviewTest(unittest.TestCase):
    def test_init_dry_run_keeps_project_review_registration_repo_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "pm.json"
            config_path.write_text("{}", encoding="utf-8")

            api = SimpleNamespace(
                ACTIVE_CONFIG={"_config_path": str(config_path), "project": {}, "task": {}, "doc": {}},
                default_config=lambda: {
                    "task": {"backend": "feishu", "tasklist_name": "默认任务", "prefix": "T", "kind": "task"},
                    "doc": {"backend": "feishu", "folder_name": "默认文档"},
                    "coder": {"backend": "codex", "agent_id": "codex", "timeout": 900, "thinking": "high", "session_key": "main"},
                },
                project_root_path=lambda value: Path(value).resolve(),
                inspect_tasklist=lambda name, configured_guid="": {"status": "missing", "name": name},
                resolve_config_path=lambda _: config_path,
                ensure_project_docs=lambda root_path, dry_run=False: {"folder_token": "doc_preview", "dry_run": dry_run},
                default_tasklist_name=lambda project_name, english_name="", agent_id="": project_name,
                default_doc_folder_name=lambda project_name, english_name="", agent_id="": project_name,
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
            )

            handlers = build_command_handlers(api)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handlers["init"](_args(root, config_path))

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("dry_run", payload["status"])
            self.assertEqual("skipped", payload["main_digest_registration"]["status"])
            self.assertEqual("repo_local_init_only", payload["main_digest_registration"]["reason"])
            self.assertEqual("skipped", payload["nightly_review_registration"]["status"])

    def test_init_dry_run_auth_bundle_points_to_lark_cli_auth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "pm.json"
            config_path.write_text("{}", encoding="utf-8")

            api = SimpleNamespace(
                ACTIVE_CONFIG={"_config_path": str(config_path), "project": {}, "task": {}, "doc": {}},
                default_config=lambda: {
                    "task": {"backend": "feishu", "tasklist_name": "默认任务", "prefix": "T", "kind": "task"},
                    "doc": {"backend": "feishu", "folder_name": "默认文档"},
                    "coder": {"backend": "codex", "agent_id": "codex", "timeout": 900, "thinking": "high", "session_key": "main"},
                },
                project_root_path=lambda value: Path(value).resolve(),
                inspect_tasklist=lambda name, configured_guid="": {"status": "missing", "name": name},
                resolve_config_path=lambda _: config_path,
                ensure_project_docs=lambda root_path, dry_run=False: {"folder_token": "doc_preview", "dry_run": dry_run},
                default_tasklist_name=lambda project_name, english_name="", agent_id="": project_name,
                default_doc_folder_name=lambda project_name, english_name="", agent_id="": project_name,
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
            )

            handlers = build_command_handlers(api)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handlers["init"](_args(root, config_path))

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("skipped", payload["auth_bundle"]["status"])
            self.assertIn("pm lark status", payload["auth_bundle"]["hint"])


if __name__ == "__main__":
    unittest.main()
