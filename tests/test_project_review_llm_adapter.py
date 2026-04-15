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


if __name__ == "__main__":
    unittest.main()
