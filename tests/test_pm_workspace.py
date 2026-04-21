from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_workspace import (
    REPO_AGENTS_TEMPLATE_NAME,
    REPO_WORKSPACE_TEMPLATES,
    build_workspace_profile,
    register_workspace,
    repo_template_root,
    scaffold_workspace,
    workspace_template_root,
)


class PmWorkspaceTest(unittest.TestCase):
    def test_repo_workspace_templates_are_self_contained(self) -> None:
        self.assertTrue(REPO_WORKSPACE_TEMPLATES.exists())
        self.assertEqual(workspace_template_root(), REPO_WORKSPACE_TEMPLATES)
        self.assertTrue((REPO_WORKSPACE_TEMPLATES / "AGENTS.md.tpl").exists())
        self.assertTrue(repo_template_root().exists())
        self.assertTrue((repo_template_root() / REPO_AGENTS_TEMPLATE_NAME).exists())

    def test_register_workspace_allows_gemini_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "openclaw.json"
            config_path.write_text(
                json.dumps(
                    {
                        "agents": {
                            "defaults": {
                                "model": {"primary": "yuyu/gpt-5.4"},
                            }
                        },
                        "bindings": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            payload = register_workspace(
                config_path=config_path,
                agent_id="demo-agent",
                workspace_root=root / "workspace",
                group_id="oc_demo",
                channel="feishu",
                skills=[],
                allow_agents=[],
                dry_run=True,
            )

            self.assertIn("gemini", payload["agent_entry"]["subagents"]["allowAgents"])
            self.assertEqual(["pm", "coder"], payload["agent_entry"]["skills"])

    def test_scaffold_workspace_syncs_shared_contract_into_repo_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            repo_root = root / "repo"
            repo_root.mkdir()
            (repo_root / "AGENTS.md").write_text("# Repo Rules\n\nKeep custom guidance.\n", encoding="utf-8")

            profile = build_workspace_profile(
                project_name="Demo Project",
                english_name="demo-project",
                agent_id="demo-project",
                channel="feishu",
                group_id="oc_demo",
                repo_root=repo_root,
                workspace_root=root / "workspace",
                tasklist_name="Demo Project",
                doc_folder_name="Demo Project Docs",
                task_prefix="T",
                default_worker="codex",
                reviewer_worker="reviewer",
            )

            result = scaffold_workspace(output=root / "workspace", profile=profile)

            repo_agents = (repo_root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Keep custom guidance.", repo_agents)
            self.assertIn("Repo / Coder Execution Contract", repo_agents)
            self.assertIn("product-canvas", repo_agents)
            self.assertIn("preferred UI worker: `gemini`", repo_agents)
            self.assertIn((repo_root / "AGENTS.md").resolve(), [Path(item).resolve() for item in result["generated_files"]])

    def test_scaffold_workspace_dry_run_previews_repo_agents_sync(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            repo_root = root / "repo"
            repo_root.mkdir()

            profile = build_workspace_profile(
                project_name="Demo Project",
                english_name="demo-project",
                agent_id="demo-project",
                channel="feishu",
                group_id="oc_demo",
                repo_root=repo_root,
                workspace_root=root / "workspace",
                tasklist_name="Demo Project",
                doc_folder_name="Demo Project Docs",
                task_prefix="T",
                default_worker="codex",
                reviewer_worker="reviewer",
            )

            result = scaffold_workspace(output=root / "workspace", profile=profile, dry_run=True)

            self.assertIn((repo_root / "AGENTS.md").resolve(), [Path(item).resolve() for item in result["generated_files"]])


if __name__ == "__main__":
    unittest.main()
