from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from pm_api_support import best_effort_release_stale_acp_label


class BestEffortReleaseStaleAcpLabelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.tempdir.name)
        self.addCleanup(self.tempdir.cleanup)
        self.previous_state_dir = os.environ.get("OPENCLAW_STATE_DIR")
        os.environ["OPENCLAW_STATE_DIR"] = str(self.state_dir)
        self.addCleanup(self._restore_env)

    def _restore_env(self) -> None:
        if self.previous_state_dir is None:
            os.environ.pop("OPENCLAW_STATE_DIR", None)
        else:
            os.environ["OPENCLAW_STATE_DIR"] = self.previous_state_dir

    def _write_state(self, *, last_event_offset_ms: int, bridge_acp_state: str = "running") -> None:
        now_ms = int(time.time() * 1000)
        child_session_key = "agent:codex:acp:test-stale"
        sessions_path = self.state_dir / "agents" / "codex" / "sessions" / "sessions.json"
        bridge_path = self.state_dir / "plugins" / "acp-progress-bridge" / "state.json"
        sessions_path.parent.mkdir(parents=True, exist_ok=True)
        bridge_path.parent.mkdir(parents=True, exist_ok=True)

        sessions_payload = {
            child_session_key: {
                "label": "pm-openclaw-pm-coder-kit-codex-t6",
                "updatedAt": now_ms + last_event_offset_ms,
                "sessionFile": str(self.state_dir / "agents" / "codex" / "sessions" / "missing.jsonl"),
                "acp": {
                    "state": "running",
                },
            }
        }
        bridge_payload = {
            "runs": {
                child_session_key: {
                    "childSessionKey": child_session_key,
                    "streamExists": True,
                    "sessionFileExists": False,
                    "acpState": bridge_acp_state,
                    "statusHint": "tracked but session transcript file is missing",
                    "discoveredAt": now_ms + last_event_offset_ms,
                    "lastEventAt": now_ms + last_event_offset_ms,
                }
            }
        }

        sessions_path.write_text(json.dumps(sessions_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        bridge_path.write_text(json.dumps(bridge_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def test_releases_running_label_when_transcript_missing_for_long_time(self) -> None:
        self._write_state(last_event_offset_ms=-10 * 60 * 1000)

        result = best_effort_release_stale_acp_label("codex", "pm-openclaw-pm-coder-kit-codex-t6")

        self.assertEqual(result["status"], "released")
        self.assertEqual(result["replacement_state"], "error")
        sessions_path = self.state_dir / "agents" / "codex" / "sessions" / "sessions.json"
        payload = json.loads(sessions_path.read_text(encoding="utf-8"))
        entry = payload["agent:codex:acp:test-stale"]
        self.assertNotIn("label", entry)
        self.assertEqual(entry["acp"]["state"], "error")

    def test_keeps_label_when_missing_transcript_is_still_within_grace_window(self) -> None:
        self._write_state(last_event_offset_ms=-5 * 1000)

        result = best_effort_release_stale_acp_label("codex", "pm-openclaw-pm-coder-kit-codex-t6")

        self.assertEqual(result["status"], "in_use")
        self.assertFalse(result["session_file_exists"])
        self.assertGreater(result["stale_grace_ms"], result["stale_for_ms"])


if __name__ == "__main__":
    unittest.main()
