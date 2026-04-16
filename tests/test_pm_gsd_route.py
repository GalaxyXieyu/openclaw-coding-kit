from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_gsd import build_gsd_route


class PmGsdRouteTest(unittest.TestCase):
    def test_brownfield_bootstrap_prefers_map_codebase(self) -> None:
        with patch("pm_gsd.detect_gsd_assets", return_value={"enabled": False}), patch(
            "pm_gsd.gsd_runtime_status",
            return_value={"ready": True},
        ):
            payload = build_gsd_route(Path("/tmp/demo"), project_mode="brownfield")

        self.assertEqual(payload["route"], "bootstrap")
        self.assertEqual(payload["recommended_gsd_skill"], "gsd-map-codebase")
        self.assertEqual(payload["recommended_mode"], "bootstrap")
        self.assertEqual(payload["runtime"]["ready"], True)

    def test_phase_with_context_and_no_plan_routes_to_plan_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            context_path = ".planning/phases/05-demo/05-CONTEXT.md"
            (root / context_path).parent.mkdir(parents=True, exist_ok=True)
            (root / context_path).write_text("# context\n", encoding="utf-8")

            with patch("pm_gsd.detect_gsd_assets", return_value={"enabled": True}), patch(
                "pm_gsd.gsd_runtime_status",
                return_value={"ready": True},
            ), patch(
                "pm_gsd.build_gsd_progress_snapshot",
                return_value={
                    "phase": "5",
                    "phase_info": {"plan_count": 0, "summary_count": 0, "name": "Demo", "has_context": True},
                    "roadmap_analysis": {},
                },
            ), patch(
                "pm_gsd.list_gsd_phase_plans",
                return_value={"phase": "5", "phase_dir": ".planning/phases/05-demo", "phase_name": "Demo", "plans": []},
            ), patch("pm_gsd.gsd_phase_context_path", return_value=context_path):
                payload = build_gsd_route(root, project_mode="brownfield")

        self.assertEqual(payload["route"], "plan-phase")
        self.assertEqual(payload["phase"], "5")
        self.assertEqual(payload["phase_name"], "Demo")
        self.assertEqual(payload["context_path"], context_path)


if __name__ == "__main__":
    unittest.main()
