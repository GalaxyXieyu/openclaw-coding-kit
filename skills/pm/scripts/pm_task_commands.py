from __future__ import annotations

import argparse
from typing import Any, Callable

from pm_command_support import CommandHandler, current_task_cfg, emit_json, task_summary_text
from pm_task_assignment import plan_task_assignee_backfill
from pm_task_members import normalize_task_members, resolve_default_task_members


def _emit(payload: dict[str, Any]) -> int:
    return emit_json(payload)


def _bind_handler(api: Any, handler: Callable[[Any, argparse.Namespace], int]) -> CommandHandler:
    def _wrapped(args: argparse.Namespace) -> int:
        return handler(api, args)

    return _wrapped


def _task_from_args(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    if args.task_guid:
        return api.get_task_record_by_guid(args.task_guid)
    return api.get_task_record(args.task_id, include_completed=args.include_completed)


def _task_with_guid(api: Any, args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    task = _task_from_args(api, args)
    guid = str(task.get("guid") or "").strip()
    if not guid:
        raise SystemExit(f"task missing guid: {args.task_id or args.task_guid}")
    return task, guid


def _cmd_create(api: Any, args: argparse.Namespace) -> int:
    if args.tasklist_name:
        api.ACTIVE_CONFIG.setdefault("task", {})
        if isinstance(api.ACTIVE_CONFIG.get("task"), dict):
            api.ACTIVE_CONFIG["task"]["tasklist_name"] = str(args.tasklist_name).strip()
        api.ACTIVE_CONFIG["tasklist_name"] = str(args.tasklist_name).strip()
    tasklist = api.ensure_tasklist(args.tasklist_name)
    summary = args.summary.strip()
    if not args.force_new:
        existing = api.find_existing_task_by_summary(summary, include_completed=True)
        if isinstance(existing, dict) and str(existing.get("guid") or "").strip():
            context = api.refresh_context_cache(task_guid=str(existing.get("guid") or ""))
            parsed = api.parse_task_summary(task_summary_text(existing)) or {}
            return _emit(
                {
                    "task_id": str((parsed or {}).get("task_id") or existing.get("normalized_task_id") or ""),
                    "task": existing,
                    "tasklist": tasklist,
                    "deduplicated": True,
                    "context_path": str(api.pm_file("current-context.json")),
                    "next_task": context.get("next_task"),
                }
            )
    task_id = api.next_task_id()
    title = f"[{task_id}] {summary}"
    description = api.build_description(task_id, summary, args.request or "", args.repo_root, args.kind)
    owner = tasklist.get("owner") if isinstance(tasklist.get("owner"), dict) else {}
    current_user_id = str(owner.get("id") or "").strip()
    task = api.create_task(
        summary=title,
        description=description,
        tasklists=[{"tasklist_guid": str(tasklist.get("guid") or "").strip()}],
        current_user_id=current_user_id,
    )
    context = api.refresh_context_cache(task_guid=str(task.get("guid") or ""))
    return _emit(
        {
            "task_id": task_id,
            "task": task,
            "tasklist": tasklist,
            "deduplicated": False,
            "context_path": str(api.pm_file("current-context.json")),
            "next_task": context.get("next_task"),
        }
    )


def _cmd_get(api: Any, args: argparse.Namespace) -> int:
    task = _task_from_args(api, args)
    guid = str(task.get("guid") or "").strip()
    comments = api.list_task_comments(guid, 20)
    parsed = api.parse_task_summary(task_summary_text(task))
    result = {
        "task_id": api.normalize_task_key(args.task_id) if args.task_id else str((parsed or {}).get("task_id") or ""),
        "summary": task.get("summary") or "",
        "normalized_summary": str((parsed or {}).get("normalized_summary") or task_summary_text(task)),
        "status": task.get("status") or "",
        "description": task.get("description") or "",
        "url": task.get("url") or "",
        "guid": task.get("guid") or "",
        "created_at": task.get("created_at") or "",
        "updated_at": task.get("updated_at") or "",
        "completed_at": task.get("completed_at") or "",
        "start": task.get("start") or {},
        "due": task.get("due") or {},
        "members": task.get("members") or [],
        "tasklists": task.get("tasklists") or [],
        "attachments": task.get("attachments") or [],
        "comments": comments,
    }
    return _emit(result)


def _cmd_comment(api: Any, args: argparse.Namespace) -> int:
    task, guid = _task_with_guid(api, args)
    auto_started = api.ensure_task_started(task)
    payload = api.create_task_comment(guid, args.content.strip())
    context = api.refresh_context_cache(task_guid=guid)
    return _emit(
        {
            "task_id": api.task_id_for_output(args.task_id),
            "task_guid": guid,
            "auto_started": bool(auto_started),
            "start_result": auto_started,
            "result": payload,
            "context_path": str(api.pm_file("current-context.json")),
            "next_task": context.get("next_task"),
        }
    )


def _cmd_complete(api: Any, args: argparse.Namespace) -> int:
    task, guid = _task_with_guid(api, args)
    content = api.resolve_optional_text_input(args.content, args.content_file)
    upload_result = api.upload_task_attachments(task, args.task_id, args.file)
    if upload_result.get("status") == "authorization_required":
        upload_result["pending_action"] = "complete"
        upload_result["content"] = content
        upload_result["commit_url"] = args.commit_url.strip() or ("" if args.skip_head_commit_url else api.current_head_commit_url(args.repo_root))
        return _emit(upload_result)

    auto_started = upload_result.get("start_result")
    if upload_result.get("status") == "skipped":
        auto_started = api.ensure_task_started(task)
    commit_url = args.commit_url.strip() or ("" if args.skip_head_commit_url else api.current_head_commit_url(args.repo_root))
    completion_comment = api.build_completion_comment(content, commit_url, int(upload_result.get("uploaded_count") or 0))
    comment_payload: dict[str, Any] | None = None
    if completion_comment:
        comment_payload = api.create_task_comment(guid, completion_comment)
    completed_at = api.now_iso()
    payload = api.patch_task(guid, api.build_completion_changes(task, completed_at=completed_at))
    context = api.refresh_context_cache()
    return _emit(
        {
            "task_id": api.task_id_for_output(args.task_id),
            "task_guid": guid,
            "auto_started": bool(auto_started),
            "start_result": auto_started,
            "completion_comment": completion_comment,
            "comment_result": comment_payload,
            "commit_url": commit_url,
            "upload_result": upload_result,
            "result": payload,
            "context_path": str(api.pm_file("current-context.json")),
            "next_task": context.get("next_task"),
        }
    )


def _cmd_update_description(api: Any, args: argparse.Namespace) -> int:
    task, guid = _task_with_guid(api, args)
    content = api.resolve_text_input(args.content, args.content_file)
    current = str(task.get("description") or "").strip()
    if args.mode == "replace":
        description = content
    else:
        separator = args.separator
        description = f"{current}{separator}{content}".strip() if current else content
    payload = api.patch_task(guid, {"description": description})
    context = api.refresh_context_cache(task_guid=guid)
    return _emit(
        {
            "task_id": api.normalize_task_key(args.task_id) if args.task_id else "",
            "task_guid": guid,
            "mode": args.mode,
            "description": description,
            "result": payload,
            "context_path": str(api.pm_file("current-context.json")),
            "next_task": context.get("next_task"),
        }
    )


def _cmd_list(api: Any, args: argparse.Namespace) -> int:
    rows = [item for item in api.task_pool(include_completed=args.include_completed) if api.extract_task_number(task_summary_text(item)) > 0]
    rows.sort(key=lambda item: api.extract_task_number(task_summary_text(item)), reverse=not args.asc)
    if args.limit:
        rows = rows[: args.limit]
    result = [
        {
            "task_id": str((api.parse_task_summary(task_summary_text(item)) or {}).get("task_id") or ""),
            "summary": item.get("summary") or "",
            "normalized_summary": str(item.get("normalized_summary") or item.get("summary") or ""),
            "status": item.get("status") or "",
            "guid": item.get("guid") or "",
            "url": item.get("url") or "",
            "created_at": item.get("created_at") or "",
            "updated_at": item.get("updated_at") or "",
        }
        for item in rows
    ]
    return _emit({"tasks": result})


def _cmd_normalize_titles(api: Any, args: argparse.Namespace) -> int:
    result = api.normalize_task_titles(include_completed=args.include_completed)
    api.refresh_context_cache()
    return _emit(result)


def _cmd_search(api: Any, args: argparse.Namespace) -> int:
    query = args.query.strip().lower()
    if not query:
        raise SystemExit("search query is required")
    matches: list[dict[str, Any]] = []
    for item in api.task_pool(include_completed=args.include_completed):
        summary = task_summary_text(item)
        parsed = api.parse_task_summary(summary)
        if not summary:
            continue
        if query in summary.lower():
            matches.append(
                {
                    "task_id": str((parsed or {}).get("task_id") or ""),
                    "summary": item.get("summary") or "",
                    "normalized_summary": str((parsed or {}).get("normalized_summary") or summary),
                    "guid": item.get("guid") or "",
                    "completed_at": item.get("completed_at") or "0",
                }
            )
            continue
        guid = str(item.get("guid") or "").strip()
        if not guid:
            continue
        task = api.get_task_record_by_guid(guid)
        description = str(task.get("description") or "")
        if query in description.lower():
            matches.append(
                {
                    "task_id": str((parsed or {}).get("task_id") or ""),
                    "summary": item.get("summary") or "",
                    "normalized_summary": str((parsed or {}).get("normalized_summary") or summary),
                    "guid": guid,
                    "completed_at": item.get("completed_at") or "0",
                    "description_excerpt": description[:240],
                }
            )
    matches.sort(
        key=lambda item: api.extract_task_number(
            str(item.get("normalized_summary") or item.get("summary") or "")
        ),
        reverse=True,
    )
    if args.limit:
        matches = matches[: args.limit]
    return _emit({"tasks": matches})


def _list_visible_tasklists(api: Any) -> list[dict[str, Any]]:
    page_token = ""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    while True:
        payload = api.run_bridge(
            "feishu_task_tasklist",
            "list",
            {"page_size": 100, **({"page_token": page_token} if page_token else {})},
        )
        details = api.details_of(payload)
        for item in details.get("tasklists") or []:
            if not isinstance(item, dict):
                continue
            guid = str(item.get("guid") or "").strip()
            if guid and guid not in seen:
                rows.append(item)
                seen.add(guid)
        page_token = str(details.get("page_token") or "").strip()
        if not details.get("has_more") or not page_token:
            break
    return rows


def _list_tasklist_rows(api: Any, tasklist_guid: str, *, completed: bool) -> list[dict[str, Any]]:
    page_token = ""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    while True:
        payload = api.run_bridge(
            "feishu_task_tasklist",
            "tasks",
            {
                "tasklist_guid": tasklist_guid,
                "completed": completed,
                "page_size": 100,
                **({"page_token": page_token} if page_token else {}),
            },
        )
        details = api.details_of(payload)
        for item in details.get("tasks") or []:
            if not isinstance(item, dict):
                continue
            guid = str(item.get("guid") or "").strip()
            if guid and guid not in seen:
                rows.append(item)
                seen.add(guid)
        page_token = str(details.get("page_token") or "").strip()
        if not details.get("has_more") or not page_token:
            break
    return rows


def _select_tasklists_for_backfill(api: Any, args: argparse.Namespace, *, default_tasklist: dict[str, Any]) -> list[dict[str, Any]]:
    explicit_tasklist_guids = [str(item or "").strip() for item in (args.tasklist_guid or []) if str(item or "").strip()]
    if args.all_visible_tasklists:
        return _list_visible_tasklists(api)
    if not explicit_tasklist_guids:
        return [default_tasklist]
    visible_index = {
        str(item.get("guid") or "").strip(): item
        for item in _list_visible_tasklists(api)
        if isinstance(item, dict) and str(item.get("guid") or "").strip()
    }
    return [visible_index.get(guid) or {"guid": guid, "name": guid} for guid in explicit_tasklist_guids]


def _resolve_current_user_id(
    api: Any,
    auth: dict[str, Any],
    *,
    tasklists_by_guid: dict[str, dict[str, Any]],
    default_tasklist: dict[str, Any],
) -> tuple[str, str]:
    auth_open_id = str(auth.get("open_id") or "").strip()
    if auth_open_id:
        return auth_open_id, "oauth"

    owner_ids = {
        str(((item.get("owner") or {}) if isinstance(item.get("owner"), dict) else {}).get("id") or "").strip()
        for item in tasklists_by_guid.values()
        if isinstance(item, dict)
    }
    owner_ids.discard("")
    if len(owner_ids) == 1:
        return next(iter(owner_ids)), "tasklist_owner"

    default_owner = str(
        (((default_tasklist.get("owner") or {}) if isinstance(default_tasklist.get("owner"), dict) else {}).get("id") or "")
    ).strip()
    if default_owner:
        return default_owner, "default_tasklist_owner"
    return "", ""


def _collect_backfill_candidates(
    api: Any,
    *,
    tasklists_by_guid: dict[str, dict[str, Any]],
    desired_members: list[dict[str, Any]],
    current_user_id: str,
    args: argparse.Namespace,
) -> tuple[set[str], dict[str, int], list[dict[str, Any]]]:
    scanned_task_guids: set[str] = set()
    skipped_by_reason: dict[str, int] = {}
    candidates: list[dict[str, Any]] = []

    for tasklist_guid, tasklist in tasklists_by_guid.items():
        task_rows = _list_tasklist_rows(api, tasklist_guid, completed=False)
        if not args.open_only:
            task_rows += _list_tasklist_rows(api, tasklist_guid, completed=True)
        for row in task_rows:
            guid = str(row.get("guid") or "").strip()
            if not guid or guid in scanned_task_guids:
                continue
            scanned_task_guids.add(guid)
            try:
                detail = api.get_task_record_by_guid(guid)
            except SystemExit:
                skipped_by_reason["detail_load_failed"] = skipped_by_reason.get("detail_load_failed", 0) + 1
                continue
            plan = plan_task_assignee_backfill(
                detail,
                desired_members,
                creator_only_user_id="" if args.all_creators else current_user_id,
            )
            if str(plan.get("action") or "") != "add_members":
                reason = str(plan.get("reason") or "skipped")
                skipped_by_reason[reason] = skipped_by_reason.get(reason, 0) + 1
                continue
            parsed = api.parse_task_summary(str(detail.get("summary") or "").strip()) or {}
            candidates.append(
                {
                    "tasklist_guid": tasklist_guid,
                    "tasklist_name": str(tasklist.get("name") or "").strip(),
                    "task_id": str(parsed.get("task_id") or ""),
                    "summary": str(detail.get("summary") or "").strip(),
                    "guid": guid,
                    "members_to_add": plan.get("members") or [],
                }
            )
            if args.limit and len(candidates) >= int(args.limit):
                break
        if args.limit and len(candidates) >= int(args.limit):
            break
    return scanned_task_guids, skipped_by_reason, candidates


def _build_backfill_preview(
    *,
    tasklists_by_guid: dict[str, dict[str, Any]],
    auth: dict[str, Any],
    current_user_id: str,
    current_user_source: str,
    desired_members: list[dict[str, Any]],
    scanned_task_guids: set[str],
    skipped_by_reason: dict[str, int],
    candidates: list[dict[str, Any]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    preview = {
        "status": "preview" if args.dry_run else "ready",
        "current_user_id": current_user_id,
        "current_user_source": current_user_source,
        "desired_members": desired_members,
        "creator_filter": "all" if args.all_creators else current_user_id,
        "open_only": bool(args.open_only),
        "assignment_auth_status": str(auth.get("status") or ""),
        "scanned_task_count": len(scanned_task_guids),
        "candidate_count": len(candidates),
        "skipped_by_reason": skipped_by_reason,
        "target_tasklists": [
            {
                "guid": guid,
                "name": str(tasklist.get("name") or "").strip(),
            }
            for guid, tasklist in tasklists_by_guid.items()
        ],
        "candidates": candidates,
    }
    if str(auth.get("status") or "") != "authorized":
        preview["assignment_auth"] = auth
    return preview


def _apply_backfill_candidates(api: Any, candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    applied: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for item in candidates:
        guid = str(item.get("guid") or "").strip()
        detail = api.get_task_record_by_guid(guid)
        try:
            result = api.add_task_members(detail, str(item.get("task_id") or ""), list(item.get("members_to_add") or []))
        except SystemExit as exc:
            failures.append(
                {
                    "task_id": str(item.get("task_id") or ""),
                    "guid": guid,
                    "summary": str(item.get("summary") or ""),
                    "error": str(exc),
                }
            )
            continue
        if str(result.get("status") or "") != "ok":
            failures.append(
                {
                    "task_id": str(item.get("task_id") or ""),
                    "guid": guid,
                    "summary": str(item.get("summary") or ""),
                    "result": result,
                }
            )
            continue
        verified_detail = api.get_task_record_by_guid(guid)
        verified_members = normalize_task_members(
            verified_detail.get("members") if isinstance(verified_detail.get("members"), list) else []
        )
        expected_members = normalize_task_members(list(item.get("members_to_add") or []))
        expected_pairs = {(str(member.get("id") or ""), str(member.get("role") or "")) for member in expected_members}
        verified_pairs = {(str(member.get("id") or ""), str(member.get("role") or "")) for member in verified_members}
        if not expected_pairs.issubset(verified_pairs):
            failures.append(
                {
                    "task_id": str(item.get("task_id") or ""),
                    "guid": guid,
                    "summary": str(item.get("summary") or ""),
                    "error": "member assignment not visible after update",
                    "result": result,
                    "verified_members": verified_members,
                }
            )
            continue
        applied.append(
            {
                "task_id": str(item.get("task_id") or ""),
                "guid": guid,
                "summary": str(item.get("summary") or ""),
                "members": result.get("members") or [],
                "backend": str(result.get("backend") or ""),
            }
        )
    return applied, failures


def _cmd_backfill_assignees(api: Any, args: argparse.Namespace) -> int:
    default_tasklist = api.ensure_tasklist()
    selected_tasklists = _select_tasklists_for_backfill(api, args, default_tasklist=default_tasklist)
    auth = api.task_assignment_auth_result()
    tasklists_by_guid = {
        str(item.get("guid") or "").strip(): item
        for item in selected_tasklists
        if isinstance(item, dict) and str(item.get("guid") or "").strip()
    }
    current_user_id, current_user_source = _resolve_current_user_id(
        api,
        auth,
        tasklists_by_guid=tasklists_by_guid,
        default_tasklist=default_tasklist,
    )
    if not args.all_creators and not current_user_id:
        return _emit(
            {
                "status": "cannot_resolve_current_user",
                "message": "unable to determine current user open_id for creator-only backfill",
                "assignment_auth": auth,
                "target_tasklists": [
                    {
                        "guid": guid,
                        "name": str(tasklist.get("name") or "").strip(),
                    }
                    for guid, tasklist in tasklists_by_guid.items()
                ],
            }
        )

    desired_members = resolve_default_task_members(
        task_config=current_task_cfg(api),
        current_user_id=current_user_id,
    )
    scanned_task_guids, skipped_by_reason, candidates = _collect_backfill_candidates(
        api,
        tasklists_by_guid=tasklists_by_guid,
        desired_members=desired_members,
        current_user_id=current_user_id,
        args=args,
    )
    preview = _build_backfill_preview(
        tasklists_by_guid=tasklists_by_guid,
        auth=auth,
        current_user_id=current_user_id,
        current_user_source=current_user_source,
        desired_members=desired_members,
        scanned_task_guids=scanned_task_guids,
        skipped_by_reason=skipped_by_reason,
        candidates=candidates,
        args=args,
    )
    if args.dry_run:
        return _emit(preview)

    applied, failures = _apply_backfill_candidates(api, candidates)
    return _emit(
        {
            **preview,
            "status": "ok" if not failures else ("partial" if applied else "failed"),
            "applied_count": len(applied),
            "failed_count": len(failures),
            "applied": applied,
            "failures": failures,
        }
    )


def _cmd_attachments(api: Any, args: argparse.Namespace) -> int:
    task = _task_from_args(api, args)
    result = api.list_task_attachments(
        task,
        args.task_id,
        args.download_dir,
        task_id_for_output_fn=api.task_id_for_output,
        attachment_auth_result_fn=api.attachment_auth_result,
        feishu_credentials=api.feishu_credentials,
        request_json=api.request_json,
    )
    return _emit(result)


def _cmd_upload_attachments(api: Any, args: argparse.Namespace) -> int:
    task = _task_from_args(api, args)
    result = api.upload_task_attachments(task, args.task_id, args.file)
    if str(result.get("status") or "") != "authorization_required":
        api.refresh_context_cache(task_guid=str(task.get("guid") or ""))
    return _emit(result)


def build_task_command_handlers(api: Any) -> dict[str, CommandHandler]:
    handlers = {
        "create": _cmd_create,
        "get": _cmd_get,
        "comment": _cmd_comment,
        "complete": _cmd_complete,
        "update_description": _cmd_update_description,
        "list": _cmd_list,
        "normalize_titles": _cmd_normalize_titles,
        "search": _cmd_search,
        "backfill_assignees": _cmd_backfill_assignees,
        "attachments": _cmd_attachments,
        "upload_attachments": _cmd_upload_attachments,
    }
    return {name: _bind_handler(api, handler) for name, handler in handlers.items()}
