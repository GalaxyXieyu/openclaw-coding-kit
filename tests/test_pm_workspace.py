from __future__ import annotations

import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_workspace import REPO_WORKSPACE_TEMPLATES, workspace_template_root


class PmWorkspaceTest(unittest.TestCase):
    def test_repo_workspace_templates_are_self_contained(self) -> None:
        self.assertTrue(REPO_WORKSPACE_TEMPLATES.exists())
        self.assertEqual(workspace_template_root(), REPO_WORKSPACE_TEMPLATES)
        self.assertTrue((REPO_WORKSPACE_TEMPLATES / "AGENTS.md.tpl").exists())


if __name__ == "__main__":
    unittest.main()
