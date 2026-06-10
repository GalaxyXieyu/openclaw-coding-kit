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

from pm_init_commands import build_init_command_handlers
from pm_workspace import sync_repo_agents_contract


def _base_args(root: Path, config_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(root),
        project_name="演示项目",
        tasklist_guid="",
        write_config=True,
        english_name="demo-project",
        doc_folder_token="",
        task_backend="",
        doc_backend="",
        task_prefix="T",
        default_worker="codex",
        reviewer_worker="reviewer",
        no_main_review_source=False,
        no_main_digest_source=False,
        dry_run=False,
        tasklist_name="",
        doc_folder_name="",
        config=str(config_path),
    )


class PmInitBootstrapFlowTest(unittest.TestCase):
    def test_init_materializes_tasklist_binding_and_repo_agents_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            repo_root.mkdir()
            config_path = repo_root / "pm.json"
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
                ensure_project_docs=lambda root_path, dry_run=False: {
                    "folder_token": "doc_demo",
                    "folder_url": "https://example.test/doc-folder",
                    "project_doc": {"token": "doc_project", "url": "https://example.test/project"},
                    "requirements_doc": {"token": "doc_requirements", "url": "https://example.test/requirements"},
                    "roadmap_doc": {"token": "doc_roadmap", "url": "https://example.test/roadmap"},
                    "state_doc": {"token": "doc_state", "url": "https://example.test/state"},
                },
                default_tasklist_name=lambda project_name, english_name="", agent_id="": project_name,
                default_doc_folder_name=lambda project_name, english_name="", agent_id="": project_name,
                english_project_name=lambda project_name, explicit_name="", explicit_agent_id="": explicit_name or "demo-project",
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
                ensure_tasklist=lambda name: {"guid": "tasklist-guid", "url": "https://example.test/tasklist"},
                ensure_pm_dir=lambda repo_root: Path(repo_root).joinpath(".pm"),
                pm_dir_path=lambda repo_root="": Path(repo_root).joinpath(".pm"),
                pm_file=lambda name, repo_root="": Path(repo_root).joinpath(".pm", name),
                ensure_bootstrap_task=lambda repo_root: {"created": False, "task": {"task_id": "", "guid": ""}},
                refresh_context_cache=lambda task_id="", task_guid="": {"repo_scan": {}, "doc_index": {}},
                sync_repo_agents_contract=sync_repo_agents_contract,
            )
            handler = build_init_command_handlers(api)["init"]
            args = _base_args(repo_root, config_path)

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handler(args)

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("tasklist-guid", payload["tasklist"]["guid"])
            self.assertEqual("updated", payload["repo_contract"]["status"])
            self.assertNotIn("workspace_bootstrap", payload)
            self.assertNotIn("run", payload)
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("tasklist-guid", saved["task"]["tasklist_guid"])
            self.assertEqual("doc_demo", saved["doc"]["folder_token"])
            repo_agents = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Repo / Coder Execution Contract", repo_agents)
            self.assertIn("official `lark-cli`", repo_agents)

    def test_init_refreshes_context_with_bootstrap_task_without_auto_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "pm.json"
            config_path.write_text("{}", encoding="utf-8")
            captured_context: dict[str, str] = {}
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
                english_project_name=lambda project_name, explicit_name="", explicit_agent_id="": explicit_name or "demo-project",
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
                ensure_tasklist=lambda name: {"guid": "tasklist-guid", "url": "https://example.test/tasklist"},
                ensure_pm_dir=lambda repo_root: Path(repo_root).joinpath(".pm"),
                pm_dir_path=lambda repo_root="": Path(repo_root).joinpath(".pm"),
                pm_file=lambda name, repo_root="": Path(repo_root or root).joinpath(".pm", name),
                ensure_bootstrap_task=lambda repo_root: {"created": True, "task": {"task_id": "T1", "guid": "task-guid"}},
                refresh_context_cache=lambda task_id="", task_guid="": captured_context.update({"task_id": task_id, "task_guid": task_guid}) or {"repo_scan": {}, "doc_index": {}},
                sync_repo_agents_contract=sync_repo_agents_contract,
            )
            handler = build_init_command_handlers(api)["init"]
            args = _base_args(root, config_path)
            args.write_config = False
            args.english_name = ""

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handler(args)

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual({"task_id": "T1", "task_guid": "task-guid"}, captured_context)
            self.assertEqual("T1", payload["bootstrap_task"]["task"]["task_id"])
            self.assertNotIn("auto_run_reason", payload)
            self.assertNotIn("run", payload)


if __name__ == "__main__":
    unittest.main()
