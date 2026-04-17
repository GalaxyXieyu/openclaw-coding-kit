from __future__ import annotations

from types import SimpleNamespace
import unittest
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_coder_routing import resolve_task_coder_route
from pm_flow_commands import dispatch_run_backend, resolve_run_settings


def _routing_config() -> dict[str, object]:
    return {
        "backend": "acp",
        "agent_id": "codex",
        "timeout": 900,
        "thinking": "high",
        "session_key": "main",
        "routing": {
            "enabled": True,
            "rules": [
                {
                    "name": "frontend-to-gemini",
                    "match": {
                        "mode": "any",
                        "task_types": ["frontend", "ui", "ux"],
                        "keywords": ["前端", "ui", "页面", "界面", "交互", "样式"],
                    },
                    "target": {
                        "backend": "codex-cli",
                        "agent_id": "gemini",
                        "thinking": "max",
                    },
                },
                {
                    "name": "bugfix-to-codex",
                    "match": {
                        "mode": "any",
                        "task_types": ["bug", "backend"],
                        "keywords": ["后端", "bug", "修复", "报错", "异常", "代码健康"],
                    },
                    "target": {
                        "backend": "acp",
                        "agent_id": "codex",
                    },
                },
            ],
        },
    }


class PmCoderRoutingTest(unittest.TestCase):
    def test_resolve_task_coder_route_matches_frontend_keywords(self) -> None:
        route = resolve_task_coder_route(
            _routing_config(),
            {
                "summary": "[T9] 重做租户管理前端页面",
                "description": "需求：补一轮 UI 视觉和交互细节。",
            },
        )

        self.assertTrue(route["matched"])
        self.assertEqual("frontend-to-gemini", route["rule_name"])
        self.assertEqual("codex-cli", route["target"]["backend"])
        self.assertEqual("gemini", route["target"]["agent_id"])
        self.assertIn("页面", route["matched_by"]["keywords"])

    def test_resolve_task_coder_route_matches_task_type_label(self) -> None:
        route = resolve_task_coder_route(
            _routing_config(),
            {
                "summary": "[T10] 修复库存服务异常",
                "description": "任务类型：bugfix\n需求：修复后端 API 报错。",
            },
        )

        self.assertTrue(route["matched"])
        self.assertEqual("bugfix-to-codex", route["rule_name"])
        self.assertEqual("bug", route["task_type"])
        self.assertEqual(["bug"], route["matched_by"]["task_types"])


class PmFlowCommandRoutingTest(unittest.TestCase):
    def test_resolve_run_settings_applies_routing_before_dispatch(self) -> None:
        api = SimpleNamespace(
            coder_config=lambda: _routing_config(),
            resolve_effective_task=lambda bundle: bundle.get("current_task") or {},
        )
        args = SimpleNamespace(backend="", agent="", timeout=0, thinking="", session_key="")
        bundle = {
            "current_task": {
                "summary": "[T11] 设计后台管理页面",
                "description": "需求：优化管理端 UI 页面布局。",
            }
        }

        settings = resolve_run_settings(api, args, bundle)

        self.assertEqual("codex-cli", settings["backend"])
        self.assertEqual("gemini", settings["agent_id"])
        self.assertEqual("max", settings["thinking"])
        self.assertTrue(settings["routing"]["matched"])

    def test_resolve_run_settings_keeps_cli_override_priority(self) -> None:
        api = SimpleNamespace(
            coder_config=lambda: _routing_config(),
            resolve_effective_task=lambda bundle: bundle.get("current_task") or {},
        )
        args = SimpleNamespace(backend="", agent="codex", timeout=120, thinking="", session_key="")
        bundle = {
            "current_task": {
                "summary": "[T12] 优化首页前端页面",
                "description": "需求：补一轮前端视觉。",
            }
        }

        settings = resolve_run_settings(api, args, bundle)

        self.assertEqual("codex", settings["agent_id"])
        self.assertEqual(120, settings["timeout_seconds"])
        self.assertEqual(["agent_id", "timeout_seconds"], settings["routing"]["overridden_fields"])

    def test_dispatch_run_backend_routes_frontend_task_to_gemini_acp_session(self) -> None:
        recorded: dict[str, object] = {}

        def fake_spawn_acp_session(**kwargs):
            recorded.update(kwargs)
            return {"status": "ok", "backend": "acp", "agent_id": kwargs["agent_id"]}

        api = SimpleNamespace(
            coder_config=lambda: {
                **_routing_config(),
                "routing": {
                    "enabled": True,
                    "rules": [
                        {
                            "name": "frontend-to-gemini-acp",
                            "match": {
                                "mode": "any",
                                "task_types": ["frontend", "ui"],
                                "keywords": ["前端", "ui", "页面", "样式"],
                            },
                            "target": {
                                "backend": "acp",
                                "agent_id": "gemini",
                                "thinking": "max",
                                "session_key": "frontend-main",
                            },
                        }
                    ],
                },
            },
            resolve_effective_task=lambda bundle: bundle.get("current_task") or {},
            project_root_path=lambda: Path("/tmp/frontend-repo"),
            spawn_acp_session=fake_spawn_acp_session,
            persist_dispatch_side_effects=lambda bundle, result, agent_id, runtime: {
                "runtime": runtime,
                "agent_id": agent_id,
                "task_id": bundle["current_task"]["task_id"],
            },
        )
        args = SimpleNamespace(backend="", agent="", timeout=0, thinking="", session_key="")
        bundle = {
            "current_task": {
                "task_id": "T13",
                "summary": "[T13] 调整营销页前端样式",
                "description": "任务类型：frontend\n需求：重做页面视觉层次和交互。",
            }
        }

        settings = resolve_run_settings(api, args, bundle)
        result, side_effects = dispatch_run_backend(
            api,
            bundle=bundle,
            settings=settings,
            message="请优化这个前端页面",
            label="pm-openclaw-gemini-T13",
        )

        self.assertEqual("acp", settings["backend"])
        self.assertEqual("gemini", settings["agent_id"])
        self.assertEqual("gemini", recorded["agent_id"])
        self.assertEqual("frontend-main", recorded["session_key"])
        self.assertEqual("max", recorded["thinking"])
        self.assertEqual("请优化这个前端页面", recorded["message"])
        self.assertEqual("gemini", result["agent_id"])
        self.assertEqual("acp", side_effects["runtime"])


if __name__ == "__main__":
    unittest.main()
