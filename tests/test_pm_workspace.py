from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_workspace import REPO_WORKSPACE_TEMPLATES, register_workspace, workspace_template_root


class PmWorkspaceTest(unittest.TestCase):
    def test_repo_workspace_templates_are_self_contained(self) -> None:
        self.assertTrue(REPO_WORKSPACE_TEMPLATES.exists())
        self.assertEqual(workspace_template_root(), REPO_WORKSPACE_TEMPLATES)
        self.assertTrue((REPO_WORKSPACE_TEMPLATES / "AGENTS.md.tpl").exists())

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
            self.assertEqual(["pm", "coder", "code-review"], payload["agent_entry"]["skills"])


if __name__ == "__main__":
    unittest.main()
