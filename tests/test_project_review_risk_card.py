from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_review_bundle import build_review_bundle
from risk_card_builder import build_card_payload


class TaskReviewRiskCardTest(unittest.TestCase):
    def test_build_code_health_card_counts_severity_and_top_risks(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "code-health",
                "project_name": "主项目群",
                "changed_files": ["src/pages/home/index.tsx"],
                "commits": [{"hash": "abc123", "subject": "fix home"}],
                "llm_reviews": {
                    "code-review": {
                        "lane": "code-review",
                        "summary": "订单有真实风险",
                        "findings": [
                            {
                                "severity": "P1",
                                "title": "退款审核结果没有同步回写订单主状态",
                                "summary": "退款处理后前端还会显示退款中",
                                "card_title": "退款后状态可能不对",
                                "card_summary": "退款处理完了，前端可能还显示退款中。",
                                "file": "src/orders/refund.ts",
                                "suggestion": "补主订单状态回写",
                            }
                        ],
                        "docs_flags": [],
                        "next_actions": ["先补主订单状态回写"],
                    },
                    "docs-review": {
                        "lane": "docs-review",
                        "summary": "文档也有偏差",
                        "findings": [
                            {
                                "severity": "P2",
                                "title": "页面路由文档还是旧的",
                                "summary": "联调会跑错页面",
                                "card_title": "页面文档还是旧的",
                                "card_summary": "测试如果照文档走，会直接打开错页面。",
                                "file": "docs/home.md",
                                "suggestion": "重写页面矩阵",
                            }
                        ],
                        "docs_flags": ["AGENTS.md 需要更新", "docs/home.md 可能过期"],
                        "next_actions": ["再补页面路由文档"],
                    },
                },
            }
        )
        card = build_card_payload(bundle)
        self.assertEqual("code_health_risk_card_v1", card["card_kind"])
        self.assertEqual({"P0": 0, "P1": 1, "P2": 1}, card["severity_counts"])
        self.assertEqual(2, len(card["top_risks"]))
        self.assertTrue(card["changed_scope"]["requires_uiux"])
        self.assertEqual("退款审核结果没有同步回写订单主状态", card["top_risks"][0]["title"])
        self.assertEqual("页面路由文档还是旧的", card["top_risks"][1]["title"])
        self.assertEqual(["开始修复", "忽略这次"], card["actions"])

    def test_build_weekly_review_card_keeps_project_rows(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "weekly",
                "project_name": "主项目群",
                "project_summaries": [
                    {
                        "project": "官网",
                        "done": "首页",
                        "pending": "表单",
                        "next_step": "接提交",
                    }
                ],
                "tasks": {"completed": [{"id": "T1"}], "active": [{"id": "T2"}], "blocked": [{"id": "T3"}]},
            }
        )
        card = build_card_payload(bundle)
        self.assertEqual("weekly_review_card_v1", card["card_kind"])
        self.assertEqual("本周项目回顾", card["title"])
        self.assertEqual([], card["actions"])
        self.assertEqual(1, card["stats"]["completed_count"])
        self.assertEqual("官网做了首页，还差表单，下一步先接提交。", card["projects"][0]["summary"])

    def test_build_daily_review_card_is_code_review_focused_and_has_no_actions(self) -> None:
        bundle = build_review_bundle(
            {
                "trigger_kind": "daily",
                "project_name": "选育溯源小程序",
                "changed_files": ["src/pages/home/index.tsx", "docs/review.md"],
                "commits": [{"hash": "abc123", "subject": "fix: update home"}],
                "file_stats": [{"path": "src/pages/home/index.tsx", "line_count": 920}],
                "reference_errors": [],
                "doc_updates": [
                    {
                        "path": "docs/review.md",
                        "summary": "补充 nightly review 的自动修复规则和文档回写口径",
                    }
                ],
                "llm_reviews": {
                    "code-review": {
                        "lane": "code-review",
                        "findings": [
                            {
                                "severity": "P1",
                                "title": "退款后状态可能不对",
                                "summary": "退款处理完了，前端可能还显示退款中。",
                                "file": "src/orders/refund.ts",
                                "suggestion": "补主订单状态回写",
                            }
                        ],
                        "next_actions": ["先补主订单状态回写"],
                    },
                    "docs-review": {
                        "lane": "docs-review",
                        "docs_flags": ["AGENTS.md 需要更新"],
                    },
                },
            }
        )
        card = build_card_payload(bundle)
        self.assertEqual("daily_review_card_v1", card["card_kind"])
        self.assertEqual("每日项目回顾", card["title"])
        self.assertEqual([], card["actions"])
        self.assertEqual({"P0": 0, "P1": 1, "P2": 0}, card["severity_counts"])
        self.assertEqual(["AGENTS.md 需要更新"], card["docs_flags"])
        self.assertEqual(
            [{"path": "docs/review.md", "summary": "补充 nightly review 的自动修复规则和文档回写口径"}],
            card["doc_updates"],
        )
        self.assertEqual(["更新 home"], card["today_updates"])
        self.assertEqual(["src/pages/home/index.tsx", "docs/review.md"], card["file_highlights"][:2])
        checks = {item["label"]: item for item in card["audit_checks"]}
        self.assertEqual("warn", checks["单文件 > 1000 行"]["status"])
        self.assertEqual("ok", checks["导入/引用异常"]["status"])
        self.assertEqual("warn", checks["功能文档同步"]["status"])


if __name__ == "__main__":
    unittest.main()
