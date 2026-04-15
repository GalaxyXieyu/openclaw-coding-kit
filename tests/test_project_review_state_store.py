from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from review_state_store import append_history, get_review_by_dedupe_key, load_state, stable_json_hash, upsert_review_record, update_review_status


class TaskReviewStateStoreTest(unittest.TestCase):
    def test_stable_json_hash_is_order_insensitive(self) -> None:
        left = stable_json_hash({"a": 1, "b": 2})
        right = stable_json_hash({"b": 2, "a": 1})
        self.assertEqual(left, right)

    def test_upsert_and_update_review_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            upsert_review_record(
                state_path,
                {
                    "review_id": "R1",
                    "dedupe_key": "weekly:demo",
                    "status": "sent",
                    "history": [{"event": "created"}],
                },
            )
            state = load_state(state_path)
            self.assertEqual("R1", state["reviews"][0]["review_id"])
            self.assertEqual("weekly:demo", get_review_by_dedupe_key(state, "weekly:demo")["dedupe_key"])
            update_review_status(state_path, "R1", status="archived", updated_at="2026-04-14T10:00:00+08:00")
            append_history(state_path, "R1", {"event": "manual_note"})
            updated = load_state(state_path)["reviews"][0]
            self.assertEqual("archived", updated["status"])
            self.assertEqual(3, len(updated["history"]))


if __name__ == "__main__":
    unittest.main()
