from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from docs_review_lane import run_docs_review_lane


class TaskReviewDocsReviewLaneTest(unittest.TestCase):
    def test_lane_detects_docs_drift_and_agents_gap(self) -> None:
        result = run_docs_review_lane(
            {
                "changed_files": ["src/pages/home/index.tsx", "scripts/build.py"],
                "repo_has_agents": False,
                "stale_doc_candidates": ["docs/old-flow.md"],
                "duplicate_tool_candidates": ["scripts/check_a.py vs scripts/check_b.py"],
            }
        )
        flags = result["docs_flags"]
        self.assertIn("代码改了，但没看到 docs 更新。", flags)
        self.assertIn("仓库还没有 AGENTS.md。", flags)
        self.assertTrue(any("过期文档候选" in item for item in flags))
        self.assertTrue(any("工具可能重复" in item for item in flags))


if __name__ == "__main__":
    unittest.main()
