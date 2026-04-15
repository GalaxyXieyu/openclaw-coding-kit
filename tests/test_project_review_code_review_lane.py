from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from code_review_lane import run_code_review_lane


class TaskReviewCodeReviewLaneTest(unittest.TestCase):
    def test_lane_generates_findings_from_metrics(self) -> None:
        result = run_code_review_lane(
            {
                "changed_files": ["src/api/home.ts", "src/pages/home/index.tsx"],
                "file_stats": [{"path": "src/pages/home/index.tsx", "line_count": 1088}],
                "function_stats": [{"path": "src/api/home.ts", "name": "loadHome", "line_count": 128}],
                "duplicate_groups": [{"files": ["src/pages/home/index.tsx"], "summary": "首页和详情页有重复逻辑"}],
                "api_contract_checked": False,
                "missing_error_handling": True,
                "reference_errors": ["src/api/home.ts:12 找不到 loadProfile 引用"],
            }
        )
        titles = [item["title"] for item in result["findings"]]
        self.assertIn("单文件超过 1000 行", titles)
        self.assertIn("函数过长", titles)
        self.assertIn("重复代码", titles)
        self.assertIn("API 契约未确认", titles)
        self.assertIn("缺少异常处理", titles)
        self.assertIn("缺少测试覆盖", titles)
        self.assertIn("引用异常", titles)


if __name__ == "__main__":
    unittest.main()
