from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "pm" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_gsd_materializer import materialize_gsd_tasks


class PmGsdMaterializerTest(unittest.TestCase):
    def test_materialize_writes_binding_index_and_local_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls: dict[str, list[dict]] = {"create": [], "patch": []}
            tasks: dict[str, dict] = {}

            def ensure_tasklist() -> dict:
                return {"guid": "local:demo", "owner": {"id": "local-user"}}

            def task_pool(**_: object) -> list[dict]:
                return list(tasks.values())

            def get_task_record_by_guid(task_guid: str) -> dict:
                return tasks[task_guid]

            def parse_task_summary(summary: str) -> dict | None:
                if summary.startswith("[T1]"):
                    return {"task_id": "T1", "number": 1}
                return None

            def build_normalized_summary_from_text(task_id: str, summary: str) -> str:
                return f"[{task_id}] {summary}"

            def build_gsd_task_summary_body(plan: dict) -> str:
                return str(plan.get("objective") or "fallback")

            def build_gsd_task_description(task_id: str, plan: dict, repo_root: Path) -> str:
                return f"任务编号：{task_id}\nGSD Plan Path: {plan['plan_path']}\nRepo：{repo_root}"

            def build_gsd_task_contract(_root: Path, plan: dict) -> dict:
                return {
                    "phase": str(plan.get("phase") or ""),
                    "plan_path": str(plan.get("plan_path") or ""),
                    "summary_path": str(plan.get("summary_path") or ""),
                    "context_path": ".planning/phases/05/05-CONTEXT.md",
                    "required_reads": [str(plan.get("plan_path") or ""), ".planning/STATE.md"],
                }

            def create_task(**kwargs: object) -> dict:
                calls["create"].append(dict(kwargs))
                task = {
                    "guid": "local-task-1",
                    "url": "local://task/local-task-1",
                    "summary": kwargs["summary"],
                    "description": kwargs["description"],
                    "gsd_contract": kwargs.get("gsd_contract") or {},
                    "completed_at": "",
                }
                tasks[task["guid"]] = task
                return task

            def patch_task(task_guid: str, changes: dict) -> dict:
                calls["patch"].append({"task_guid": task_guid, **changes})
                tasks[task_guid].update(changes)
                return tasks[task_guid]

            def write_repo_json(path: Path, payload: dict) -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

            payload = materialize_gsd_tasks(
                root=root,
                phase_payload={
                    "phase": "5",
                    "phase_dir": ".planning/phases/05-demo",
                    "phase_name": "Demo",
                    "plans": [
                        {
                            "phase": "5",
                            "plan_path": ".planning/phases/05-demo/05-01-PLAN.md",
                            "summary_path": ".planning/phases/05-demo/05-01-SUMMARY.md",
                            "objective": "Refactor PM backend seam",
                            "has_summary": True,
                        }
                    ],
                },
                ensure_tasklist=ensure_tasklist,
                task_pool=task_pool,
                get_task_record_by_guid=get_task_record_by_guid,
                extract_task_number=lambda _: 0,
                parse_task_summary=parse_task_summary,
                parse_task_id_from_description=lambda _: "",
                extract_gsd_task_binding=lambda _: {},
                task_prefix=lambda: "T",
                build_normalized_summary_from_text=build_normalized_summary_from_text,
                build_gsd_task_summary_body=build_gsd_task_summary_body,
                build_gsd_task_description=build_gsd_task_description,
                build_gsd_task_contract=build_gsd_task_contract,
                create_task=create_task,
                patch_task=patch_task,
                now_iso=lambda: "2026-04-07T12:00:00+08:00",
                binding_index_path=root / ".pm" / "gsd-task-bindings.json",
                write_repo_json=write_repo_json,
            )

            self.assertEqual(payload["created_count"], 1)
            self.assertEqual(payload["completed_synced_count"], 1)
            self.assertEqual(calls["create"][0]["gsd_contract"]["plan_path"], ".planning/phases/05-demo/05-01-PLAN.md")
            binding_index = json.loads((root / ".pm" / "gsd-task-bindings.json").read_text(encoding="utf-8"))
            self.assertEqual(binding_index["bindings"][0]["contract"]["phase"], "5")
            self.assertTrue(any(call.get("completed_at") for call in calls["patch"]))


if __name__ == "__main__":
    unittest.main()
