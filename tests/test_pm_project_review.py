from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_project_review import register_main_review_source, register_nightly_review_job


class PmProjectReviewRegistryTest(unittest.TestCase):
    def test_register_main_review_source_bootstraps_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            openclaw_config = root / "openclaw.json"
            openclaw_config.write_text("{}", encoding="utf-8")
            repo_root = root / "repo"
            repo_root.mkdir()
            template_path = root / "template.json"
            template_path.write_text(
                json.dumps(
                    {
                        "main_target": {
                            "alias": "main",
                            "channel": "feishu",
                            "chat_id": "oc_main",
                            "chat_name": "宇宇",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = register_main_review_source(
                openclaw_config_path=openclaw_config,
                repo_root=repo_root,
                project_name="项目一",
                source_key="project-one",
                template_path=template_path,
            )

            self.assertEqual("ok", result["status"])
            self.assertTrue(result["created_config"])
            config_path = Path(result["config_path"])
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("oc_main", payload["main_target"]["chat_id"])
            self.assertEqual("project-one", payload["sources"][0]["key"])
            self.assertTrue(payload["sources"][0]["enabled"])

    def test_register_main_review_source_preserves_disabled_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            openclaw_config = root / "openclaw.json"
            openclaw_config.write_text("{}", encoding="utf-8")
            registry_dir = root / "project-review"
            registry_dir.mkdir()
            config_path = registry_dir / "main_review_sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "main_target": {"chat_id": "oc_main"},
                        "sources": [
                            {
                                "key": "project-one",
                                "project_name": "旧名字",
                                "repo_root": str((root / "repo").resolve()),
                                "enabled": False,
                            }
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = register_main_review_source(
                openclaw_config_path=openclaw_config,
                repo_root=root / "repo",
                project_name="新名字",
                source_key="project-one",
            )

            self.assertEqual("ok", result["status"])
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual("新名字", payload["sources"][0]["project_name"])
            self.assertFalse(payload["sources"][0]["enabled"])

    def test_register_nightly_review_job_bootstraps_cron_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            openclaw_config = root / "openclaw.json"
            openclaw_config.write_text("{}", encoding="utf-8")
            repo_root = root / "repo"
            repo_root.mkdir()
            pm_config = repo_root / "pm.json"
            pm_config.write_text("{}", encoding="utf-8")

            result = register_nightly_review_job(
                openclaw_config_path=openclaw_config,
                repo_root=repo_root,
                pm_config_path=pm_config,
                project_name="PM工具链",
                reviewer_model="codex",
            )

            self.assertEqual("ok", result["status"])
            jobs_path = Path(result["jobs_path"])
            payload = json.loads(jobs_path.read_text(encoding="utf-8"))
            self.assertEqual(1, len(payload["jobs"]))
            job = payload["jobs"][0]
            self.assertEqual("main", job["agentId"])
            self.assertEqual("agent:main:main", job["sessionKey"])
            self.assertIn("nightly_auto_review.py", job["payload"]["message"])
            self.assertIn(str(repo_root), job["payload"]["message"])


if __name__ == "__main__":
    unittest.main()
