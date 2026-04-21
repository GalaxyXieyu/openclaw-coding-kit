from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_api_support import resolve_current_openclaw_context
from pm_api_support import best_effort_release_stale_acp_label
from pm_api_support import resolve_dispatch_session_key
from pm_flow_commands import build_flow_command_handlers
from pm_init_commands import build_init_command_handlers


class PmOpenclawContextTest(unittest.TestCase):
    def test_resolve_current_openclaw_context_reads_session_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            sessions_dir = state_dir / "agents" / "openclaw-pm-coder-kit" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_key = "agent:openclaw-pm-coder-kit:feishu:group:oc_demo"
            sessions_payload = {
                session_key: {
                    "channel": "feishu",
                    "deliveryContext": {
                        "channel": "feishu",
                        "to": "chat:oc_demo",
                        "accountId": "default",
                    },
                    "lastAccountId": "default",
                    "lastTo": "chat:oc_demo",
                }
            }
            (sessions_dir / "sessions.json").write_text(json.dumps(sessions_payload, ensure_ascii=False), encoding="utf-8")

            with mock.patch.dict(
                os.environ,
                {
                    "OPENCLAW_STATE_DIR": str(state_dir),
                    "OPENCLAW_AGENT_ID": "openclaw-pm-coder-kit",
                    "OPENCLAW_SESSION_KEY": session_key,
                },
                clear=False,
            ):
                context = resolve_current_openclaw_context()

        self.assertEqual(session_key, context["session_key"])
        self.assertEqual("openclaw-pm-coder-kit", context["agent_id"])
        self.assertEqual("feishu", context["message_channel"])
        self.assertEqual("default", context["account_id"])
        self.assertEqual("chat:oc_demo", context["message_to"])

    def test_resolve_dispatch_session_key_prefers_explicit_then_context_then_fallback(self) -> None:
        self.assertEqual("manual-session", resolve_dispatch_session_key("manual-session", fallback="main"))

        with mock.patch.dict(os.environ, {"OPENCLAW_SESSION_KEY": "agent:demo:feishu:group:oc_demo"}, clear=False):
            self.assertEqual("agent:demo:feishu:group:oc_demo", resolve_dispatch_session_key("", fallback="main"))

        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual("main", resolve_dispatch_session_key("", fallback="main"))

    def test_best_effort_release_stale_acp_label_clears_terminal_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_dir = Path(tmp_dir)
            sessions_dir = state_dir / "agents" / "codex" / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            child_session_key = "agent:codex:acp:stale-run"
            sessions_payload = {
                child_session_key: {
                    "label": "pm-demo-codex-t14",
                    "updatedAt": 123,
                    "acp": {"state": "running"},
                }
            }
            (sessions_dir / "sessions.json").write_text(
                json.dumps(sessions_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            bridge_dir = state_dir / "plugins" / "acp-progress-bridge"
            bridge_dir.mkdir(parents=True, exist_ok=True)
            bridge_payload = {
                "runs": {
                    child_session_key: {
                        "doneAt": 456,
                        "terminalKind": "error",
                        "completionHandled": True,
                        "statusHint": "completion already detected; progress delivery stopped",
                    }
                }
            }
            (bridge_dir / "state.json").write_text(
                json.dumps(bridge_payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with mock.patch.dict(os.environ, {"OPENCLAW_STATE_DIR": str(state_dir)}, clear=False):
                result = best_effort_release_stale_acp_label("codex", "pm-demo-codex-t14")

            updated_payload = json.loads((sessions_dir / "sessions.json").read_text(encoding="utf-8"))
            self.assertEqual("released", result["status"])
            self.assertEqual("error", updated_payload[child_session_key]["acp"]["state"])
            self.assertNotIn("label", updated_payload[child_session_key])


class PmFlowCommandSessionInheritanceTest(unittest.TestCase):
    def test_run_inherits_current_openclaw_session_when_cli_is_empty(self) -> None:
        recorded: dict[str, object] = {}
        api = SimpleNamespace(
            build_coder_context=lambda task_id="", task_guid="": (
                {"current_task": {"task_id": "T13", "summary": "[T13] Demo"}},
                Path("/tmp/coder-context.json"),
            ),
            coder_config=lambda: {
                "backend": "acp",
                "agent_id": "codex",
                "timeout": 900,
                "thinking": "high",
                "session_key": "main",
            },
            resolve_dispatch_session_key=resolve_dispatch_session_key,
            build_run_message=lambda bundle: f"run {bundle['current_task']['task_id']}",
            resolve_effective_task=lambda bundle: bundle.get("current_task") or {},
            build_run_label=lambda root, agent_id, task_id: f"{root.name}-{agent_id}-{task_id}",
            project_root_path=lambda: Path("/tmp/demo-repo"),
            spawn_acp_session=lambda **kwargs: recorded.update(kwargs) or {"status": "ok", "runId": "run-1"},
            persist_dispatch_side_effects=lambda bundle, result, agent_id, runtime: {"runtime": runtime, "agent_id": agent_id},
            write_pm_bundle=lambda name, payload: None,
            run_codex_cli=lambda **kwargs: {"status": "unused"},
            run_openclaw_agent=lambda **kwargs: {"status": "unused"},
            persist_run_side_effects=lambda bundle, result: {"status": "unused"},
        )
        handler = build_flow_command_handlers(api)["run"]
        stdout = io.StringIO()

        with mock.patch.dict(
            os.environ,
            {"OPENCLAW_SESSION_KEY": "agent:openclaw-pm-coder-kit:feishu:group:oc_demo"},
            clear=False,
        ):
            with contextlib.redirect_stdout(stdout):
                handler(argparse.Namespace(task_id="T13", task_guid="", backend="", agent="", timeout=0, thinking="", session_key=""))

        payload = json.loads(stdout.getvalue())
        self.assertEqual("agent:openclaw-pm-coder-kit:feishu:group:oc_demo", recorded["session_key"])
        self.assertEqual("agent:openclaw-pm-coder-kit:feishu:group:oc_demo", payload["session_key"])

    def test_run_reports_label_recovery_before_spawning(self) -> None:
        recorded: dict[str, object] = {}
        api = SimpleNamespace(
            build_coder_context=lambda task_id="", task_guid="": (
                {"current_task": {"task_id": "T14", "summary": "[T14] Demo"}},
                Path("/tmp/coder-context.json"),
            ),
            coder_config=lambda: {
                "backend": "acp",
                "agent_id": "codex",
                "timeout": 900,
                "thinking": "high",
                "session_key": "main",
            },
            resolve_dispatch_session_key=resolve_dispatch_session_key,
            build_run_message=lambda bundle: f"run {bundle['current_task']['task_id']}",
            resolve_effective_task=lambda bundle: bundle.get("current_task") or {},
            build_run_label=lambda root, agent_id, task_id: f"{root.name}-{agent_id}-{task_id}",
            project_root_path=lambda: Path("/tmp/demo-repo"),
            best_effort_release_stale_acp_label=lambda **kwargs: {"status": "released", **kwargs},
            spawn_acp_session=lambda **kwargs: recorded.update(kwargs) or {"status": "ok", "runId": "run-1"},
            persist_dispatch_side_effects=lambda bundle, result, agent_id, runtime: {"runtime": runtime, "agent_id": agent_id},
            write_pm_bundle=lambda name, payload: None,
            run_codex_cli=lambda **kwargs: {"status": "unused"},
            run_openclaw_agent=lambda **kwargs: {"status": "unused"},
            persist_run_side_effects=lambda bundle, result: {"status": "unused"},
        )
        handler = build_flow_command_handlers(api)["run"]
        stdout = io.StringIO()

        with contextlib.redirect_stdout(stdout):
            handler(argparse.Namespace(task_id="T14", task_guid="", backend="", agent="", timeout=0, thinking="", session_key=""))

        payload = json.loads(stdout.getvalue())
        self.assertEqual("released", payload["label_recovery"]["status"])
        self.assertEqual("demo-repo-codex-T14", payload["label_recovery"]["label"])
        self.assertEqual("demo-repo-codex-T14", recorded["label"])


class PmInitCommandSessionInheritanceTest(unittest.TestCase):
    def test_init_auto_run_inherits_current_openclaw_session(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            config_path = root / "pm.json"
            openclaw_config_path = root / "openclaw.json"
            config_path.write_text("{}", encoding="utf-8")
            openclaw_config_path.write_text("{}", encoding="utf-8")
            recorded: dict[str, object] = {}
            api = SimpleNamespace(
                ACTIVE_CONFIG={
                    "_config_path": str(config_path),
                    "project": {},
                    "task": {},
                    "doc": {},
                },
                default_config=lambda: {
                    "task": {"backend": "feishu", "tasklist_name": "默认任务", "prefix": "T", "kind": "task"},
                    "doc": {"backend": "feishu", "folder_name": "默认文档"},
                    "coder": {"backend": "acp", "agent_id": "codex", "timeout": 900, "thinking": "high", "session_key": "main"},
                },
                project_root_path=lambda value: Path(value).resolve(),
                build_auth_bundle=lambda **_: {"status": "ok"},
                resolve_openclaw_config_path=lambda _: openclaw_config_path,
                inspect_tasklist=lambda name, configured_guid="": {"status": "missing", "name": name},
                resolve_config_path=lambda _: config_path,
                ensure_project_docs=lambda root_path, dry_run=False: {"folder_token": "doc_preview", "dry_run": dry_run},
                default_tasklist_name=lambda project_name, english_name="", agent_id="": project_name,
                default_doc_folder_name=lambda project_name, english_name="", agent_id="": project_name,
                task_prefix=lambda: "T",
                task_kind=lambda: "task",
                project_slug=lambda project_name, english_name="", agent_id="": "demo-project",
                register_main_digest_source=lambda **kwargs: {"status": "ok", "source": {"key": kwargs["source_key"]}},
                ensure_tasklist=lambda name: {"guid": "tasklist-guid", "url": "https://example.test/tasklist"},
                ensure_pm_dir=lambda repo_root: Path(repo_root).joinpath(".pm"),
                pm_dir_path=lambda repo_root="": Path(repo_root).joinpath(".pm"),
                pm_file=lambda name, repo_root="": Path(repo_root or root).joinpath(".pm", name),
                ensure_bootstrap_task=lambda repo_root: {"created": True, "task": {"task_id": "T1", "guid": "task-guid"}},
                refresh_context_cache=lambda task_id="", task_guid="": {"repo_scan": {}, "doc_index": {}, "gsd": {}},
                build_coder_context=lambda task_id="", task_guid="": (
                    {"current_task": {"task_id": task_id or "T1", "guid": task_guid or "task-guid"}},
                    root / ".pm" / "coder-context.json",
                ),
                build_run_message=lambda bundle: f"run {bundle['current_task']['task_id']}",
                spawn_acp_session=lambda **kwargs: recorded.update(kwargs) or {"status": "ok", "result": {"runId": "run-1"}},
                build_run_label=lambda repo_root, agent_id, task_id: f"{repo_root.name}-{agent_id}-{task_id}",
                persist_dispatch_side_effects=lambda bundle, result, agent_id, runtime: {"runtime": runtime, "agent_id": agent_id},
                write_pm_bundle=lambda name, payload: None,
                resolve_dispatch_session_key=resolve_dispatch_session_key,
            )
            handler = build_init_command_handlers(api)["init"]
            stdout = io.StringIO()
            args = argparse.Namespace(
                repo_root=str(root),
                project_name="演示项目",
                tasklist_guid="",
                agent="",
                timeout=0,
                thinking="",
                session_key="",
                skip_bootstrap_task=False,
                skip_auto_run=False,
                write_config=False,
                english_name="",
                agent_id="",
                group_id="",
                workspace_root="",
                openclaw_config="",
                channel="feishu",
                doc_folder_token="",
                task_backend="",
                doc_backend="",
                task_prefix="T",
                default_worker="codex",
                reviewer_worker="reviewer",
                skill=[],
                allow_agent=[],
                model_primary="",
                no_auth_bundle=False,
                no_main_review_source=False,
                no_main_digest_source=False,
                force=False,
                replace_binding=False,
                dry_run=False,
                tasklist_name="",
                doc_folder_name="",
                config=str(config_path),
                _deprecated_command="",
            )

            with mock.patch.dict(
                os.environ,
                {"OPENCLAW_SESSION_KEY": "agent:openclaw-pm-coder-kit:feishu:group:oc_demo"},
                clear=False,
            ):
                with contextlib.redirect_stdout(stdout):
                    handler(args)

            payload = json.loads(stdout.getvalue())
            self.assertEqual("agent:openclaw-pm-coder-kit:feishu:group:oc_demo", recorded["session_key"])
            self.assertEqual("agent:openclaw-pm-coder-kit:feishu:group:oc_demo", payload["run"]["session_key"])


if __name__ == "__main__":
    unittest.main()
