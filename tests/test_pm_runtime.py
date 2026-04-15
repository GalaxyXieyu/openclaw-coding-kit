from __future__ import annotations

import subprocess
from types import SimpleNamespace
import unittest
from pathlib import Path
import sys
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_runtime import describe_openclaw_agent_failure, run_codex_cli


class PmRuntimeTest(unittest.TestCase):
    def test_unknown_agent_failure_includes_front_agent_hint(self) -> None:
        message = describe_openclaw_agent_failure("codex", stderr='Unknown agent id "codex"')
        self.assertIn("Unknown agent id", message)
        self.assertIn("front agent", message)
        self.assertIn("openclaw agents list --bindings", message)

    def test_run_codex_cli_uses_devnull_stdin(self) -> None:
        recorded: dict[str, object] = {}

        def fake_run(*args, **kwargs):
            cmd = args[0]
            output_index = cmd.index("-o") + 1
            Path(cmd[output_index]).write_text('{"ok":true}', encoding="utf-8")
            recorded["cmd"] = cmd
            recorded["stdin"] = kwargs.get("stdin")
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch("pm_runtime.subprocess.run", side_effect=fake_run):
            result = run_codex_cli(
                agent_id="codex",
                message='Return exactly {"ok":true}',
                cwd="/tmp/demo-repo",
                timeout_seconds=60,
                bin_path_fn=lambda: Path("/usr/local/bin/codex"),
            )

        self.assertIs(recorded["stdin"], subprocess.DEVNULL)
        self.assertIn("-C", recorded["cmd"])
        self.assertEqual("/tmp/demo-repo", recorded["cmd"][recorded["cmd"].index("-C") + 1])
        self.assertEqual('{"ok":true}', result["result"]["payloads"][0]["text"])


if __name__ == "__main__":
    unittest.main()
