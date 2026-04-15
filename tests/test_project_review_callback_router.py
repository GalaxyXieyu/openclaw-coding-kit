from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from callback_router import apply_callback_action, route_callback_action
from review_state_store import load_state, upsert_review_record


class TaskReviewCallbackRouterTest(unittest.TestCase):
    def test_route_fix_action_triggers_fix_flow(self) -> None:
        decision = route_callback_action(
            "code_health_risk_card_v1",
            "开始修复",
            now_iso="2026-04-14T10:00:00+08:00",
        )
        self.assertEqual("fix_now", decision.action_id)
        self.assertEqual("acked", decision.next_state)
        self.assertTrue(decision.should_trigger_fix)

    def test_apply_snooze_action_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            upsert_review_record(
                state_path,
                {
                    "review_id": "R2",
                    "dedupe_key": "code-health:demo",
                    "status": "sent",
                    "history": [],
                },
            )
            result = apply_callback_action(
                str(state_path),
                review_id="R2",
                card_kind="code_health_risk_card_v1",
                action="明天再看",
                now_iso="2026-04-14T10:00:00+08:00",
            )
            self.assertEqual("snoozed", result["decision"]["next_state"])
            self.assertTrue(result["decision"]["snooze_until"].startswith("2026-04-15"))
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("snoozed", stored["status"])

    def test_apply_fix_action_triggers_fix_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            upsert_review_record(
                state_path,
                {
                    "review_id": "R3",
                    "dedupe_key": "code-health:demo:fix",
                    "status": "sent",
                    "history": [],
                },
            )
            result = apply_callback_action(
                str(state_path),
                review_id="R3",
                card_kind="code_health_risk_card_v1",
                action="开始修复",
                now_iso="2026-04-15T12:00:00+08:00",
                run_fix_executor_fn=lambda *args, **kwargs: {"status": "task_created", "task_id": "T11"},
            )
            self.assertEqual("acked", result["decision"]["next_state"])
            self.assertEqual("task_created", result["fix_execution"]["status"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("acked", stored["status"])


if __name__ == "__main__":
    unittest.main()
