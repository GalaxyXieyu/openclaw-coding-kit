from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_review_bundle import build_review_bundle
from review_llm_adapter import build_llm_review_request, normalize_llm_review_response


class TaskReviewLlmAdapterTest(unittest.TestCase):
    def test_build_request_uses_lane_results_as_candidates(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "code-health",
                "project_name": "主项目群",
                "changed_files": ["src/api/home.ts"],
                "commits": [{"hash": "abc123", "subject": "fix api"}],
                "api_contract_checked": False,
            }
        )
        request = build_llm_review_request(bundle, "code-review")
        self.assertEqual("code-review", request["lane"])
        self.assertTrue(request["candidate_findings"])
        self.assertEqual("Review the provided evidence and return strict JSON only.", request["task"])

    def test_build_daily_request_focuses_on_business_summary(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "daily",
                "project_name": "主项目群",
                "changed_files": ["src/api/home.ts", "docs/review.md"],
                "commits": [{"hash": "abc123", "subject": "feat: improve order review flow"}],
                "doc_updates": [
                    {
                        "path": "docs/review.md",
                        "summary": "补充订单审核流程说明",
                    }
                ],
            }
        )
        request = build_llm_review_request(bundle, "daily-review")
        self.assertEqual("daily-review", request["lane"])
        self.assertEqual("Review today's repo changes and return a compact daily summary JSON only.", request["task"])
        self.assertEqual(["feat: improve order review flow"], request["candidate_done_items"])
        self.assertTrue(any("docs_sync is mandatory" in item for item in request["instructions"]))

    def test_normalize_llm_response(self) -> None:
        normalized = normalize_llm_review_response(
            {
                "lane": "docs-review",
                "summary": "docs 有漂移",
                "findings": [
                    {
                        "severity": "P1",
                        "title": "接口文档没同步",
                        "summary": "字段还是旧的",
                        "file": "docs/api.md",
                        "evidence": ["src/api/home.ts", "docs/api.md"],
                        "suggestion": "更新字段说明",
                    }
                ],
                "docs_flags": ["AGENTS.md 可能没同步"],
            },
            "docs-review",
        )
        self.assertEqual("docs-review", normalized["lane"])
        self.assertEqual("llm-review", normalized["source"])
        self.assertEqual("P1", normalized["findings"][0]["severity"])
        self.assertEqual(["AGENTS.md 可能没同步"], normalized["docs_flags"])

    def test_normalize_daily_llm_response(self) -> None:
        normalized = normalize_llm_review_response(
            {
                "lane": "daily-review",
                "summary": "今天把订单审核链路收敛完了。",
                "done_items": ["优化了订单审核流转", "补上了退款状态回写"],
                "docs_sync": {
                    "status": "synced",
                    "summary": "业务文档已补充订单审核功能。",
                    "items": ["业务文档已补充订单审核功能"],
                },
                "risk_items": [
                    {
                        "severity": "P1",
                        "title": "退款联调还没走完",
                        "summary": "退款场景还需要和下游再验一次。",
                    }
                ],
                "next_action": "先完成退款联调验收。",
            },
            "daily-review",
        )
        self.assertEqual("daily-review", normalized["lane"])
        self.assertEqual("llm-review", normalized["source"])
        self.assertEqual("synced", normalized["docs_sync"]["status"])
        self.assertEqual("退款联调还没走完", normalized["risk_items"][0]["title"])
        self.assertEqual("先完成退款联调验收。", normalized["next_action"])


if __name__ == "__main__":
    unittest.main()
