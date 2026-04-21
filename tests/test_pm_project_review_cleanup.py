from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_project_review import register_main_digest_source
from pm_project_review import register_nightly_review_job
from pm_project_review import unregister_main_digest_source
from pm_project_review import unregister_nightly_review_job


class PmProjectReviewCleanupTest(unittest.TestCase):
    def test_unregister_main_digest_source_removes_matching_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            openclaw_config_path = root / "openclaw.json"
            openclaw_config_path.write_text("{}", encoding="utf-8")
            repo_root = root / "repo"
            repo_root.mkdir()

            register_main_digest_source(
                openclaw_config_path=openclaw_config_path,
                repo_root=repo_root,
                project_name="Demo Project",
                source_key="demo-project",
            )
            payload = unregister_main_digest_source(
                openclaw_config_path=openclaw_config_path,
                repo_root=repo_root,
                source_key="demo-project",
            )

            self.assertEqual("deleted", payload["status"])
            self.assertEqual("demo-project", payload["removed"][0]["key"])

    def test_unregister_nightly_review_job_removes_matching_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            openclaw_config_path = root / "openclaw.json"
            openclaw_config_path.write_text("{}", encoding="utf-8")
            repo_root = root / "repo"
            repo_root.mkdir()
            pm_config_path = repo_root / "pm.json"
            pm_config_path.write_text(json.dumps({"project": {"name": "Demo Project"}}, ensure_ascii=False), encoding="utf-8")

            register_nightly_review_job(
                openclaw_config_path=openclaw_config_path,
                repo_root=repo_root,
                pm_config_path=pm_config_path,
                project_name="Demo Project",
                agent_id="demo-agent",
                group_id="oc_demo",
            )
            payload = unregister_nightly_review_job(
                openclaw_config_path=openclaw_config_path,
                repo_root=repo_root,
                project_name="Demo Project",
            )

            self.assertEqual("deleted", payload["status"])
            self.assertEqual("Project review · Demo Project", payload["removed"][0]["name"])


if __name__ == "__main__":
    unittest.main()
