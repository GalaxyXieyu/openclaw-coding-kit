from __future__ import annotations

import unittest
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_dispatch import spawn_acp_session


class PmDispatchTest(unittest.TestCase):
    def test_spawn_acp_session_passes_gemini_agent_id_to_bridge(self) -> None:
        recorded: dict[str, object] = {}

        def fake_bridge(tool_name, _unused, args, *, session_key):
            recorded["tool_name"] = tool_name
            recorded["args"] = args
            recorded["session_key"] = session_key
            return {"status": "ok", "result": {"runId": "run-1"}}

        result = spawn_acp_session(
            fake_bridge,
            agent_id="gemini",
            message="请优化前端页面视觉",
            cwd="/tmp/frontend-repo",
            timeout_seconds=120,
            thinking="max",
            label="pm-openclaw-gemini-T13",
            session_key="frontend-main",
        )

        self.assertEqual("sessions_spawn", recorded["tool_name"])
        self.assertEqual("frontend-main", recorded["session_key"])
        self.assertEqual("gemini", recorded["args"]["agentId"])
        self.assertEqual("请优化前端页面视觉", recorded["args"]["task"])
        self.assertEqual("acp", recorded["args"]["runtime"])
        self.assertEqual("max", recorded["args"]["thinking"])
        self.assertEqual("run-1", result["result"]["runId"])


if __name__ == "__main__":
    unittest.main()
