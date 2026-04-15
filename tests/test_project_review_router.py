from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from review_router import route_review, touches_ui_paths


class TaskReviewRouterTest(unittest.TestCase):
    def test_daily_route_uses_code_review_lanes(self) -> None:
        route = route_review(
            "daily",
            changed_files=["src/pages/home/index.tsx", "docs/review.md"],
            has_recent_commits=True,
        )
        self.assertTrue(route.should_run)
        self.assertEqual("daily_review_card_v1", route.card_kind)
        self.assertEqual(("code-review", "docs-review", "ui-ux-review"), route.lanes)

    def test_code_health_route_adds_uiux_for_ui_changes(self) -> None:
        route = route_review(
            "code-health",
            changed_files=["src/pages/home/index.tsx", "docs/review.md"],
            has_recent_commits=True,
        )
        self.assertTrue(route.should_run)
        self.assertEqual("code_health_risk_card_v1", route.card_kind)
        self.assertEqual(("code-review", "docs-review", "ui-ux-review"), route.lanes)

    def test_code_health_route_skips_without_recent_commits(self) -> None:
        route = route_review("code-health", has_recent_commits=False)
        self.assertFalse(route.should_run)
        self.assertEqual(tuple(), route.lanes)
        self.assertIn("没有新的 commit", route.skip_reason)

    def test_weekly_route_can_enable_graph_observe(self) -> None:
        route = route_review("weekly", enable_graph=True)
        self.assertEqual(("project-retro", "graph-observe"), route.lanes)
        self.assertTrue(route.uses_graph_observe)

    def test_touch_ui_paths_detects_prefix_and_suffix(self) -> None:
        self.assertTrue(touches_ui_paths(["components/button/index.ts", "README.md"]))
        self.assertTrue(touches_ui_paths(["docs/design.css"]))
        self.assertFalse(touches_ui_paths(["docs/review.md", "scripts/check.py"]))


if __name__ == "__main__":
    unittest.main()
