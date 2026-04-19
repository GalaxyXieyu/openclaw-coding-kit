from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pm_attachments import attachment_auth_result as build_pm_attachment_auth_result
from pm_attachments import list_task_attachments as list_pm_task_attachments
from pm_attachments import task_id_for_output as format_pm_task_id_for_output
from pm_attachments import upload_task_attachments as upload_pm_task_attachments
from pm_bootstrap import bootstrap_task_template as build_bootstrap_task_template
from pm_bootstrap import ensure_bootstrap_task as create_bootstrap_task
from pm_config import ACTIVE_CONFIG
from pm_config import default_config
from pm_config import doc_config
from pm_config import task_prefix
from pm_config import tasklist_name
from pm_io import now_iso
from pm_io import now_text
from pm_local_backend import add_attachments as add_local_task_attachments
from pm_local_backend import create_comment as create_local_task_comment
from pm_local_backend import create_task as create_local_task
from pm_local_backend import ensure_tasklist as ensure_local_tasklist
from pm_local_backend import get_task_by_guid as get_local_task_by_guid
from pm_local_backend import inspect_tasklist as inspect_local_tasklist
from pm_local_backend import list_attachments as list_local_task_attachments
from pm_local_backend import list_comments as list_local_task_comments
from pm_local_backend import list_tasklist_tasks as list_local_tasklist_tasks
from pm_local_backend import patch_task as patch_local_task
from pm_scan import build_bootstrap_info
from pm_scan import detect_project_mode
from pm_task_assignment import add_task_members as add_pm_task_members
from pm_task_assignment import task_assignment_auth_result as build_pm_task_assignment_auth_result
from pm_task_members import normalize_task_members
from pm_task_members import resolve_default_task_members
from pm_tasks import build_completion_comment as build_pm_completion_comment
from pm_tasks import build_description as build_pm_task_description
from pm_tasks import build_normalized_summary_from_text as build_pm_normalized_summary
from pm_tasks import current_head_commit_url as resolve_pm_head_commit_url
from pm_tasks import detail_for_row as load_pm_task_detail_for_row
from pm_tasks import ensure_description_has_task_id as ensure_pm_description_has_task_id
from pm_tasks import ensure_task_started as ensure_pm_task_started
from pm_tasks import ensure_tasklist as ensure_pm_tasklist
from pm_tasks import extract_task_number as extract_pm_task_number
from pm_tasks import find_existing_task_by_summary as find_pm_existing_task_by_summary
from pm_tasks import find_task_summary as find_pm_task_summary
from pm_tasks import get_task_record as get_pm_task_record
from pm_tasks import get_task_record_by_guid as get_pm_task_record_by_guid
from pm_tasks import inspect_tasklist as inspect_pm_tasklist
from pm_tasks import list_tasklist_tasks as list_pm_tasklist_tasks
from pm_tasks import maybe_normalize_task_summary as maybe_normalize_pm_task_summary
from pm_tasks import next_task_id as next_pm_task_id
from pm_tasks import normalize_task_key as normalize_pm_task_key
from pm_tasks import normalize_task_titles as normalize_pm_task_titles
from pm_tasks import parse_task_id_from_description as parse_pm_task_id_from_description
from pm_tasks import parse_task_summary as parse_pm_task_summary
from pm_tasks import task_pool as build_task_pool

from pm_api_support import build_auth_link
from pm_api_support import details_of
from pm_api_support import ensure_attachment_token
from pm_api_support import feishu_credentials
from pm_api_support import load_openclaw_gateway_user_token
from pm_api_support import request_json
from pm_api_support import request_user_oauth_link
from pm_api_support import run_bridge
from pm_api_support import sanitize_feishu_markdown
from pm_api_support import task_backend_name


def ensure_task_started(task: dict[str, Any]) -> Optional[dict[str, Any]]:
    if task_backend_name() == "local":
        if str(task.get("guid") or "").strip() and not str(((task.get("start") or {}).get("timestamp") or "")).strip():
            return patch_local_task(str(task.get("guid") or "").strip(), {"start": {"timestamp": now_iso(), "is_all_day": False}})
        return None
    return ensure_pm_task_started(task, run_bridge=run_bridge, now_iso=now_iso)


def task_id_for_output(task_id: str) -> str:
    return format_pm_task_id_for_output(task_id, normalize_task_key_fn=normalize_task_key)


def parse_task_summary(summary: str) -> Optional[dict[str, Any]]:
    return parse_pm_task_summary(summary, task_prefix=task_prefix)


def parse_task_id_from_description(description: str) -> str:
    return parse_pm_task_id_from_description(description, task_prefix=task_prefix)


def build_normalized_summary_from_text(task_id: str, summary: str) -> str:
    return build_pm_normalized_summary(task_id, summary, parse_task_summary=parse_task_summary)


def ensure_description_has_task_id(description: str, task_id: str) -> str:
    return ensure_pm_description_has_task_id(description, task_id, parse_task_id_from_description=parse_task_id_from_description)


def maybe_normalize_task_summary(
    item: dict[str, Any],
    *,
    fetch_description_if_needed: bool = True,
    allow_patch: bool = False,
) -> dict[str, Any]:
    if task_backend_name() == "local":
        summary = str(item.get("summary") or "").strip()
        parsed = parse_task_summary(summary)
        if parsed:
            item["normalized_task_id"] = str(parsed.get("task_id") or "").strip()
            item["normalized_summary"] = str(parsed.get("normalized_summary") or "").strip()
        else:
            task_id = parse_task_id_from_description(str(item.get("description") or ""))
            if task_id:
                item["normalized_task_id"] = task_id
                item["normalized_summary"] = build_normalized_summary_from_text(task_id, summary)
        return item
    return maybe_normalize_pm_task_summary(
        item,
        parse_task_summary=parse_task_summary,
        parse_task_id_from_description=parse_task_id_from_description,
        build_normalized_summary_from_text=build_normalized_summary_from_text,
        run_bridge=run_bridge,
        details_of=details_of,
        fetch_description_if_needed=fetch_description_if_needed,
        allow_patch=allow_patch,
    )


def detail_for_row(row: dict[str, Any]) -> dict[str, Any]:
    if task_backend_name() == "local":
        guid = str(row.get("guid") or "").strip()
        return get_local_task_by_guid(guid) if guid else {}
    return load_pm_task_detail_for_row(row, run_bridge=run_bridge, details_of=details_of)


def normalize_task_titles(*, include_completed: bool) -> dict[str, Any]:
    if task_backend_name() == "local":
        rows = task_pool(include_completed=include_completed, fetch_description_if_needed=False)
        changed: list[dict[str, Any]] = []
        untouched: list[dict[str, Any]] = []
        for item in rows:
            guid = str(item.get("guid") or "").strip()
            summary = str(item.get("summary") or "").strip()
            description = str(item.get("description") or "").strip()
            parsed = parse_task_summary(summary)
            task_id = str((parsed or {}).get("task_id") or parse_task_id_from_description(description) or "").strip()
            if not task_id:
                untouched.append({"guid": guid, "summary": summary})
                continue
            normalized_summary = build_normalized_summary_from_text(task_id, summary)
            normalized_description = ensure_description_has_task_id(description, task_id)
            if normalized_summary != summary or normalized_description != description:
                patch_task(guid, {"summary": normalized_summary, "description": normalized_description})
                changed.append({"guid": guid, "task_id": task_id, "summary_after": normalized_summary})
            else:
                untouched.append({"guid": guid, "task_id": task_id, "summary": normalized_summary})
        return {
            "tasklist_guid": str(ensure_tasklist().get("guid") or ""),
            "scanned_count": len(rows),
            "changed_count": len(changed),
            "changed": changed,
            "untouched_count": len(untouched),
            "untouched": untouched,
        }
    return normalize_pm_task_titles(
        include_completed=include_completed,
        task_prefix=task_prefix,
        ensure_tasklist_fn=ensure_tasklist,
        list_tasklist_tasks_fn=list_tasklist_tasks,
        parse_task_summary=parse_task_summary,
        parse_task_id_from_description=parse_task_id_from_description,
        build_normalized_summary_from_text=build_normalized_summary_from_text,
        ensure_description_has_task_id=ensure_description_has_task_id,
        detail_for_row_fn=detail_for_row,
        run_bridge=run_bridge,
    )


def create_task(
    *,
    summary: str,
    description: str,
    tasklists: list[dict[str, Any]] | None = None,
    current_user_id: str = "",
    members: list[dict[str, Any]] | None = None,
    gsd_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    task_cfg = ACTIVE_CONFIG.get("task")
    resolved_members = normalize_task_members(members) or resolve_default_task_members(
        task_config=task_cfg if isinstance(task_cfg, dict) else {},
        current_user_id=current_user_id,
    )
    if task_backend_name() == "local":
        return create_local_task(
            summary=summary,
            description=description,
            tasklists=tasklists,
            current_user_id=current_user_id,
            members=resolved_members,
            gsd_contract=gsd_contract,
        )
    create_args: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "tasklists": [item for item in (tasklists or []) if isinstance(item, dict)],
    }
    if current_user_id:
        create_args["current_user_id"] = current_user_id
    if resolved_members:
        create_args["members"] = resolved_members
    payload = run_bridge("feishu_task_task", "create", create_args)
    task = details_of(payload).get("task")
    if not isinstance(task, dict):
        raise SystemExit("failed to create task")
    return task


def patch_task(task_guid: str, changes: dict[str, Any]) -> dict[str, Any]:
    cleaned = {str(key): value for key, value in (changes or {}).items() if str(key).strip()}
    if task_backend_name() == "local":
        return patch_local_task(task_guid, cleaned)
    payload = run_bridge("feishu_task_task", "patch", {"task_guid": task_guid, **cleaned})
    task = details_of(payload).get("task")
    if isinstance(task, dict):
        return task
    if cleaned:
        return get_task_record_by_guid(task_guid)
    return {}


def completion_due_mode() -> str:
    task_cfg = ACTIVE_CONFIG.get("task")
    if isinstance(task_cfg, dict):
        mode = str(task_cfg.get("completion_due_mode") or "").strip().lower()
        if mode in {"never", "if_missing", "always"}:
            return mode
        legacy_toggle = task_cfg.get("sync_completed_at_to_due")
        if isinstance(legacy_toggle, bool):
            return "if_missing" if legacy_toggle else "never"
    return "never"


def task_has_due(task: dict[str, Any]) -> bool:
    due = task.get("due")
    return isinstance(due, dict) and str(due.get("timestamp") or "").strip() not in {"", "0"}


def build_completion_changes(task: dict[str, Any], *, completed_at: str) -> dict[str, Any]:
    timestamp = str(completed_at or "").strip()
    if not timestamp:
        return {}
    changes: dict[str, Any] = {"completed_at": timestamp}
    mode = completion_due_mode()
    should_sync_due = mode == "always" or (mode == "if_missing" and not task_has_due(task))
    if should_sync_due:
        changes["due"] = {
            "timestamp": timestamp,
            "is_all_day": False,
        }
    return changes


def list_task_comments(task_guid: str, limit: int = 20) -> list[dict[str, Any]]:
    if not str(task_guid or "").strip():
        return []
    if task_backend_name() == "local":
        return list_local_task_comments(task_guid, page_size=limit)
    comments_payload = run_bridge("feishu_task_comment", "list", {"resource_id": task_guid, "direction": "desc", "page_size": limit})
    return details_of(comments_payload).get("comments") or []


def create_task_comment(task_guid: str, content: str) -> dict[str, Any] | None:
    cleaned = sanitize_feishu_markdown(content)
    if not task_guid.strip() or not cleaned.strip():
        return None
    if task_backend_name() == "local":
        return create_local_task_comment(task_guid, cleaned)
    payload = run_bridge("feishu_task_comment", "create", {"task_guid": task_guid, "content": cleaned})
    return details_of(payload)


def ensure_tasklist(name: str | None = None) -> dict[str, Any]:
    configured_guid = ""
    task_cfg = ACTIVE_CONFIG.get("task")
    if isinstance(task_cfg, dict):
        configured_guid = str(task_cfg.get("tasklist_guid") or "").strip()
    resolved_name = name or tasklist_name()
    if task_backend_name() == "local":
        return ensure_local_tasklist(name=str(resolved_name or "").strip(), configured_guid=configured_guid)
    return ensure_pm_tasklist(
        run_bridge,
        details_of,
        tasklist_name=tasklist_name,
        name=resolved_name,
        configured_guid=configured_guid,
    )


def inspect_tasklist(name: str | None = None, *, configured_guid: str = "") -> dict[str, Any]:
    guid_hint = configured_guid
    if not guid_hint:
        task_cfg = ACTIVE_CONFIG.get("task")
        if isinstance(task_cfg, dict):
            guid_hint = str(task_cfg.get("tasklist_guid") or "").strip()
    resolved_name = name or tasklist_name()
    if task_backend_name() == "local":
        return inspect_local_tasklist(name=str(resolved_name or "").strip(), configured_guid=guid_hint)
    return inspect_pm_tasklist(
        run_bridge,
        details_of,
        tasklist_name=tasklist_name,
        name=resolved_name,
        configured_guid=guid_hint,
    )


def list_tasklist_tasks(tasklist_guid: str, *, completed: bool) -> list[dict[str, Any]]:
    if task_backend_name() == "local":
        return list_local_tasklist_tasks(tasklist_guid, completed=completed)
    return list_pm_tasklist_tasks(run_bridge, details_of, tasklist_guid, completed=completed)


def task_pool(
    *,
    include_completed: bool,
    normalize_titles_before_list: bool = False,
    fetch_description_if_needed: bool = True,
) -> list[dict[str, Any]]:
    if task_backend_name() == "local":
        if normalize_titles_before_list:
            normalize_task_titles(include_completed=include_completed)
        tasklist = ensure_tasklist()
        tasklist_guid = str(tasklist.get("guid") or "").strip()
        rows = list_tasklist_tasks(tasklist_guid, completed=False)
        if include_completed:
            rows += list_tasklist_tasks(tasklist_guid, completed=True)
        dedup: dict[str, dict[str, Any]] = {}
        for item in rows:
            guid = str(item.get("guid") or "").strip()
            if guid:
                maybe_normalize_task_summary(item, fetch_description_if_needed=False, allow_patch=False)
                dedup[guid] = item
        return list(dedup.values())
    return build_task_pool(
        include_completed=include_completed,
        normalize_task_titles=normalize_task_titles,
        ensure_tasklist_fn=ensure_tasklist,
        list_tasklist_tasks_fn=list_tasklist_tasks,
        maybe_normalize_task_summary=maybe_normalize_task_summary,
        normalize_titles_before_list=normalize_titles_before_list,
        fetch_description_if_needed=fetch_description_if_needed,
    )


def extract_task_number(summary: str) -> int:
    return extract_pm_task_number(summary, parse_task_summary=parse_task_summary)


def next_task_id() -> str:
    return next_pm_task_id(task_prefix=task_prefix, task_pool_fn=task_pool, extract_task_number_fn=extract_task_number)


def normalize_task_key(task_key: str) -> str:
    return normalize_pm_task_key(task_key, task_prefix=task_prefix)


def find_task_summary(task_key: str, *, include_completed: bool) -> dict[str, Any]:
    if task_backend_name() == "local":
        normalized = normalize_task_key(task_key)
        for item in task_pool(include_completed=include_completed):
            parsed = parse_task_summary(str(item.get("normalized_summary") or item.get("summary") or "")) or {}
            normalized_task_id = str(item.get("normalized_task_id") or parsed.get("task_id") or "")
            if normalized_task_id == normalized:
                return item
        state_hint = "including completed tasks" if include_completed else "among unfinished tasks"
        raise SystemExit(f"task not found in local backend {state_hint}: {normalized}")
    return find_pm_task_summary(
        task_key,
        include_completed=include_completed,
        normalize_task_key_fn=normalize_task_key,
        task_pool_fn=task_pool,
        parse_task_summary=parse_task_summary,
    )


def get_task_record(task_key: str, *, include_completed: bool) -> dict[str, Any]:
    if task_backend_name() == "local":
        summary_item = find_task_summary(task_key, include_completed=include_completed)
        guid = str(summary_item.get("guid") or "").strip()
        if not guid:
            raise SystemExit(f"task missing guid: {task_key}")
        return get_task_record_by_guid(guid)
    return get_pm_task_record(
        task_key,
        include_completed=include_completed,
        find_task_summary_fn=find_task_summary,
        run_bridge=run_bridge,
        details_of=details_of,
    )


def get_task_record_by_guid(task_guid: str) -> dict[str, Any]:
    if task_backend_name() == "local":
        task = get_local_task_by_guid(task_guid)
        maybe_normalize_task_summary(task, fetch_description_if_needed=False, allow_patch=False)
        return task
    return get_pm_task_record_by_guid(
        task_guid,
        run_bridge=run_bridge,
        details_of=details_of,
        maybe_normalize_task_summary=maybe_normalize_task_summary,
    )


def find_existing_task_by_summary(summary: str, *, include_completed: bool = True) -> dict[str, Any] | None:
    return find_pm_existing_task_by_summary(
        summary,
        include_completed=include_completed,
        task_pool_fn=task_pool,
        parse_task_summary=parse_task_summary,
    )


def build_description(task_id: str, summary: str, request: str, repo_root: str, kind: str) -> str:
    return build_pm_task_description(
        task_id,
        summary,
        request,
        repo_root,
        kind,
        now_text=now_text,
        description_requirements=lambda: ACTIVE_CONFIG.get("description_requirements") or default_config()["description_requirements"],
    )


def bootstrap_task_template(root: Path) -> dict[str, str]:
    return build_bootstrap_task_template(
        root,
        build_bootstrap_info=build_bootstrap_info,
        doc_config=doc_config,
        detect_project_mode=detect_project_mode,
    )


def ensure_bootstrap_task(root: Path) -> dict[str, Any]:
    if task_backend_name() == "local":
        existing = [item for item in task_pool(include_completed=True) if extract_task_number(str(item.get("summary") or "")) > 0]
        if existing:
            existing.sort(key=lambda item: extract_task_number(str(item.get("summary") or "")))
            first = existing[0]
            parsed = parse_task_summary(str(first.get("summary") or "")) or {}
            return {
                "created": False,
                "reason": "tasks_already_exist",
                "task": {
                    "task_id": str(parsed.get("task_id") or ""),
                    "summary": str(parsed.get("normalized_summary") or first.get("summary") or ""),
                    "guid": str(first.get("guid") or ""),
                    "url": str(first.get("url") or ""),
                },
            }
        tasklist = ensure_tasklist()
        template = bootstrap_task_template(root)
        task_id = next_task_id()
        title = f"[{task_id}] {template['summary']}"
        description = build_description(task_id, template["summary"], template["request"], str(root), "bootstrap")
        task = create_task(
            summary=title,
            description=description,
            tasklists=[{"tasklist_guid": str(tasklist.get("guid") or "").strip()}],
        )
        return {
            "created": True,
            "reason": "created",
            "task": {
                "task_id": task_id,
                "summary": str(task.get("summary") or title),
                "guid": str(task.get("guid") or ""),
                "url": str(task.get("url") or "").strip(),
                "description": str(task.get("description") or description),
            },
            "result": task,
        }
    return create_bootstrap_task(
        root,
        task_pool=lambda **kwargs: task_pool(normalize_titles_before_list=True, **kwargs),
        extract_task_number=extract_task_number,
        parse_task_summary=parse_task_summary,
        ensure_tasklist=ensure_tasklist,
        next_task_id=next_task_id,
        build_description=build_description,
        run_bridge=run_bridge,
        details_of=details_of,
        get_task_record_by_guid=get_task_record_by_guid,
        build_bootstrap_info=build_bootstrap_info,
        doc_config=doc_config,
        detect_project_mode=detect_project_mode,
    )


def resolve_text_input(content: str, content_file: str) -> str:
    inline = (content or "").strip()
    file_path = (content_file or "").strip()
    if inline and file_path:
        raise SystemExit("use either --content or --content-file, not both")
    if file_path:
        path = Path(file_path).expanduser()
        if not path.exists():
            raise SystemExit(f"content file not found: {path}")
        inline = path.read_text(encoding="utf-8").strip()
    if not inline:
        raise SystemExit("content is required")
    return inline


def resolve_optional_text_input(content: str, content_file: str) -> str:
    inline = (content or "").strip()
    file_path = (content_file or "").strip()
    if inline and file_path:
        raise SystemExit("use either --content or --content-file, not both")
    if file_path:
        path = Path(file_path).expanduser()
        if not path.exists():
            raise SystemExit(f"content file not found: {path}")
        inline = path.read_text(encoding="utf-8").strip()
    return inline


def attachment_auth_result(task: dict[str, Any], task_id: str) -> dict[str, Any]:
    return build_pm_attachment_auth_result(
        task,
        task_id,
        task_id_for_output_fn=task_id_for_output,
        ensure_attachment_token=lambda: ensure_attachment_token(),
        build_auth_link=lambda **kwargs: build_auth_link(**kwargs),
        request_user_oauth_link=lambda **kwargs: request_user_oauth_link(**kwargs),
    )


def task_assignment_auth_result() -> dict[str, Any]:
    return build_pm_task_assignment_auth_result(
        ensure_user_token=lambda scopes: ensure_attachment_token(scopes),
        build_auth_link=lambda **kwargs: build_auth_link(**kwargs),
        request_user_oauth_link=lambda **kwargs: request_user_oauth_link(**kwargs),
    )


def add_task_members(task: dict[str, Any], task_id: str, members: list[dict[str, Any]]) -> dict[str, Any]:
    normalized_new_members = normalize_task_members(members)
    task_guid = str(task.get("guid") or "").strip()
    bridge_error = ""
    if task_guid and normalized_new_members:
        current_members = normalize_task_members(task.get("members") if isinstance(task.get("members"), list) else [])
        merged_members = normalize_task_members(current_members + normalized_new_members)
        try:
            updated_task = patch_task(task_guid, {"members": merged_members})
            updated_members = normalize_task_members(updated_task.get("members") if isinstance(updated_task.get("members"), list) else [])
            expected_pairs = {(str(item.get("id") or ""), str(item.get("role") or "")) for item in normalized_new_members}
            updated_pairs = {(str(item.get("id") or ""), str(item.get("role") or "")) for item in updated_members}
            if expected_pairs and not expected_pairs.issubset(updated_pairs):
                raise SystemExit("bridge patch did not persist task members")
            return {
                "status": "ok",
                "task_id": task_id_for_output(task_id),
                "task_guid": task_guid,
                "members": normalized_new_members,
                "patched_members": merged_members,
                "task": updated_task if isinstance(updated_task, dict) else {},
                "backend": "bridge",
            }
        except SystemExit as exc:
            bridge_error = str(exc)

    gateway_user_id = ""
    for item in normalized_new_members:
        if str(item.get("role") or "") == "assignee":
            gateway_user_id = str(item.get("id") or "").strip()
            if gateway_user_id:
                break
    gateway_auth = load_openclaw_gateway_user_token(gateway_user_id)
    result = add_pm_task_members(
        task,
        task_id,
        normalized_new_members,
        task_id_for_output_fn=task_id_for_output,
        auth_result_fn=(lambda: gateway_auth) if gateway_auth else task_assignment_auth_result,
        feishu_credentials=feishu_credentials,
        request_json=request_json,
    )
    if bridge_error:
        result["bridge_error"] = bridge_error
        result["backend"] = "gateway_keychain_fallback" if gateway_auth else "direct_api_fallback"
    return result


def upload_task_attachments(task: dict[str, Any], task_id: str, file_args: list[str]) -> dict[str, Any]:
    if task_backend_name() == "local":
        auto_started = ensure_task_started(task)
        result = add_local_task_attachments(str(task.get("guid") or "").strip(), [str(item or "").strip() for item in (file_args or []) if str(item or "").strip()])
        result["backend"] = "local"
        result["auto_started"] = bool(auto_started)
        result["start_result"] = auto_started
        return result
    return upload_pm_task_attachments(
        task,
        task_id,
        file_args,
        task_id_for_output_fn=task_id_for_output,
        attachment_auth_result_fn=attachment_auth_result,
        ensure_task_started_fn=ensure_task_started,
        feishu_credentials=feishu_credentials,
        request_json=request_json,
    )


def current_head_commit_url(root: str) -> str:
    return resolve_pm_head_commit_url(root)


def build_completion_comment(content: str, commit_url: str, uploaded_count: int) -> str:
    return build_pm_completion_comment(content, commit_url, uploaded_count)


def list_task_attachments(
    task: dict[str, Any],
    task_id: str,
    download_dir: str,
    *,
    task_id_for_output_fn: Any,
    attachment_auth_result_fn: Any,
    feishu_credentials: Any,
    request_json: Any,
) -> dict[str, Any]:
    if task_backend_name() == "local":
        result = list_local_task_attachments(str(task.get("guid") or "").strip(), download_dir=download_dir)
        result["task_id"] = task_id_for_output_fn(task_id)
        result["backend"] = "local"
        return result
    return list_pm_task_attachments(
        task,
        task_id,
        download_dir,
        task_id_for_output_fn=task_id_for_output_fn,
        attachment_auth_result_fn=attachment_auth_result_fn,
        feishu_credentials=feishu_credentials,
        request_json=request_json,
    )
