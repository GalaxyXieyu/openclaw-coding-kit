from __future__ import annotations

import argparse
from typing import Any

from pm_command_support import CommandHandler, emit_json


def emit_gsd_payload(payload: dict[str, Any]) -> int:
    return emit_json(payload)


def activate_repo_root(api: Any, repo_root: str) -> Any:
    root = api.project_root_path(repo_root)
    api.ACTIVE_CONFIG["repo_root"] = str(root)
    return root


def gsd_context_snapshot(api: Any, root: Any) -> dict[str, Any]:
    refreshed = api.refresh_context_cache()
    return {
        "context_path": str(api.pm_file("current-context.json", str(root))),
        "doc_index": refreshed.get("doc_index") or {},
        "gsd": refreshed.get("gsd") or {},
    }


def resolve_gsd_task_guid(api: Any, args: argparse.Namespace) -> str:
    task_guid = str(args.task_guid or "").strip()
    if task_guid or not str(args.task_id or "").strip():
        return task_guid
    task = api.get_task_record(args.task_id, include_completed=args.include_completed)
    return str(task.get("guid") or "").strip()


def sync_gsd_docs_command(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    root = activate_repo_root(api, args.repo_root)
    payload = api.sync_gsd_docs(root=root, include=list(args.include or []))
    return {**payload, **gsd_context_snapshot(api, root)}


def sync_gsd_progress_command(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    root = activate_repo_root(api, args.repo_root)
    payload = api.sync_gsd_progress(
        root=root,
        phase=str(args.phase or "").strip(),
        task_guid=resolve_gsd_task_guid(api, args),
        append_to_state=not args.no_state_append,
    )
    return {
        **payload,
        "context_path": str(api.pm_file("current-context.json", str(root))),
    }


def materialize_gsd_tasks_command(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    root = activate_repo_root(api, args.repo_root)
    payload = api.materialize_gsd_tasks(root=root, phase=str(args.phase or "").strip())
    return {**payload, **gsd_context_snapshot(api, root)}


def route_gsd_command(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    root = activate_repo_root(api, args.repo_root)
    payload = api.route_gsd_work(root, phase=str(args.phase or "").strip(), prefer_pm_tasks=True)
    return {
        "repo_root": str(root),
        "route": payload,
        **gsd_context_snapshot(api, root),
    }


def plan_phase_command(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    root = activate_repo_root(api, args.repo_root)
    return api.plan_gsd_phase_workflow(
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


def build_gsd_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def cmd_sync_gsd_docs(args: argparse.Namespace) -> int:
        return emit_gsd_payload(sync_gsd_docs_command(api, args))

    def cmd_sync_gsd_progress(args: argparse.Namespace) -> int:
        return emit_gsd_payload(sync_gsd_progress_command(api, args))

    def cmd_materialize_gsd_tasks(args: argparse.Namespace) -> int:
        return emit_gsd_payload(materialize_gsd_tasks_command(api, args))

    def cmd_route_gsd(args: argparse.Namespace) -> int:
        return emit_gsd_payload(route_gsd_command(api, args))

    def cmd_plan_phase(args: argparse.Namespace) -> int:
        return emit_gsd_payload(plan_phase_command(api, args))

    return {
        "sync_gsd_docs": cmd_sync_gsd_docs,
        "sync_gsd_progress": cmd_sync_gsd_progress,
        "materialize_gsd_tasks": cmd_materialize_gsd_tasks,
        "route_gsd": cmd_route_gsd,
        "plan_phase": cmd_plan_phase,
    }
