from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from review_orchestrator import execute_review_with_codex, ingest_review_results, prepare_review
from review_state_store import load_state


class TaskReviewReviewOrchestratorTest(unittest.TestCase):
    def test_prepare_review_builds_llm_requests_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            result = prepare_review(
                {
                    "trigger_kind": "code-health",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "changed_files": ["src/api/home.ts", "docs/api.md"],
                    "commits": [{"hash": "abc123", "subject": "fix api"}],
                    "api_contract_checked": False,
                },
                state_path=state_path,
                now_iso="2026-04-14T16:00:00+08:00",
                prompt_version="project-review-reviewer/v1",
                model="reviewer-mini",
            )
            self.assertEqual("drafted", result["status"])
            self.assertEqual(["code-review", "docs-review"], result["pending_llm_lanes"])
            self.assertEqual(2, len(result["llm_requests"]))
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual(result["review_id"], stored["review_id"])
            self.assertEqual("reviewer-mini", stored["model"])
            self.assertEqual("abc123", stored["latest_commit_hash"])
            self.assertEqual(1, len(stored["history"]))

    def test_prepare_review_reuses_same_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            payload = {
                "trigger_kind": "code-health",
                "project_name": "主项目群",
                "channel_id": "oc_demo",
                "changed_files": ["src/api/home.ts"],
                "commits": [{"hash": "abc123", "subject": "fix api"}],
            }
            first = prepare_review(
                payload,
                state_path=state_path,
                now_iso="2026-04-14T16:00:00+08:00",
                model="reviewer-mini",
            )
            second = prepare_review(
                payload,
                state_path=state_path,
                now_iso="2026-04-14T16:05:00+08:00",
                model="reviewer-mini",
            )
            state = load_state(state_path)
            self.assertFalse(first["reused_existing"])
            self.assertTrue(second["reused_existing"])
            self.assertEqual(first["review_id"], second["review_id"])
            self.assertEqual(1, len(state["reviews"]))
            self.assertEqual(1, len(state["reviews"][0]["history"]))

    def test_ingest_review_results_merges_llm_verdict_into_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "code-health",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "changed_files": ["src/api/home.ts"],
                    "commits": [{"hash": "abc123", "subject": "fix api"}],
                    "repo_has_agents": True,
                    "agent_sync_required": True,
                },
                state_path=state_path,
                now_iso="2026-04-14T16:00:00+08:00",
            )
            ingested = ingest_review_results(
                prepared["review_id"],
                {
                    "code-review": {
                        "lane": "code-review",
                        "summary": "发现重复逻辑",
                        "findings": [
                            {
                                "severity": "P1",
                                "title": "语义重复",
                                "summary": "接口拼装逻辑和另一个模块重复",
                                "file": "src/api/home.ts",
                                "evidence": ["src/api/home.ts", "src/api/profile.ts"],
                                "suggestion": "提成共享函数",
                            }
                        ],
                        "docs_flags": [],
                    },
                    "docs-review": {
                        "lane": "docs-review",
                        "summary": "AGENTS 没同步",
                        "findings": [],
                        "docs_flags": ["AGENTS.md 可能没同步"],
                    },
                },
                state_path=state_path,
                now_iso="2026-04-14T16:10:00+08:00",
                model="reviewer-max",
            )
            self.assertTrue(ingested["llm_ready"])
            self.assertEqual([], ingested["pending_llm_lanes"])
            titles = [item["title"] for item in ingested["bundle"]["findings"]]
            self.assertIn("语义重复", titles)
            self.assertIn("AGENTS.md 可能没同步", ingested["bundle"]["docs_flags"])
            stored = load_state(state_path)["reviews"][0]
            self.assertTrue(stored["llm_ready"])
            self.assertEqual("reviewer-max", stored["model"])
            self.assertEqual(2, len(stored["history"]))

    def test_prepare_review_redraft_clears_stale_llm_and_delivery_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            payload = {
                "trigger_kind": "code-health",
                "project_name": "主项目群",
                "channel_id": "oc_demo",
                "changed_files": ["src/api/home.ts"],
                "commits": [{"hash": "abc123", "subject": "fix api"}],
            }
            prepared = prepare_review(
                payload,
                state_path=state_path,
                now_iso="2026-04-14T16:00:00+08:00",
                prompt_version="project-review-reviewer/v1",
                model="codex",
            )
            ingest_review_results(
                prepared["review_id"],
                {
                    "code-review": {
                        "lane": "code-review",
                        "summary": "发现真实风险",
                        "findings": [
                            {
                                "severity": "P1",
                                "title": "订单状态会回退",
                                "summary": "退款后状态没有回写",
                                "card_title": "订单状态可能不对",
                                "card_summary": "退款处理后，用户看到的订单状态可能还是旧的。",
                                "file": "src/api/home.ts",
                                "evidence": ["src/api/home.ts:1-9"],
                                "suggestion": "补齐主订单状态回写",
                            }
                        ],
                        "docs_flags": [],
                        "next_actions": ["先补订单状态回写"],
                    },
                    "docs-review": {
                        "lane": "docs-review",
                        "summary": "文档没问题",
                        "findings": [],
                        "docs_flags": [],
                        "next_actions": ["再补一次回归检查"],
                    },
                },
                state_path=state_path,
                now_iso="2026-04-14T16:10:00+08:00",
                prompt_version="project-review-reviewer/v1",
                model="codex",
            )
            state = load_state(state_path)
            state["reviews"][0]["delivery"] = {"message_id": "om_demo"}
            Path(state_path).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

            redrafted = prepare_review(
                payload,
                state_path=state_path,
                now_iso="2026-04-14T16:20:00+08:00",
                prompt_version="project-review-reviewer/v2-card-copy",
                model="codex",
            )

            self.assertFalse(redrafted["reused_existing"])
            stored = load_state(state_path)["reviews"][0]
            self.assertFalse(stored["llm_ready"])
            self.assertEqual(["code-review", "docs-review"], stored["pending_llm_lanes"])
            self.assertEqual({}, stored["llm_verdict"])
            self.assertEqual({}, stored["delivery"])
            self.assertEqual("", stored["sent_at"])
            self.assertEqual(3, len(stored["history"]))

    def test_execute_review_with_codex_runs_pending_lanes_and_ingests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            state_path = tmp_root / "project-review-state.json"

            lane_outputs = {
                "code-review": {
                    "lane": "code-review",
                    "summary": "发现接口重复判断",
                    "findings": [
                        {
                            "severity": "P1",
                            "title": "接口拼装重复",
                            "summary": "home 和 profile 有重复的返回拼装逻辑",
                            "file": "src/api/home.ts",
                            "evidence": ["src/api/home.ts", "src/api/profile.ts"],
                            "suggestion": "提成共享 helper",
                        }
                    ],
                    "docs_flags": [],
                },
                "docs-review": {
                    "lane": "docs-review",
                    "summary": "README 没同步",
                    "findings": [],
                    "docs_flags": ["README.md 可能没同步这次接口调整"],
                },
            }

            def fake_run(request: dict, **kwargs):
                lane = str(request.get("lane") or "").strip()
                return {
                    "lane": lane,
                    "response": lane_outputs[lane],
                    "raw_text": "",
                    "backend": "codex-cli",
                    "meta": {"cwd": kwargs.get("repo_root", "")},
                }

            with patch("review_orchestrator._run_codex_reviewer_request", side_effect=fake_run) as mocked_run:
                result = execute_review_with_codex(
                    {
                        "trigger_kind": "code-health",
                        "project_name": "主项目群",
                        "channel_id": "oc_demo",
                        "repo_root": str(tmp_root),
                        "changed_files": ["src/api/home.ts", "docs/api.md"],
                        "commits": [{"hash": "abc123", "subject": "fix api"}],
                        "api_contract_checked": False,
                    },
                    state_path=state_path,
                    now_iso="2026-04-15T09:00:00+08:00",
                    model="codex",
                )

            self.assertEqual(2, mocked_run.call_count)
            self.assertTrue(result["llm_ready"])
            self.assertEqual([], result["pending_llm_lanes"])
            self.assertEqual(2, len(result["reviewer_runs"]))
            ingested = result["ingested"]
            self.assertIsNotNone(ingested)
            titles = [item["title"] for item in ingested["bundle"]["findings"]]
            self.assertIn("接口拼装重复", titles)
            self.assertIn("README.md 可能没同步这次接口调整", ingested["bundle"]["docs_flags"])

            stored = load_state(state_path)["reviews"][0]
            self.assertTrue(stored["llm_ready"])
            self.assertEqual("codex", stored["model"])
            self.assertEqual([], stored["pending_llm_lanes"])

    def test_prepare_and_ingest_daily_review_uses_single_daily_lane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "daily",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "changed_files": ["src/pages/home/index.tsx", "docs/review.md"],
                    "commits": [{"hash": "abc123", "subject": "feat: improve home review flow"}],
                },
                state_path=state_path,
                now_iso="2026-04-15T09:00:00+08:00",
                model="codex",
            )
            self.assertEqual(["daily-review"], prepared["pending_llm_lanes"])

            ingested = ingest_review_results(
                prepared["review_id"],
                {
                    "daily-review": {
                        "lane": "daily-review",
                        "summary": "今天把首页回顾链路收口了。",
                        "done_items": ["优化了首页回顾流程"],
                        "docs_sync": {
                            "status": "synced",
                            "summary": "业务文档已补充首页回顾功能。",
                            "items": ["业务文档已补充首页回顾功能"],
                        },
                        "risk_items": [],
                        "next_action": "先做一轮真机验收。",
                    }
                },
                state_path=state_path,
                now_iso="2026-04-15T09:10:00+08:00",
                model="codex",
            )

            self.assertTrue(ingested["llm_ready"])
            self.assertEqual([], ingested["pending_llm_lanes"])
            self.assertEqual("业务文档已补充首页回顾功能。", ingested["card"]["docs_sync"]["summary"])


if __name__ == "__main__":
    unittest.main()
