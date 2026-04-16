from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from fix_executor import execute_fix_flow
from review_orchestrator import prepare_review
from review_state_store import load_state


class ProjectReviewFixExecutorTest(unittest.TestCase):
    def test_execute_fix_flow_creates_fix_task_and_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            state_path = repo_root / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "code-health",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "repo_root": str(repo_root),
                    "changed_files": ["src/api/home.ts", "docs/api.md"],
                    "commits": [{"hash": "abc123", "subject": "fix api"}],
                    "findings": [
                        {
                            "severity": "P1",
                            "title": "接口拼装重复",
                            "summary": "home 和 profile 有重复逻辑",
                            "file": "src/api/home.ts",
                        }
                    ],
                    "docs_flags": ["README.md 可能没同步"],
                },
                state_path=state_path,
                now_iso="2026-04-15T10:00:00+08:00",
            )

            fake_pm = SimpleNamespace(
                ACTIVE_CONFIG={},
                load_config=lambda path: {"repo_root": str(repo_root), "task": {"tasklist_name": "demo"}, "coder": {"agent_id": "codex"}},
                ensure_tasklist=lambda: {"guid": "tl_demo", "owner": {"id": "ou_demo"}},
                find_existing_task_by_summary=lambda summary, include_completed=True: None,
                next_task_id=lambda: "T9",
                build_description=lambda task_id, summary, request, repo_root_value, kind: "FIX DESC",
                task_kind=lambda: "task",
                create_task=lambda **kwargs: {"guid": "task_guid_demo", "summary": kwargs["summary"], "description": kwargs["description"]},
                refresh_context_cache=lambda **kwargs: {"task_guid": kwargs.get("task_guid")},
                parse_task_summary=lambda summary: {"task_id": "T9"},
                create_task_comment=lambda guid, content: {"guid": guid, "content": content},
            )

            with patch("fix_executor._load_pm_module", return_value=fake_pm):
                result = execute_fix_flow(
                    prepared["review_id"],
                    state_path=state_path,
                    now_iso="2026-04-15T10:10:00+08:00",
                    auto_run=False,
                )

            self.assertEqual("task_created", result["status"])
            self.assertEqual("T9", result["task_id"])
            self.assertTrue(result["docs_update_expected"])
            self.assertTrue(str(result["repair_contract_path"]).endswith(".json"))
            self.assertTrue(Path(result["repair_contract_path"]).exists())
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("T9", stored["fix_task_id"])
            self.assertEqual("task_created", stored["fix_execution"]["status"])
            self.assertEqual(str(result["repair_contract_path"]), stored["fix_execution"]["repair_contract_path"])

    def test_execute_fix_flow_can_auto_run_coder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            state_path = repo_root / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "code-health",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "repo_root": str(repo_root),
                    "changed_files": ["src/pages/home/index.tsx", "docs/home.md"],
                    "commits": [{"hash": "abc123", "subject": "fix home"}],
                    "findings": [
                        {
                            "severity": "P0",
                            "title": "白屏风险",
                            "summary": "接口报错会直接白屏",
                            "file": "src/pages/home/index.tsx",
                        }
                    ],
                },
                state_path=state_path,
                now_iso="2026-04-15T11:00:00+08:00",
            )

            fake_pm = SimpleNamespace(
                ACTIVE_CONFIG={},
                load_config=lambda path: {"repo_root": str(repo_root), "task": {"tasklist_name": "demo"}, "coder": {"agent_id": "codex"}},
                ensure_tasklist=lambda: {"guid": "tl_demo", "owner": {"id": "ou_demo"}},
                find_existing_task_by_summary=lambda summary, include_completed=True: None,
                next_task_id=lambda: "T10",
                build_description=lambda task_id, summary, request, repo_root_value, kind: "FIX DESC",
                task_kind=lambda: "task",
                create_task=lambda **kwargs: {"guid": "task_guid_demo", "summary": kwargs["summary"], "description": kwargs["description"]},
                refresh_context_cache=lambda **kwargs: {"task_guid": kwargs.get("task_guid")},
                parse_task_summary=lambda summary: {"task_id": "T10"},
                create_task_comment=lambda guid, content: {"guid": guid, "content": content},
                build_coder_context=lambda task_guid="": ({"current_task": {"guid": task_guid, "task_id": "T10"}}, repo_root / ".pm" / "coder-context.json"),
                build_run_message=lambda bundle: "run fix task",
                run_codex_cli=lambda **kwargs: {"backend": "codex-cli", "result": {"payloads": [{"text": "fixed"}], "meta": {"cwd": kwargs["cwd"]}}},
                persist_run_side_effects=lambda bundle, result: {"comment_result": {"ok": True}},
            )

            with patch("fix_executor._load_pm_module", return_value=fake_pm):
                result = execute_fix_flow(
                    prepared["review_id"],
                    state_path=state_path,
                    now_iso="2026-04-15T11:10:00+08:00",
                    auto_run=True,
                    model="codex",
                )

            self.assertEqual("coder_completed", result["status"])
            self.assertEqual("pending_integration", result["uiux_review_status"])
            self.assertEqual("codex-cli", result["coder_backend"])
            self.assertIn("Project-review repair contract:", result["coder_message_preview"])
            self.assertIn("Contract JSON:", result["coder_message_preview"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("coder_completed", stored["fix_execution"]["status"])

    def test_execute_fix_flow_persists_coder_failure_without_aborting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            state_path = repo_root / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "code-health",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "repo_root": str(repo_root),
                    "changed_files": ["src/api/home.ts"],
                    "commits": [{"hash": "abc123", "subject": "fix api"}],
                    "findings": [
                        {
                            "severity": "P1",
                            "title": "接口拼装重复",
                            "summary": "home 和 profile 有重复逻辑",
                            "file": "src/api/home.ts",
                        }
                    ],
                },
                state_path=state_path,
                now_iso="2026-04-15T12:00:00+08:00",
            )

            fake_pm = SimpleNamespace(
                ACTIVE_CONFIG={},
                load_config=lambda path: {"repo_root": str(repo_root), "task": {"tasklist_name": "demo"}, "coder": {"agent_id": "codex"}},
                ensure_tasklist=lambda: {"guid": "tl_demo", "owner": {"id": "ou_demo"}},
                find_existing_task_by_summary=lambda summary, include_completed=True: None,
                next_task_id=lambda: "T11",
                build_description=lambda task_id, summary, request, repo_root_value, kind: "FIX DESC",
                task_kind=lambda: "task",
                create_task=lambda **kwargs: {"guid": "task_guid_demo", "summary": kwargs["summary"], "description": kwargs["description"]},
                refresh_context_cache=lambda **kwargs: {"task_guid": kwargs.get("task_guid")},
                parse_task_summary=lambda summary: {"task_id": "T11"},
                create_task_comment=lambda guid, content: {"guid": guid, "content": content},
                build_coder_context=lambda task_guid="": ({"current_task": {"guid": task_guid, "task_id": "T11"}}, repo_root / ".pm" / "coder-context.json"),
                build_run_message=lambda bundle: "run fix task",
                run_codex_cli=lambda **kwargs: (_ for _ in ()).throw(SystemExit("codex exec timed out after 1800s")),
                persist_run_side_effects=lambda bundle, result: {"comment_result": {"ok": True}},
            )

            with patch("fix_executor._load_pm_module", return_value=fake_pm):
                result = execute_fix_flow(
                    prepared["review_id"],
                    state_path=state_path,
                    now_iso="2026-04-15T12:10:00+08:00",
                    auto_run=True,
                    model="codex",
                )

            self.assertEqual("coder_failed", result["status"])
            self.assertEqual("T11", result["task_id"])
            self.assertIn("timed out", result["coder_error"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("coder_failed", stored["fix_execution"]["status"])
            self.assertIn("timed out", stored["fix_execution"]["coder_error"])


if __name__ == "__main__":
    unittest.main()
