from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PM_SCRIPT = REPO_ROOT / "skills" / "pm" / "scripts" / "pm.py"


class PmLocalCliTest(unittest.TestCase):
    def test_local_backend_supports_attachment_and_complete_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            planning = root / ".planning"
            planning.mkdir(parents=True)
            for name in ("PROJECT.md", "REQUIREMENTS.md", "ROADMAP.md", "STATE.md"):
                (planning / name).write_text(f"# {name}\n", encoding="utf-8")
            config = {
                "repo_root": str(root),
                "project": {"name": "demo"},
                "task": {"backend": "local", "tasklist_name": "demo", "prefix": "T", "kind": "task"},
                "doc": {"backend": "repo", "folder_name": "demo"},
                "coder": {"backend": "codex-cli", "agent_id": "codex", "timeout": 60, "thinking": "high", "session_key": "main"},
            }
            config_path = root / "pm.json"
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            evidence_file = root / "evidence.txt"
            evidence_file.write_text("evidence", encoding="utf-8")

            def run(*args: str) -> dict:
                proc = subprocess.run(
                    ["python3", str(PM_SCRIPT), "--config", str(config_path), *args],
                    cwd=str(root),
                    text=True,
                    capture_output=True,
                    check=True,
                )
                return json.loads(proc.stdout)

            created = run("create", "--summary", "Lifecycle task")
            self.assertEqual(created["task_id"], "T1")

            upload = run("upload-attachments", "--task-id", "T1", "--file", str(evidence_file))
            self.assertEqual(upload["status"], "ok")
            self.assertEqual(upload["backend"], "local")
            self.assertEqual(upload["uploaded_count"], 1)

            listed = run("attachments", "--task-id", "T1")
            self.assertEqual(listed["backend"], "local")
            self.assertEqual(listed["attachment_count"], 1)
            self.assertEqual(listed["attachments"][0]["name"], "evidence.txt")

            completed = run("complete", "--task-id", "T1", "--content", "done locally")
            self.assertEqual(completed["task_id"], "T1")
            task = run("get", "--task-id", "T1", "--include-completed")
            self.assertTrue(bool(task["completed_at"]))
            self.assertEqual(len(task["attachments"]), 1)
            self.assertTrue(any("done locally" in str(item.get("content") or "") for item in task["comments"]))


if __name__ == "__main__":
    unittest.main()
