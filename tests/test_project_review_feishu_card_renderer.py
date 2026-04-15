from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from feishu_card_renderer import build_feishu_card


class ProjectReviewFeishuCardRendererTest(unittest.TestCase):
    def test_build_review_card_renders_project_summaries(self) -> None:
        card = build_feishu_card(
            {
                "review_id": "RV-demo",
                "updated_at": "2026-04-14T20:00:00+08:00",
                "card_kind": "weekly_review_card_v1",
                "card_preview": {
                    "card_kind": "weekly_review_card_v1",
                    "title": "本周项目回顾",
                    "projects": [
                        {
                            "project": "小程序",
                            "summary": "小程序做了登录页，还差支付联调，下一步先补测试。",
                            "status": "推进中",
                            "next_step": "补测试",
                        }
                    ],
                    "stats": {
                        "completed_count": 1,
                        "active_count": 2,
                        "blocked_count": 0,
                        "stale_count": 0,
                    },
                },
                "bundle": {
                    "project": {"name": "主项目群"},
                },
            }
        )

        self.assertEqual("本周项目回顾", card["header"]["title"]["content"])
        self.assertEqual("blue", card["header"]["template"])
        content = card["elements"][0]["text"]["content"]
        self.assertIn("**小程序** · 推进中", content)
        self.assertIn("下步先看", content)
        self.assertEqual(1, len(card["elements"]))

    def test_build_code_health_card_renders_risks_and_docs_flags(self) -> None:
        card = build_feishu_card(
            {
                "review_id": "RV-risk",
                "updated_at": "2026-04-14T20:00:00+08:00",
                "card_kind": "code_health_risk_card_v1",
                "card_preview": {
                    "card_kind": "code_health_risk_card_v1",
                    "title": "代码健康提醒",
                    "severity_counts": {"P0": 0, "P1": 2, "P2": 1},
                    "top_risks": [
                        {
                            "severity": "P1",
                            "title": "物流回写按单个运单直接改整单状态，会提前完成或覆盖更高优先级状态",
                            "summary": "Every tracking refresh/webhook rewrites the whole order to SHIPPED or COMPLETED.",
                            "card_title": "物流状态可能把整张订单提前改完成",
                            "card_summary": "只要一个运单更新，整张订单就可能被提前改成已发货或已完成，多包裹和退款中的订单最容易出错。",
                            "suggestion": "先核对物流状态更新是不是按整单汇总后再回写。",
                            "file": "apps/api/src/supply/supply.service.ts",
                        }
                    ],
                    "docs_flags": ["canonical-miniapp-route-drift"],
                    "changed_scope": {"requires_uiux": True},
                    "commit_window": {"count": 3, "latest_subject": "feat: update home"},
                    "actions": ["开始修复", "忽略这次"],
                    "next_actions": ["先核对物流状态更新是不是按整单汇总后再回写。"],
                },
                "bundle": {
                    "project": {"name": "主项目群"},
                    "changed_scope": {
                        "files": [
                            "apps/api/src/supply/supply.service.ts",
                            "apps/miniapp/src/styles/guiquan/supply.css",
                            "docs/miniapp-runbook.md",
                        ]
                    },
                },
            }
        )

        self.assertEqual("orange", card["header"]["template"])
        content = card["elements"][0]["text"]["content"]
        self.assertIn("P0 0 · P1 2 · P2 1", content)
        self.assertIn("现在最要紧的 3 件事", content)
        self.assertIn("页面路由说明和真实跳转可能对不上", content)
        self.assertIn("建议怎么做", content)
        self.assertIn("整张订单就可能被提前改成已发货或已完成", content)
        self.assertIn("文件索引", content)
        self.assertIn("[F1]", content)
        self.assertEqual("action", card["elements"][-1]["tag"])
        labels = [item["text"]["content"] for item in card["elements"][-1]["actions"]]
        self.assertEqual(["开始修复", "忽略这次"], labels)

    def test_build_daily_review_card_renders_without_buttons(self) -> None:
        card = build_feishu_card(
            {
                "review_id": "RV-daily",
                "updated_at": "2026-04-15T14:20:00+08:00",
                "card_kind": "daily_review_card_v1",
                "card_preview": {
                    "card_kind": "daily_review_card_v1",
                    "title": "每日项目回顾",
                    "review_summary": "今天先按代码和文档两条线回顾。",
                    "today_updates": ["同步 weapp 入口和卖家市场更新", "收尾 supply cart 样式"],
                    "file_highlights": ["apps/miniapp/app.json", "apps/miniapp/src/features/guiquan/screen.tsx"],
                    "audit_checks": [
                        {
                            "label": "单文件 > 1000 行",
                            "status": "ok",
                            "detail": "本次变更里没发现超过 1000 行的文件。",
                        },
                        {
                            "label": "导入/引用异常",
                            "status": "unknown",
                            "detail": "这次没有带编译或静态检查结果，暂时看不到这类报错。",
                        },
                    ],
                    "focus_findings": [
                        {
                            "title": "退款后状态可能不对",
                            "card_title": "退款后状态可能不对",
                            "card_summary": "退款处理完了，前端可能还显示退款中。",
                            "file": "src/orders/refund.ts",
                            "suggestion": "补主订单状态回写",
                        }
                    ],
                    "doc_updates": [
                        {
                            "path": "docs/review.md",
                            "summary": "补充 nightly review 如何自动拆长文件和同步文档",
                        }
                    ],
                    "docs_flags": ["canonical-miniapp-route-drift"],
                    "changed_scope": {"requires_uiux": True},
                    "commit_window": {"count": 2, "latest_subject": "fix: update refund status"},
                    "next_actions": ["先补主订单状态回写"],
                    "automation_updates": ["已自动创建并执行修复任务 T88。"],
                    "actions": [],
                },
                "bundle": {
                    "project": {"name": "选育溯源小程序"},
                    "changed_scope": {"files": ["src/orders/refund.ts", "docs/review.md"]},
                    "commits": [{"subject": "fix: update refund status"}],
                },
            }
        )

        self.assertEqual("每日项目回顾", card["header"]["title"]["content"])
        content = card["elements"][0]["text"]["content"]
        self.assertIn("今天具体推进", content)
        self.assertIn("今天实际改到的范围", content)
        self.assertIn("主要落在", content)
        self.assertIn("审核结果", content)
        self.assertIn("今天文档主要更新了什么", content)
        self.assertIn("最值得看的问题", content)
        self.assertIn("下一步", content)
        self.assertIn("自动处理", content)
        self.assertIn("文件索引", content)
        self.assertIn("[F1]", content)
        self.assertNotIn("P0 0 · P1 1 · P2 0", content)
        self.assertEqual(1, len(card["elements"]))


if __name__ == "__main__":
    unittest.main()
