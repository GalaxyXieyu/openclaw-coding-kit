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


class PmInitProjectReviewTest(unittest.TestCase):
    def test_init_dry_run_includes_main_digest_registration_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "pm.json"
            openclaw_config_path = root / "openclaw.json"
            config_path.write_text("{}", encoding="utf-8")
            openclaw_config_path.write_text("{}", encoding="utf-8")

            api = SimpleNamespace(
                ACTIVE_CONFIG={
                    "_config_path": str(config_path),
                    "project": {},
                    "task": {},
                    "doc": {},
                },
                default_config=lambda: {
                    "task": {"backend": "feishu", "tasklist_name": "默认任务", "prefix": "T", "kind": "task"},
                    "doc": {"backend": "feishu", "folder_name": "默认文档"},
                    "coder": {"backend": "acp", "agent_id": "codex", "timeout": 900, "thinking": "high", "session_key": "main"},
                },
                project_root_path=lambda value: Path(value).resolve(),
                build_auth_bundle=lambda **_: {"status": "ok"},
                resolve_openclaw_config_path=lambda _: openclaw_config_path,
                inspect_tasklist=lambda name, configured_guid="": {"status": "missing", "name": name},
                resolve_config_path=lambda _: config_path,
                ensure_project_docs=lambda root_path, dry_run=False: {"folder_token": "doc_preview", "dry_run": dry_run},
                default_tasklist_name=lambda project_name, english_name="", agent_id="": project_name,
                default_doc_folder_name=lambda project_name, english_name="", agent_id="": project_name,
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
                project_slug=lambda project_name, english_name="", agent_id="": "demo-project",
                register_main_digest_source=lambda **kwargs: {"status": "dry_run", "action": "bootstrapped", "source": {"key": kwargs["source_key"]}},
            )

            handlers = build_command_handlers(api)
            args = argparse.Namespace(
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
                agent_id="",
                group_id="",
                workspace_root="",
                openclaw_config="",
                channel="feishu",
                doc_folder_token="",
                task_backend="",
                doc_backend="",
                task_prefix="T",
                default_worker="codex",
                reviewer_worker="reviewer",
                skill=[],
                allow_agent=[],
                model_primary="",
                no_auth_bundle=False,
                no_main_digest_source=False,
                force=False,
                replace_binding=False,
                dry_run=True,
                tasklist_name="",
                doc_folder_name="",
                config=str(config_path),
                _deprecated_command="",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handlers["init"](args)

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("dry_run", payload["status"])
            self.assertEqual("dry_run", payload["main_digest_registration"]["status"])
            self.assertEqual("demo-project", payload["main_digest_registration"]["source"]["key"])

    def test_init_dry_run_includes_nightly_review_registration_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "pm.json"
            openclaw_config_path = root / "openclaw.json"
            config_path.write_text("{}", encoding="utf-8")
            openclaw_config_path.write_text("{}", encoding="utf-8")

            api = SimpleNamespace(
                ACTIVE_CONFIG={
                    "_config_path": str(config_path),
                    "project": {},
                    "task": {},
                    "doc": {},
                    "project_review": {
                        "nightly": {
                            "enabled": True,
                            "cron": "15 0 * * *",
                            "reviewer_model": "codex",
                        }
                    },
                },
                default_config=lambda: {
                    "task": {"backend": "feishu", "tasklist_name": "默认任务", "prefix": "T", "kind": "task"},
                    "doc": {"backend": "feishu", "folder_name": "默认文档"},
                    "coder": {"backend": "acp", "agent_id": "codex", "timeout": 900, "thinking": "high", "session_key": "main"},
                },
                project_root_path=lambda value: Path(value).resolve(),
                build_auth_bundle=lambda **_: {"status": "ok"},
                resolve_openclaw_config_path=lambda _: openclaw_config_path,
                inspect_tasklist=lambda name, configured_guid="": {"status": "missing", "name": name},
                resolve_config_path=lambda _: config_path,
                ensure_project_docs=lambda root_path, dry_run=False: {"folder_token": "doc_preview", "dry_run": dry_run},
                default_tasklist_name=lambda project_name, english_name="", agent_id="": project_name,
                default_doc_folder_name=lambda project_name, english_name="", agent_id="": project_name,
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
                project_slug=lambda project_name, english_name="", agent_id="": "demo-project",
                register_main_digest_source=lambda **kwargs: {"status": "dry_run", "action": "bootstrapped", "source": {"key": kwargs["source_key"]}},
                register_nightly_review_job=lambda **kwargs: {"status": "dry_run", "job": {"name": "Nightly 演示项目 review", "schedule": {"expr": kwargs["cron_expr"]}}},
            )

            handlers = build_command_handlers(api)
            args = argparse.Namespace(
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
                agent_id="",
                group_id="",
                workspace_root="",
                openclaw_config="",
                channel="feishu",
                doc_folder_token="",
                task_backend="",
                doc_backend="",
                task_prefix="T",
                default_worker="codex",
                reviewer_worker="reviewer",
                skill=[],
                allow_agent=[],
                model_primary="",
                no_auth_bundle=False,
                no_main_digest_source=False,
                force=False,
                replace_binding=False,
                dry_run=True,
                tasklist_name="",
                doc_folder_name="",
                config=str(config_path),
                _deprecated_command="",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handlers["init"](args)

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("dry_run", payload["status"])
            self.assertEqual("dry_run", payload["nightly_review_registration"]["status"])
            self.assertEqual("15 0 * * *", payload["nightly_review_registration"]["job"]["schedule"]["expr"])


if __name__ == "__main__":
    unittest.main()
