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
from pm_workspace import build_workspace_profile
from pm_workspace import scaffold_workspace


class PmInitBootstrapFlowTest(unittest.TestCase):
    def test_init_materializes_tasklist_binding_and_default_agents_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            repo_root = root / "repo"
            repo_root.mkdir()
            config_path = repo_root / "pm.json"
            openclaw_config_path = root / "openclaw.json"
            workspace_root = root / "workspace"
            config_path.write_text("{}", encoding="utf-8")
            openclaw_config_path.write_text("{}", encoding="utf-8")

            api = SimpleNamespace(
                ACTIVE_CONFIG={"_config_path": str(config_path), "project": {}, "task": {}, "doc": {}},
                default_config=lambda: {
                    "task": {"backend": "feishu", "tasklist_name": "默认任务", "prefix": "T", "kind": "task"},
                    "doc": {"backend": "feishu", "folder_name": "默认文档"},
                    "coder": {"backend": "acp", "agent_id": "codex", "timeout": 900, "thinking": "high", "session_key": "main"},
                },
                project_root_path=lambda value: Path(value).resolve(),
                build_auth_bundle=lambda **_: {"status": "ok"},
                resolve_openclaw_config_path=lambda _: openclaw_config_path,
                resolve_workspace_root=lambda **_: workspace_root,
                build_workspace_profile=build_workspace_profile,
                scaffold_workspace=lambda **kwargs: scaffold_workspace(**kwargs),
                register_workspace=lambda **_: {"status": "ok"},
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
                english_project_name=lambda project_name, explicit_name="", explicit_agent_id="": explicit_name or explicit_agent_id or "demo-project",
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
                project_slug=lambda project_name, english_name="", agent_id="": "demo-project",
                register_main_digest_source=lambda **kwargs: {"status": "ok", "source": {"key": kwargs["source_key"]}},
                ensure_tasklist=lambda name: {"guid": "tasklist-guid", "url": "https://example.test/tasklist"},
                ensure_pm_dir=lambda repo_root: Path(repo_root).joinpath(".pm"),
                pm_dir_path=lambda repo_root="": Path(repo_root).joinpath(".pm"),
                pm_file=lambda name, repo_root="": Path(repo_root or root).joinpath(".pm", name),
                ensure_bootstrap_task=lambda repo_root: {"created": False, "task": {"task_id": "", "guid": ""}},
                refresh_context_cache=lambda task_id="", task_guid="": {"repo_scan": {}, "doc_index": {}, "gsd": {}},
                resolve_dispatch_session_key=lambda explicit, fallback="main": fallback,
                write_pm_bundle=lambda name, payload: None,
            )
            handler = build_init_command_handlers(api)["init"]
            args = argparse.Namespace(
                repo_root=str(repo_root),
                project_name="演示项目",
                tasklist_guid="",
                agent="",
                timeout=0,
                thinking="",
                session_key="",
                skip_bootstrap_task=False,
                skip_auto_run=True,
                write_config=True,
                english_name="demo-project",
                agent_id="demo-project",
                group_id="oc_demo",
                workspace_root=str(workspace_root),
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
                no_main_review_source=False,
                no_main_digest_source=False,
                force=False,
                replace_binding=False,
                dry_run=False,
                tasklist_name="",
                doc_folder_name="",
                config=str(config_path),
                _deprecated_command="",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handler(args)

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("tasklist-guid", payload["tasklist"]["guid"])
            generated = [Path(item).resolve() for item in payload["workspace_bootstrap"]["scaffold"]["generated_files"]]
            self.assertIn((workspace_root / "AGENTS.md").resolve(), generated)
            self.assertIn((repo_root / "AGENTS.md").resolve(), generated)
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("tasklist-guid", saved["task"]["tasklist_guid"])
            self.assertEqual("doc_demo", saved["doc"]["folder_token"])
            self.assertTrue((workspace_root / "AGENTS.md").exists())
            self.assertTrue((repo_root / "AGENTS.md").exists())

    def test_init_auto_run_uses_bootstrap_task_as_discovery_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "pm.json"
            openclaw_config_path = root / "openclaw.json"
            config_path.write_text("{}", encoding="utf-8")
            openclaw_config_path.write_text("{}", encoding="utf-8")
            captured_context: dict[str, str] = {}
            recorded_run: dict[str, str] = {}
            api = SimpleNamespace(
                ACTIVE_CONFIG={"_config_path": str(config_path), "project": {}, "task": {}, "doc": {}},
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
                register_main_digest_source=lambda **kwargs: {"status": "ok", "source": {"key": kwargs["source_key"]}},
                ensure_tasklist=lambda name: {"guid": "tasklist-guid", "url": "https://example.test/tasklist"},
                ensure_pm_dir=lambda repo_root: Path(repo_root).joinpath(".pm"),
                pm_dir_path=lambda repo_root="": Path(repo_root).joinpath(".pm"),
                pm_file=lambda name, repo_root="": Path(repo_root or root).joinpath(".pm", name),
                ensure_bootstrap_task=lambda repo_root: {"created": True, "task": {"task_id": "T1", "guid": "task-guid"}},
                refresh_context_cache=lambda task_id="", task_guid="": {"repo_scan": {}, "doc_index": {}, "gsd": {}},
                build_coder_context=lambda task_id="", task_guid="": (
                    captured_context.update({"task_id": task_id, "task_guid": task_guid})
                    or {"current_task": {"task_id": task_id, "guid": task_guid}},
                    root / ".pm" / "coder-context.json",
                ),
                build_run_message=lambda bundle: f"run {bundle['current_task']['task_id']} {bundle['current_task']['guid']}",
                spawn_acp_session=lambda **kwargs: recorded_run.update(kwargs) or {"status": "ok", "result": {"runId": "run-1"}},
                build_run_label=lambda repo_root, agent_id, task_id: f"{repo_root.name}-{agent_id}-{task_id}",
                persist_dispatch_side_effects=lambda bundle, result, agent_id, runtime: {"runtime": runtime, "agent_id": agent_id},
                resolve_dispatch_session_key=lambda explicit, fallback="main": fallback,
                write_pm_bundle=lambda name, payload: None,
            )
            handler = build_init_command_handlers(api)["init"]
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
                no_main_review_source=False,
                no_main_digest_source=False,
                force=False,
                replace_binding=False,
                dry_run=False,
                tasklist_name="",
                doc_folder_name="",
                config=str(config_path),
                _deprecated_command="",
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handler(args)

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual({"task_id": "T1", "task_guid": "task-guid"}, captured_context)
            self.assertEqual("bootstrap_task_created", payload["auto_run_reason"])
            self.assertEqual("T1", payload["bootstrap_task"]["task"]["task_id"])
            self.assertEqual("run T1 task-guid", payload["run"]["message_preview"])
            self.assertEqual("T1", recorded_run["label"].split("-")[-1])


if __name__ == "__main__":
    unittest.main()
