from __future__ import annotations

import argparse
from typing import Any

from pm_command_support import CommandHandler, emit_json


def build_gsd_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def emit(payload: dict[str, Any]) -> int:
        return emit_json(payload)

    def cmd_sync_gsd_docs(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.sync_gsd_docs(root=root, include=list(args.include or []))
        refreshed = api.refresh_context_cache()
        payload["context_path"] = str(api.pm_file("current-context.json", str(root)))
        payload["doc_index"] = refreshed.get("doc_index") or {}
        payload["gsd"] = refreshed.get("gsd") or {}
        return emit(payload)

    def cmd_sync_gsd_progress(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        task_guid = str(args.task_guid or "").strip()
        if not task_guid and str(args.task_id or "").strip():
            task = api.get_task_record(args.task_id, include_completed=args.include_completed)
            task_guid = str(task.get("guid") or "").strip()
        payload = api.sync_gsd_progress(
            root=root,
            phase=str(args.phase or "").strip(),
            task_guid=task_guid,
            append_to_state=not args.no_state_append,
        )
        payload["context_path"] = str(api.pm_file("current-context.json", str(root)))
        return emit(payload)

    def cmd_materialize_gsd_tasks(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.materialize_gsd_tasks(root=root, phase=str(args.phase or "").strip())
        refreshed = api.refresh_context_cache()
        payload["context_path"] = str(api.pm_file("current-context.json", str(root)))
        payload["doc_index"] = refreshed.get("doc_index") or {}
        payload["gsd"] = refreshed.get("gsd") or {}
        return emit(payload)

    def cmd_route_gsd(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.route_gsd_work(root, phase=str(args.phase or "").strip(), prefer_pm_tasks=True)
        refreshed = api.refresh_context_cache()
        return emit(
            {
                "repo_root": str(root),
                "route": payload,
                "context_path": str(api.pm_file("current-context.json", str(root))),
                "doc_index": refreshed.get("doc_index") or {},
                "gsd": refreshed.get("gsd") or {},
            }
        )

    def cmd_plan_phase(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.plan_gsd_phase_workflow(
            root=root,
            phase=str(args.phase or "").strip(),
            task_id=str(args.task_id or "").strip(),
            task_guid=str(args.task_guid or "").strip(),
            include_completed=bool(args.include_completed),
            agent_id=str(args.agent or "").strip(),
            timeout_seconds=int(args.timeout or 0),
            thinking=str(args.thinking or "").strip(),
            research=bool(args.research),
            skip_research=bool(args.skip_research),
            gaps=bool(args.gaps),
            skip_verify=bool(args.skip_verify),
            prd=str(args.prd or "").strip(),
            reviews=bool(args.reviews),
            sync_docs=not args.no_doc_sync,
            sync_progress=not args.no_progress_sync,
            append_state=not args.no_state_append,
        )
        return emit(payload)

    return {
        "sync_gsd_docs": cmd_sync_gsd_docs,
        "sync_gsd_progress": cmd_sync_gsd_progress,
        "materialize_gsd_tasks": cmd_materialize_gsd_tasks,
        "route_gsd": cmd_route_gsd,
        "plan_phase": cmd_plan_phase,
    }
