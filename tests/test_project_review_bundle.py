from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_review_bundle import build_review_bundle


class TaskReviewBundleTest(unittest.TestCase):
    def test_build_weekly_bundle_generates_valid_project_summary(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "weekly",
                "project_name": "主项目群",
                "channel_id": "oc_demo",
                "project_summaries": [
                    {
                        "project": "小程序",
                        "done": "登录页",
                        "pending": "支付联调",
                        "next_step": "补测试",
                        "status": "推进中",
                    }
                ],
                "tasks": {"completed": [{"id": "T1"}], "active": [{"id": "T2"}]},
                "enable_graph": True,
            }
        )
        self.assertEqual("weekly_review_card_v1", bundle["trigger"]["card_kind"])
        self.assertEqual(["project-retro", "graph-observe"], bundle["trigger"]["lanes"])
        self.assertEqual("小程序做了登录页，还差支付联调，下一步先补测试。", bundle["projects"][0]["summary"])
        self.assertTrue(bundle["projects"][0]["summary_ok"])

    def test_build_code_health_bundle_marks_ui_scope(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "code-health",
                "project_name": "主项目群",
                "changed_files": ["src/pages/home/index.tsx", "docs/spec.md"],
                "commits": [{"hash": "abc123", "subject": "update home"}],
                "repo_has_agents": False,
                "file_stats": [{"path": "src/pages/home/index.tsx", "line_count": 460}],
            }
        )
        self.assertTrue(bundle["trigger"]["should_run"])
        self.assertEqual(["code-review", "docs-review", "ui-ux-review"], bundle["trigger"]["lanes"])
        self.assertTrue(bundle["changed_scope"]["touches_ui"])
        self.assertIn("仓库还没有 AGENTS.md。", bundle["docs_flags"])
        self.assertTrue(bundle["findings"])
        self.assertEqual("code-review", bundle["lane_results"]["code_review"]["lane"])

    def test_build_code_health_bundle_skips_without_commits(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "code-health",
                "project_name": "主项目群",
                "has_recent_commits": False,
            }
        )
        self.assertFalse(bundle["trigger"]["should_run"])
        self.assertEqual([], bundle["trigger"]["lanes"])

    def test_build_bundle_merges_llm_reviews(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "code-health",
                "project_name": "主项目群",
                "changed_files": ["src/api/home.ts"],
                "commits": [{"hash": "abc123", "subject": "fix api"}],
                "llm_reviews": {
                    "code-review": {
                        "lane": "code-review",
                        "findings": [
                            {
                                "severity": "P1",
                                "title": "语义重复",
                                "summary": "逻辑看起来和另一个模块重复",
                                "file": "src/api/home.ts",
                            }
                        ],
                    },
                    "docs-review": {
                        "lane": "docs-review",
                        "docs_flags": ["docs/api.md 语义没同步"],
                    },
                },
            }
        )
        titles = [item["title"] for item in bundle["findings"]]
        self.assertIn("语义重复", titles)
        self.assertIn("docs/api.md 语义没同步", bundle["docs_flags"])

    def test_build_bundle_keeps_doc_updates(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "daily",
                "project_name": "PM工具链",
                "changed_files": ["docs/review.md"],
                "commits": [{"hash": "abc123", "subject": "docs: update nightly review"}],
                "doc_updates": [
                    {
                        "path": "docs/review.md",
                        "summary": "补充 nightly review 如何自动拆长文件和回写文档说明",
                    }
                ],
            }
        )
        self.assertEqual(
            [{"path": "docs/review.md", "summary": "补充 nightly review 如何自动拆长文件和回写文档说明"}],
            bundle["doc_updates"],
        )


if __name__ == "__main__":
    unittest.main()
