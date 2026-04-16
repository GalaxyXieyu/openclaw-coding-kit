from __future__ import annotations

import argparse
from typing import Any


def _add_auth_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser], handlers: dict[str, Any]) -> None:
    auth_link = sub.add_parser("auth-link")
    auth_link.add_argument("--scopes", default="")
    auth_link.add_argument("--mode", default="app-scope", choices=["app-scope", "user-oauth"])
    auth_link.add_argument("--token-type", default="user", choices=["user", "tenant"])
    auth_link.set_defaults(func=handlers["auth_link"])

    permission_bundle = sub.add_parser("permission-bundle")
    permission_bundle.add_argument("--preset", action="append", default=[])
    permission_bundle.add_argument("--scope", action="append", default=[])
    permission_bundle.add_argument("--token-type", default="tenant", choices=["user", "tenant"])
    permission_bundle.add_argument("--list-presets", action="store_true", default=False)
    permission_bundle.set_defaults(func=handlers["permission_bundle"])

    auth = sub.add_parser("auth")
    auth.add_argument("--no-group-open-reply", action="store_true", default=False)
    auth.add_argument("--no-attachment-oauth", action="store_true", default=False)
    auth.set_defaults(func=handlers["auth"])


def _add_init_shared_arguments(
    parser: argparse.ArgumentParser,
    *,
    require_project_name: bool,
    require_group_id: bool,
    require_repo_root: bool,
) -> None:
    parser.add_argument(
        "--project-name",
        required=require_project_name,
        default="" if not require_project_name else argparse.SUPPRESS,
        help="Primary human-readable project name; defaults to repo name",
    )
    parser.add_argument("--english-name", default="", help="Optional ASCII name used for workspace/agent slug generation; required when --project-name contains non-ASCII characters")
    parser.add_argument("--agent-id", default="", help="Optional explicit agent id override for workspace bootstrap")
    parser.add_argument(
        "--group-id",
        required=require_group_id,
        default="" if not require_group_id else argparse.SUPPRESS,
        help="Optional Feishu group id; when provided, workspace bootstrap preview/execution is also enabled",
    )
    parser.add_argument(
        "--repo-root",
        required=require_repo_root,
        default="" if not require_repo_root else argparse.SUPPRESS,
    )
    parser.add_argument("--workspace-root", default="")
    parser.add_argument("--openclaw-config", default="")
    parser.add_argument("--channel", default="feishu")
    parser.add_argument("--tasklist-guid", default="", help="Bind an existing Feishu tasklist by GUID when name matches are ambiguous")
    parser.add_argument("--agent", default="")
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument("--thinking", default="")
    parser.add_argument("--session-key", default="")
    parser.add_argument("--skip-bootstrap-task", action="store_true", default=False)
    parser.add_argument("--skip-auto-run", action="store_true", default=False)
    parser.add_argument("--write-config", action="store_true", default=False)
    parser.add_argument("--doc-folder-token", default="", help="Bind an existing Feishu docs folder by token when name matches are ambiguous")
    parser.add_argument("--task-backend", default="", choices=["", "feishu", "local"])
    parser.add_argument("--doc-backend", default="", choices=["", "feishu", "repo"])
    parser.add_argument("--task-prefix", default="T")
    parser.add_argument("--default-worker", default="codex")
    parser.add_argument("--reviewer-worker", default="reviewer")
    parser.add_argument("--skill", action="append", default=[])
    parser.add_argument("--allow-agent", action="append", default=[])
    parser.add_argument("--model-primary", default="")
    parser.add_argument("--no-auth-bundle", action="store_true", default=False)
    parser.add_argument("--no-main-review-source", action="store_true", default=False)
    parser.add_argument("--no-main-digest-source", action="store_true", default=False)
    parser.add_argument("--force", action="store_true", default=False)
    parser.add_argument("--replace-binding", action="store_true", default=False)
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--tasklist-name", default="", help=argparse.SUPPRESS)
    parser.add_argument("--doc-folder-name", default="", help=argparse.SUPPRESS)


def _add_init_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser], handlers: dict[str, Any]) -> None:
    init = sub.add_parser(
        "init",
        help="Bind or create PM resources for a project",
        description=(
            "Initialize PM resources for a repo. By default only --project-name is needed; "
            "tasklist/doc names default to that same project name. If same-name resources are ambiguous, "
            "provide --tasklist-guid or --doc-folder-token explicitly."
        ),
    )
    _add_init_shared_arguments(
        init,
        require_project_name=False,
        require_group_id=False,
        require_repo_root=False,
    )
    init.set_defaults(func=handlers["init"])

    workspace_init = sub.add_parser(
        "workspace-init",
        help="Deprecated alias of init",
        description="Deprecated alias of `init`. Prefer `init`; tasklist/doc names default to --project-name and ambiguity should be resolved via guid/token.",
    )
    _add_init_shared_arguments(
        workspace_init,
        require_project_name=True,
        require_group_id=True,
        require_repo_root=True,
    )
    workspace_init.set_defaults(func=handlers["init"], _deprecated_command="workspace-init")


def _add_gsd_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser], handlers: dict[str, Any]) -> None:
    sync_gsd_docs = sub.add_parser("sync-gsd-docs")
    sync_gsd_docs.add_argument("--repo-root", default="")
    sync_gsd_docs.add_argument(
        "--include",
        action="append",
        default=[],
        choices=["project", "requirements", "roadmap", "state"],
    )
    sync_gsd_docs.set_defaults(func=handlers["sync_gsd_docs"])

    sync_gsd_progress = sub.add_parser("sync-gsd-progress")
    sync_gsd_progress.add_argument("--repo-root", default="")
    sync_gsd_progress.add_argument("--phase", default="")
    sync_gsd_progress.add_argument("--task-id", default="")
    sync_gsd_progress.add_argument("--task-guid", default="")
    sync_gsd_progress.add_argument("--include-completed", action="store_true", default=False)
    sync_gsd_progress.add_argument("--no-state-append", action="store_true", default=False)
    sync_gsd_progress.set_defaults(func=handlers["sync_gsd_progress"])

    materialize_gsd_tasks = sub.add_parser("materialize-gsd-tasks")
    materialize_gsd_tasks.add_argument("--repo-root", default="")
    materialize_gsd_tasks.add_argument("--phase", default="")
    materialize_gsd_tasks.set_defaults(func=handlers["materialize_gsd_tasks"])

    route_gsd = sub.add_parser("route-gsd")
    route_gsd.add_argument("--repo-root", default="")
    route_gsd.add_argument("--phase", default="")
    route_gsd.set_defaults(func=handlers["route_gsd"])

    plan_phase = sub.add_parser("plan-phase")
    plan_phase.add_argument("--repo-root", default="")
    plan_phase.add_argument("--phase", default="")
    plan_phase.add_argument("--task-id", default="")
    plan_phase.add_argument("--task-guid", default="")
    plan_phase.add_argument("--include-completed", action="store_true", default=False)
    plan_phase.add_argument("--agent", default="")
    plan_phase.add_argument("--timeout", type=int, default=0)
    plan_phase.add_argument("--thinking", default="")
    plan_phase.add_argument("--prd", default="")
    plan_phase.add_argument("--research", action="store_true", default=False)
    plan_phase.add_argument("--skip-research", action="store_true", default=False)
    plan_phase.add_argument("--gaps", action="store_true", default=False)
    plan_phase.add_argument("--skip-verify", action="store_true", default=False)
    plan_phase.add_argument("--reviews", action="store_true", default=False)
    plan_phase.add_argument("--no-doc-sync", action="store_true", default=False)
    plan_phase.add_argument("--no-progress-sync", action="store_true", default=False)
    plan_phase.add_argument("--no-state-append", action="store_true", default=False)
    plan_phase.set_defaults(func=handlers["plan_phase"])


def _add_flow_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser], handlers: dict[str, Any]) -> None:
    context = sub.add_parser("context")
    context.add_argument("--task-id", default="")
    context.add_argument("--task-guid", default="")
    context.add_argument("--refresh", action="store_true", default=False)
    context.set_defaults(func=handlers["context"])

    nxt = sub.add_parser("next")
    nxt.add_argument("--refresh", action="store_true", default=False)
    nxt.set_defaults(func=handlers["next"])

    plan = sub.add_parser("plan")
    plan.add_argument("--task-id", default="")
    plan.add_argument("--task-guid", default="")
    plan.add_argument("--focus", default="")
    plan.set_defaults(func=handlers["plan"])

    refine = sub.add_parser("refine")
    refine.add_argument("--task-id", default="")
    refine.add_argument("--task-guid", default="")
    refine.add_argument("--focus", default="")
    refine.set_defaults(func=handlers["refine"])

    coder_context = sub.add_parser("coder-context")
    coder_context.add_argument("--task-id", default="")
    coder_context.add_argument("--task-guid", default="")
    coder_context.set_defaults(func=handlers["coder_context"])

    run = sub.add_parser("run")
    run.add_argument("--task-id", default="")
    run.add_argument("--task-guid", default="")
    run.add_argument("--backend", default="")
    run.add_argument("--agent", default="")
    run.add_argument("--timeout", type=int, default=0)
    run.add_argument("--thinking", default="")
    run.add_argument("--session-key", default="")
    run.set_defaults(func=handlers["run"])


def _add_task_ref_arguments(parser: argparse.ArgumentParser, *, include_completed: bool = False) -> None:
    parser.add_argument("--task-id", default="")
    parser.add_argument("--task-guid", default="")
    if include_completed:
        parser.add_argument("--include-completed", action="store_true", default=False)


def _add_task_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser], handlers: dict[str, Any]) -> None:
    create = sub.add_parser("create")
    create.add_argument("--summary", required=True)
    create.add_argument("--request", default="")
    create.add_argument("--repo-root", default="")
    create.add_argument("--kind", default="")
    create.add_argument("--tasklist-name", default="")
    create.add_argument("--force-new", action="store_true", default=False)
    create.set_defaults(func=handlers["create"])

    get = sub.add_parser("get")
    _add_task_ref_arguments(get, include_completed=True)
    get.set_defaults(func=handlers["get"])

    comment = sub.add_parser("comment")
    _add_task_ref_arguments(comment, include_completed=True)
    comment.add_argument("--content", required=True)
    comment.set_defaults(func=handlers["comment"])

    complete = sub.add_parser("complete")
    _add_task_ref_arguments(complete, include_completed=True)
    complete.add_argument("--content", default="")
    complete.add_argument("--content-file", default="")
    complete.add_argument("--file", action="append", default=[])
    complete.add_argument("--commit-url", default="")
    complete.add_argument("--skip-head-commit-url", action="store_true", default=False)
    complete.add_argument("--repo-root", default="")
    complete.set_defaults(func=handlers["complete"])

    update_description = sub.add_parser("update-description")
    _add_task_ref_arguments(update_description, include_completed=True)
    update_description.add_argument("--mode", choices=("replace", "append"), default="replace")
    update_description.add_argument("--separator", default="\n\n")
    update_description.add_argument("--content", default="")
    update_description.add_argument("--content-file", default="")
    update_description.set_defaults(func=handlers["update_description"])

    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=20)
    listing.add_argument("--asc", action="store_true", default=False)
    listing.add_argument("--include-completed", action="store_true", default=False)
    listing.set_defaults(func=handlers["list"])

    normalize_titles = sub.add_parser("normalize-titles")
    normalize_titles.add_argument("--include-completed", action="store_true", default=False)
    normalize_titles.set_defaults(func=handlers["normalize_titles"])

    search = sub.add_parser("search")
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--include-completed", action="store_true", default=False)
    search.set_defaults(func=handlers["search"])

    backfill_assignees = sub.add_parser("backfill-assignees")
    backfill_assignees.add_argument("--tasklist-guid", action="append", default=[])
    backfill_assignees.add_argument("--all-visible-tasklists", action="store_true", default=False)
    backfill_assignees.add_argument("--all-creators", action="store_true", default=False)
    backfill_assignees.add_argument("--open-only", action="store_true", default=False)
    backfill_assignees.add_argument("--limit", type=int, default=0)
    backfill_assignees.add_argument("--dry-run", action="store_true", default=False)
    backfill_assignees.set_defaults(func=handlers["backfill_assignees"])

    attachments = sub.add_parser("attachments")
    _add_task_ref_arguments(attachments, include_completed=True)
    attachments.add_argument("--download-dir", default="")
    attachments.set_defaults(func=handlers["attachments"])

    upload_attachments = sub.add_parser("upload-attachments")
    _add_task_ref_arguments(upload_attachments, include_completed=True)
    upload_attachments.add_argument("--file", action="append", default=[])
    upload_attachments.set_defaults(func=handlers["upload_attachments"])


def build_parser(*, handlers: dict[str, Any]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PM project orchestration utilities for project workspaces")
    parser.add_argument("--config", default="")
    sub = parser.add_subparsers(dest="command", required=True)
    _add_auth_commands(sub, handlers)
    _add_init_commands(sub, handlers)
    _add_gsd_commands(sub, handlers)
    _add_flow_commands(sub, handlers)
    _add_task_commands(sub, handlers)
    return parser
