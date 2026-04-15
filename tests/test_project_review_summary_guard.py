from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from summary_guard import build_project_summary, validate_project_summary


class TaskReviewSummaryGuardTest(unittest.TestCase):
    def test_build_summary_keeps_plain_language_shape(self) -> None:
        summary = build_project_summary("小程序", "登录页", "支付联调", "补测试")
        self.assertLessEqual(len(summary), 50)
        self.assertIn("做了", summary)
        self.assertIn("还差", summary)
        self.assertIn("下一步", summary)

    def test_build_summary_trims_long_input(self) -> None:
        summary = build_project_summary(
            "特别长的项目名字",
            "登录页和商品页还有订单页",
            "支付联调和消息通知还有埋点核对",
            "补测试并检查真机报错",
            limit=50,
        )
        self.assertLessEqual(len(summary), 50)
        self.assertIn("下一步", summary)

    def test_validate_rejects_banned_terms(self) -> None:
        result = validate_project_summary("小程序完成核心能力沉淀，下一步持续闭环推进。")
        self.assertFalse(result.ok)
        self.assertTrue(any("禁用词" in issue for issue in result.issues))

    def test_validate_requires_three_part_shape(self) -> None:
        result = validate_project_summary("小程序做了登录页。")
        self.assertFalse(result.ok)
        self.assertTrue(any("三段信息" in issue for issue in result.issues))


if __name__ == "__main__":
    unittest.main()
