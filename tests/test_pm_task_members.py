from __future__ import annotations

import unittest
from pathlib import Path
import sys


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_task_members import normalize_task_members
from pm_task_members import resolve_default_task_members


class PmTaskMembersTest(unittest.TestCase):
    def test_normalize_task_members_prefers_assignee_role(self) -> None:
        members = normalize_task_members(
            [
                {"id": "ou_a", "role": "follower"},
                {"id": "ou_a", "role": "assignee"},
                {"id": "ou_b"},
                {"id": ""},
            ]
        )
        self.assertEqual(
            members,
            [
                {"id": "ou_a", "role": "assignee"},
                {"id": "ou_b", "role": "assignee"},
            ],
        )

    def test_resolve_default_task_members_assigns_current_user_by_default(self) -> None:
        members = resolve_default_task_members(task_config={}, current_user_id="ou_self")
        self.assertEqual(members, [{"id": "ou_self", "role": "assignee"}])

    def test_resolve_default_task_members_keeps_current_user_as_collaborator(self) -> None:
        members = resolve_default_task_members(
            task_config={
                "default_members": [{"id": "ou_reviewer", "role": "follower"}],
                "default_assignees": ["ou_partner"],
            },
            current_user_id="ou_self",
        )
        self.assertEqual(
            members,
            [
                {"id": "ou_reviewer", "role": "follower"},
                {"id": "ou_partner", "role": "assignee"},
                {"id": "ou_self", "role": "follower"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
