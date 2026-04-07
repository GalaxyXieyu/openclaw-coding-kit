from __future__ import annotations

import unittest
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
PM_SCRIPT_DIR = REPO_ROOT / "skills" / "pm" / "scripts"
if str(PM_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(PM_SCRIPT_DIR))

from pm_bridge import bridge_script_path


class PmBridgeTest(unittest.TestCase):
    def test_repo_local_lark_bridge_script_exists_and_is_preferred(self) -> None:
        repo_script = REPO_ROOT / "skills" / "openclaw-lark-bridge" / "scripts" / "invoke_openclaw_tool.py"
        fallback_script = Path.home() / ".codex" / "skills" / "openclaw-lark-bridge" / "scripts" / "invoke_openclaw_tool.py"

        self.assertTrue(repo_script.exists())
        resolved = bridge_script_path((repo_script, fallback_script))
        self.assertEqual(resolved, repo_script)


if __name__ == "__main__":
    unittest.main()
