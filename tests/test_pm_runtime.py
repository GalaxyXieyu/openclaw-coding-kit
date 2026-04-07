from __future__ import annotations

import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_runtime import describe_openclaw_agent_failure


class PmRuntimeTest(unittest.TestCase):
    def test_unknown_agent_failure_includes_front_agent_hint(self) -> None:
        message = describe_openclaw_agent_failure("codex", stderr='Unknown agent id "codex"')
        self.assertIn("Unknown agent id", message)
        self.assertIn("front agent", message)
        self.assertIn("openclaw agents list --bindings", message)


if __name__ == "__main__":
    unittest.main()
