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


class PmWorkspaceDeleteCommandTest(unittest.TestCase):
    def test_workspace_delete_cleans_bound_resources_and_repo_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            sandbox = Path(tmp_dir)
            repo_root = sandbox / "repo"
            repo_root.mkdir()
            workspace_root = sandbox / "workspace"
            workspace_root.mkdir()
            (workspace_root / "AGENTS.md").write_text("workspace", encoding="utf-8")
            config_path = repo_root / "pm.json"
            openclaw_config_path = sandbox / "openclaw.json"
            openclaw_config_path.write_text("{}", encoding="utf-8")
            config_path.write_text(
                json.dumps(
                    {
                        "project": {"name": "Demo Project", "agent": "demo-agent", "group_id": "oc_demo"},
                        "task": {
                            "backend": "feishu",
                            "tasklist_name": "Demo Tasks",
                            "tasklist_guid": "tl_demo",
                            "tasklist_url": "https://example.com/tasklist",
                            "default_assignee": "ou_demo",
                        },
                        "doc": {
                            "backend": "feishu",
                            "folder_name": "Demo Docs",
                            "folder_token": "fld_demo",
                            "folder_url": "https://example.com/folder",
                            "project_doc_token": "doc_project",
                            "project_doc_url": "https://example.com/project",
                            "requirements_doc_token": "doc_requirements",
                            "requirements_doc_url": "https://example.com/requirements",
                            "roadmap_doc_token": "doc_roadmap",
                            "roadmap_doc_url": "https://example.com/roadmap",
                            "state_doc_token": "doc_state",
                            "state_doc_url": "https://example.com/state",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            bridge_calls: list[tuple[str, str, dict[str, str]]] = []
            api = SimpleNamespace(
                project_root_path=lambda value: Path(value).resolve(),
                load_config=lambda path: json.loads(Path(path).read_text(encoding="utf-8")),
                resolve_openclaw_config_path=lambda _: openclaw_config_path,
                inspect_workspace_registration=lambda **_: {
                    "status": "matched",
                    "resolved_agent_id": "demo-agent",
                    "resolved_group_id": "oc_demo",
                    "resolved_channel": "feishu",
                    "resolved_workspace_root": str(workspace_root),
                },
                inspect_tasklist=lambda name, configured_guid="": {
                    "status": "configured_match",
                    "tasklist": {"guid": configured_guid or "tl_demo", "name": name or "Demo Tasks"},
                },
                run_bridge=lambda tool, action, args: bridge_calls.append((tool, action, args)) or {},
                find_root_folder_by_name=lambda name: None,
                project_slug=lambda project_name, english_name="", agent_id="": "demo-agent",
                unregister_main_digest_source=lambda **_: {"status": "deleted", "removed": [{"key": "demo-agent"}]},
                unregister_nightly_review_job=lambda **_: {"status": "deleted", "removed": [{"name": "Nightly Demo Project review"}]},
                unregister_workspace=lambda **_: {"status": "deleted", "agent_removed": True, "binding_removed": True},
            )

            handlers = build_command_handlers(api)
            args = argparse.Namespace(
                repo_root=str(repo_root),
                workspace_root="",
                openclaw_config="",
                agent_id="",
                group_id="",
                channel="feishu",
                dry_run=False,
                config=str(config_path),
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = handlers["workspace_delete"](args)

            self.assertEqual(0, status)
            payload = json.loads(stdout.getvalue())
            self.assertEqual("deleted", payload["status"])
            self.assertEqual("deleted", payload["tasklist_cleanup"]["status"])
            self.assertEqual("deleted", payload["docs_cleanup"]["status"])
            self.assertEqual("updated", payload["repo_config_cleanup"]["status"])
            self.assertFalse(workspace_root.exists())

            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("Demo Project", saved["project"]["name"])
            self.assertNotIn("agent", saved["project"])
            self.assertNotIn("tasklist_guid", saved["task"])
            self.assertNotIn("folder_token", saved["doc"])
            self.assertEqual(
                [
                    ("feishu_task_tasklist", "delete", {"tasklist_guid": "tl_demo"}),
                    ("feishu_drive_file", "delete", {"file_token": "fld_demo", "type": "folder"}),
                ],
                bridge_calls,
            )


if __name__ == "__main__":
    unittest.main()
