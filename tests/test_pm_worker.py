from __future__ import annotations

import unittest
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_worker import build_coder_handoff_contract, build_run_message


class PmWorkerTest(unittest.TestCase):
    def test_handoff_prefers_structured_gsd_contract(self) -> None:
        bundle = {
            "project": {"name": "demo", "repo_root": "/repo"},
            "bootstrap": {"recommended_action": "map-codebase", "project_mode": "brownfield"},
            "inputs": {
                "config": "/repo/pm.json",
                "context_path": "/repo/.pm/current-context.json",
                "bootstrap_path": "/repo/.pm/bootstrap.json",
            },
            "current_task": {
                "task_id": "T12",
                "summary": "[T12] Refactor PM backend seam",
                "description": "任务编号：T12",
                "gsd_contract": {
                    "plan_path": ".planning/phases/05/05-01-PLAN.md",
                    "context_path": ".planning/phases/05/05-CONTEXT.md",
                    "required_reads": [
                        ".planning/phases/05/05-01-PLAN.md",
                        ".planning/STATE.md",
                    ],
                },
            },
            "recommended_flow": ["Implement the current task first and update progress through pm when done."],
        }
        contract = build_coder_handoff_contract(bundle)
        self.assertTrue(contract["gsd_contract_present"])
        self.assertEqual(contract["gsd_plan_path"], ".planning/phases/05/05-01-PLAN.md")
        self.assertIn(".planning/STATE.md", contract["required_reads"])
        message = build_run_message({**bundle, "handoff_contract": contract})
        self.assertIn("structured handoff contract", message)
        self.assertIn("Read GSD plan first", message)


if __name__ == "__main__":
    unittest.main()
