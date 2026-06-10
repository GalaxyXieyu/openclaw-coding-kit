from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
PM_SCRIPT_DIR = REPO_ROOT / "skills" / "pm" / "scripts"
if str(PM_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(PM_SCRIPT_DIR))

import pm_api_support
import pm_lark_cli
from pm_config import ACTIVE_CONFIG, default_config


class PmLarkCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self._active_config = dict(ACTIVE_CONFIG)
        self._env = {name: os.environ.get(name) for name in ("LARK_CLI_BIN", "PM_LARK_PROFILE", "PM_LARK_AS", "PM_FEISHU_PROVIDER")}
        ACTIVE_CONFIG.clear()
        ACTIVE_CONFIG.update(default_config())
        for name in self._env:
            os.environ.pop(name, None)

    def tearDown(self) -> None:
        ACTIVE_CONFIG.clear()
        ACTIVE_CONFIG.update(self._active_config)
        for name, value in self._env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def test_sanitized_env_removes_openclaw_context(self) -> None:
        env = pm_lark_cli.sanitized_env(
            {
                "OPENCLAW_SESSION_KEY": "agent:abc:main",
                "OPENCLAW_CONFIG": "/tmp/openclaw.json",
                "CLAWDBOT_GATEWAY_TOKEN": "secret",
                "CLAUDE_CODE_OPENCLAW_CONTEXT": "1",
                "PM_ALLOW_WORKSPACE_OPENCLAW_CONFIG": "true",
                "PATH": "/bin",
            }
        )
        self.assertEqual(env, {"PATH": "/bin"})

    def test_health_action_does_not_add_unsupported_flags(self) -> None:
        calls: list[tuple[list[str], dict]] = []

        def fake_run(cmd, **kwargs):
            calls.append((cmd, kwargs))
            self.assertNotIn("OPENCLAW_SESSION_KEY", kwargs["env"])
            return subprocess.CompletedProcess(cmd, 0, stdout='{"ok":true}\n', stderr="")

        with patch.dict(os.environ, {"OPENCLAW_SESSION_KEY": "agent:abc:main"}, clear=False):
            with patch("pm_lark_cli.subprocess.run", fake_run):
                payload = pm_lark_cli.run_bridge_compatible("lark_cli", "status", {})

        self.assertEqual(calls[0][0], ["lark-cli", "auth", "status"])
        self.assertEqual(payload["adapter"], "lark-cli")
        self.assertEqual(payload["tool"], "lark_cli")
        self.assertEqual(payload["action"], "status")
        self.assertEqual(payload["details"]["output"], '{"ok":true}')

    def test_json_command_adds_identity_and_format(self) -> None:
        calls: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps({"ok": True}), stderr="")

        with patch("pm_lark_cli.subprocess.run", fake_run):
            result = pm_lark_cli.run_lark_cli(["task", "tasks", "list"])

        self.assertEqual(calls[0], ["lark-cli", "task", "tasks", "list", "--as", "bot", "--format", "json"])
        self.assertEqual(result, {"ok": True})

    def test_provider_selector_routes_to_lark_cli(self) -> None:
        observed = {}

        def fake_run_bridge_compatible(tool, action, args):
            observed["call"] = (tool, action, args)
            return pm_lark_cli.normalize_payload({"tasklists": []}, {"ok": True}, tool, action)

        with patch("pm_lark_cli.run_bridge_compatible", fake_run_bridge_compatible):
            os.environ["PM_FEISHU_PROVIDER"] = "lark-cli"
            payload = pm_api_support.run_bridge("feishu_task_tasklist", "list", {"page_size": 1})

        self.assertEqual(observed["call"], ("feishu_task_tasklist", "list", {"page_size": 1}))
        self.assertEqual(payload["adapter"], "lark-cli")
        self.assertEqual(pm_api_support.details_of(payload), {"tasklists": []})

    def test_tasklist_helper_uses_official_lark_cli_command(self) -> None:
        calls: list[list[str]] = []

        def fake_run_lark_cli(argv, **kwargs):
            calls.append(list(argv))
            return {"tasklists": [{"guid": "tl1", "name": "PM"}], "has_more": False}

        with patch("pm_lark_cli.run_lark_cli", fake_run_lark_cli):
            self.assertEqual(pm_lark_cli.search_tasklists(), [{"guid": "tl1", "name": "PM"}])

        self.assertEqual(calls[0], ["task", "tasklists", "list", "--page-size", "100"])

    def test_task_read_helpers_use_official_lark_cli_commands(self) -> None:
        calls: list[list[str]] = []

        def fake_run_lark_cli(argv, **kwargs):
            calls.append(list(argv))
            if "get" in argv:
                return {"task": {"guid": "t1", "summary": "[PM1] Read"}}
            return {"tasks": [{"guid": "t1", "summary": "[PM1] Read"}], "has_more": False}

        with patch("pm_lark_cli.run_lark_cli", fake_run_lark_cli):
            rows = pm_lark_cli.list_tasklist_tasks("tl1", completed=False)
            task = pm_lark_cli.get_task("t1")

        self.assertEqual(rows, [{"guid": "t1", "summary": "[PM1] Read"}])
        self.assertEqual(task, {"guid": "t1", "summary": "[PM1] Read"})
        self.assertEqual(calls[0], ["task", "tasks", "list", "--tasklist-guid", "tl1", "--completed", "false", "--page-size", "100"])
        self.assertEqual(calls[1], ["task", "tasks", "get", "--task-guid", "t1"])

    def test_task_write_helpers_use_official_lark_cli_commands(self) -> None:
        calls: list[tuple[list[str], dict]] = []

        def fake_run_lark_cli(argv, **kwargs):
            calls.append((list(argv), kwargs))
            if "comments" in argv:
                return {"comment": {"id": "c1", "content": "done"}}
            return {"task": {"guid": "t1", "summary": "Write"}}

        with patch("pm_lark_cli.run_lark_cli", fake_run_lark_cli):
            task = pm_lark_cli.create_task(summary="Write", description="Body", tasklists=[{"tasklist_guid": "tl1"}], current_user_id="u1", members=[{"id": "u2"}])
            updated = pm_lark_cli.update_task("t1", {"summary": "Updated", "completed_at": "2026-06-10T00:00:00Z", "bogus": "drop", "due": {}})
            comment = pm_lark_cli.create_task_comment("t1", "done")

        self.assertEqual(task, {"guid": "t1", "summary": "Write"})
        self.assertEqual(updated, {"guid": "t1", "summary": "Write"})
        self.assertEqual(comment, {"id": "c1", "content": "done"})
        self.assertEqual(calls[0][0], ["task", "tasks", "create", "--summary", "Write", "--description", "Body", "--tasklist-guid", "tl1"])
        self.assertEqual(calls[0][1]["input_json"], {"current_user_id": "u1", "members": [{"id": "u2"}]})
        self.assertEqual(calls[1][0], ["task", "tasks", "update", "--task-guid", "t1"])
        self.assertEqual(calls[1][1]["input_json"], {"summary": "Updated", "completed_at": "2026-06-10T00:00:00Z"})
        self.assertEqual(calls[2][0], ["task", "comments", "create", "--task-guid", "t1", "--content", "done"])

    def test_unsupported_business_mapping_has_clear_phase_message(self) -> None:
        with self.assertRaises(SystemExit) as raised:
            pm_lark_cli.run_bridge_compatible("feishu_task_tasklist", "list", {"page_size": 1})
        message = str(raised.exception)
        self.assertIn("unsupported by the lark-cli adapter in Phase 1", message)
        self.assertIn("Phase 2/3", message)
        self.assertIn("OpenClaw/Gateway is no longer", message)

    def test_default_config_has_no_lark_cli_secrets(self) -> None:
        feishu = default_config()["feishu"]
        self.assertEqual(feishu, {"provider": "lark-cli", "cli_profile": "", "as": "bot"})
        serialized = json.dumps(feishu, ensure_ascii=False).lower()
        for forbidden in ("secret", "token", "password", "tenant"):
            self.assertNotIn(forbidden, serialized)

    def test_local_backends_do_not_call_lark_cli(self) -> None:
        ACTIVE_CONFIG["task"] = {"backend": "local"}
        ACTIVE_CONFIG["doc"] = {"backend": "repo"}

        def fail_run_lark_cli(*args, **kwargs):
            raise AssertionError("local backend should not invoke lark-cli")

        with patch("pm_lark_cli.run_lark_cli", fail_run_lark_cli):
            self.assertEqual(pm_api_support.task_backend_name(), "local")
            self.assertEqual(pm_api_support.doc_backend_name(), "repo")
            self.assertEqual(pm_api_support.feishu_provider_name(), "local")

    def test_lark_health_helpers_use_official_auth_commands(self) -> None:
        calls: list[tuple[list[str], dict]] = []

        def fake_run_lark_cli(argv, **kwargs):
            calls.append((list(argv), kwargs))
            return {"output": "ok", "stderr": ""}

        with patch("pm_lark_cli.run_lark_cli", fake_run_lark_cli):
            status = pm_lark_cli.lark_health("status")
            doctor = pm_lark_cli.lark_health("doctor")

        self.assertEqual(status["action"], "status")
        self.assertEqual(doctor["action"], "doctor")
        self.assertEqual(calls[0], (["auth", "status"], {"json_output": False, "include_identity": False}))
        self.assertEqual(calls[1], (["doctor"], {"json_output": False, "include_identity": False}))

    def test_lark_login_defaults_to_command_preview(self) -> None:
        self.assertEqual(pm_lark_cli.lark_login()["command"], ["lark-cli", "auth", "login", "--recommend"])

    def test_openclaw_gateway_provider_is_disabled(self) -> None:
        os.environ["PM_FEISHU_PROVIDER"] = "openclaw-gateway"
        with self.assertRaises(SystemExit) as raised:
            pm_api_support.run_bridge("lark_cli", "status", {})
        self.assertIn("OpenClaw/Gateway Feishu provider is disabled", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
