from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_task_assignment import plan_task_assignee_backfill
from pm_task_assignment import task_assignment_auth_result


class PmTaskAssignmentTest(unittest.TestCase):
    def test_task_assignment_auth_result_unwraps_nested_token_payload(self) -> None:
        result = task_assignment_auth_result(
            ensure_user_token=lambda scopes: {
                "status": "authorized",
                "token": {
                    "access_token": "token_123",
                    "open_id": "ou_self",
                    "scope": " ".join(scopes),
                },
            },
            build_auth_link=lambda **kwargs: {},
            request_user_oauth_link=lambda **kwargs: {},
        )

        self.assertEqual(result["status"], "authorized")
        self.assertEqual(result["token"], "token_123")
        self.assertEqual(result["open_id"], "ou_self")
        self.assertEqual(result["token_payload"]["open_id"], "ou_self")

    def test_task_assignment_auth_result_returns_authorization_required(self) -> None:
        result = task_assignment_auth_result(
            ensure_user_token=lambda scopes: {
                "status": "authorization_required",
                "verification_uri_complete": "https://example.com/device",
                "user_code": "ABCD-EFGH",
                "scopes": list(scopes),
            },
            build_auth_link=lambda **kwargs: {"url": "https://example.com/auth"},
            request_user_oauth_link=lambda **kwargs: {"url": "https://example.com/oauth"},
        )

        self.assertEqual(result["status"], "authorization_required")
        self.assertEqual(result["verification_uri_complete"], "https://example.com/device")
        self.assertEqual(result["user_code"], "ABCD-EFGH")
        self.assertEqual(result["auth"]["url"], "https://example.com/auth")
        self.assertEqual(result["oauth"]["url"], "https://example.com/oauth")

    def test_plan_task_assignee_backfill_skips_when_role_change_is_required(self) -> None:
        plan = plan_task_assignee_backfill(
            {
                "creator": {"id": "ou_self"},
                "members": [{"id": "ou_self", "role": "follower"}],
            },
            [{"id": "ou_self", "role": "assignee"}],
            creator_only_user_id="ou_self",
        )

        self.assertEqual(plan["action"], "skip")
        self.assertEqual(plan["reason"], "role_change_required")

    def test_plan_task_assignee_backfill_adds_missing_assignee(self) -> None:
        plan = plan_task_assignee_backfill(
            {
                "creator": {"id": "ou_self"},
                "members": [],
            },
            [{"id": "ou_self", "role": "assignee"}],
            creator_only_user_id="ou_self",
        )

        self.assertEqual(
            plan,
            {
                "action": "add_members",
                "members": [{"id": "ou_self", "role": "assignee"}],
            },
        )


if __name__ == "__main__":
    unittest.main()
