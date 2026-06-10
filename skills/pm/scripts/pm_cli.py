from __future__ import annotations

import argparse
from typing import Any


def build_parser(*, handlers: dict[str, Any]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PM project orchestration utilities for project workspaces")
    parser.add_argument("--config", default="")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser(
        "init",
        help="Bind or create PM resources for a project",
        description=(
            "Initialize PM resources for a repo. By default only --project-name is needed; "
            "tasklist/doc names default to that same project name. If same-name resources are ambiguous, "
            "provide --tasklist-guid or --doc-folder-token explicitly."
        ),
    )
    init.add_argument("--repo-root", default="")
    init.add_argument("--project-name", default="", help="Primary human-readable project name; defaults to repo name")
    init.add_argument("--tasklist-guid", default="", help="Bind an existing Feishu tasklist by GUID when name matches are ambiguous")
    init.add_argument("--write-config", action="store_true", default=False)
    init.add_argument("--english-name", default="", help="Optional ASCII name used for repo-local PM contract generation")
    init.add_argument("--doc-folder-token", default="", help="Bind an existing Feishu docs folder by token when name matches are ambiguous")
    init.add_argument("--task-backend", default="", choices=["", "feishu", "local"])
    init.add_argument("--doc-backend", default="", choices=["", "feishu", "repo"])
    init.add_argument("--task-prefix", default="T")
    init.add_argument("--default-worker", default="codex")
    init.add_argument("--reviewer-worker", default="reviewer")
    init.add_argument("--no-main-review-source", action="store_true", default=False)
    init.add_argument("--no-main-digest-source", action="store_true", default=False)
    init.add_argument("--dry-run", action="store_true", default=False)
    init.add_argument("--tasklist-name", default="", help=argparse.SUPPRESS)
    init.add_argument("--doc-folder-name", default="", help=argparse.SUPPRESS)
    init.set_defaults(func=handlers["init"])

    lark = sub.add_parser("lark", help="Initialize or inspect official lark-cli auth")
    lark.add_argument("action", choices=("status", "doctor", "login"), nargs="?", default="status")
    lark.add_argument("--exec", action="store_true", default=False, help="Run interactive lark-cli auth login for the login action")
    lark.set_defaults(func=handlers["lark"])

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

    create = sub.add_parser("create")
    create.add_argument("--summary", required=True)
    create.add_argument("--request", default="")
    create.add_argument("--repo-root", default="")
    create.add_argument("--kind", default="")
    create.add_argument("--tasklist-name", default="")
    create.add_argument("--force-new", action="store_true", default=False)
    create.set_defaults(func=handlers["create"])

    get = sub.add_parser("get")
    get.add_argument("--task-id", default="")
    get.add_argument("--task-guid", default="")
    get.add_argument("--include-completed", action="store_true", default=False)
    get.set_defaults(func=handlers["get"])

    comment = sub.add_parser("comment")
    comment.add_argument("--task-id", default="")
    comment.add_argument("--task-guid", default="")
    comment.add_argument("--include-completed", action="store_true", default=False)
    comment.add_argument("--content", required=True)
    comment.set_defaults(func=handlers["comment"])

    complete = sub.add_parser("complete")
    complete.add_argument("--task-id", default="")
    complete.add_argument("--task-guid", default="")
    complete.add_argument("--include-completed", action="store_true", default=False)
    complete.add_argument("--content", default="")
    complete.add_argument("--content-file", default="")
    complete.add_argument("--file", action="append", default=[])
    complete.add_argument("--commit-url", default="")
    complete.add_argument("--skip-head-commit-url", action="store_true", default=False)
    complete.add_argument("--repo-root", default="")
    complete.set_defaults(func=handlers["complete"])

    update_description = sub.add_parser("update-description")
    update_description.add_argument("--task-id", default="")
    update_description.add_argument("--task-guid", default="")
    update_description.add_argument("--include-completed", action="store_true", default=False)
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
    attachments.add_argument("--task-id", default="")
    attachments.add_argument("--task-guid", default="")
    attachments.add_argument("--include-completed", action="store_true", default=False)
    attachments.add_argument("--download-dir", default="")
    attachments.set_defaults(func=handlers["attachments"])

    upload_attachments = sub.add_parser("upload-attachments")
    upload_attachments.add_argument("--task-id", default="")
    upload_attachments.add_argument("--task-guid", default="")
    upload_attachments.add_argument("--include-completed", action="store_true", default=False)
    upload_attachments.add_argument("--file", action="append", default=[])
    upload_attachments.set_defaults(func=handlers["upload_attachments"])
    return parser
