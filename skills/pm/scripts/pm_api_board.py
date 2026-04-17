from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from pm_config import ACTIVE_CONFIG
from pm_config import pm_file
from pm_config import project_name
from pm_config import project_root_path
from pm_io import load_json_file
from pm_io import now_iso
from pm_api_tasks import ensure_tasklist
from pm_api_tasks import get_task_record
from pm_api_tasks import get_task_record_by_guid
from pm_api_tasks import list_task_comments
from pm_api_tasks import list_tasklist_tasks
from pm_api_tasks import list_visible_tasklists
from pm_api_tasks import parse_task_id_from_description
from pm_api_tasks import parse_task_summary
from pm_api_tasks import task_pool


PM_EVENT_BLOCK_RE = re.compile(r"\[\[pm_event\]\]\s*(?P<body>.*?)\s*\[\[/pm_event\]\]", flags=re.IGNORECASE | re.DOTALL)
SUMMARY_PREFIX_RE = re.compile(r"^\s*[\[【(（]?\s*[A-Za-z]+\s*\d+\s*[\]】)）]?\s*[:：\-—.、]*\s*")
REVIEW_ID_RE = re.compile(r"\bRV-[A-Za-z0-9]+\b")

VALID_TASK_TYPES = {"planning", "development", "testing"}
VALID_TASK_STATUSES = {"todo", "in_progress", "done", "blocked"}
VALID_EVENT_KINDS = {"progress", "start", "complete", "blocked", "note"}
TASK_STATUS_ALIASES = {
    "todo": "todo",
    "pending": "todo",
    "not_started": "todo",
    "open": "todo",
    "in_progress": "in_progress",
    "started": "in_progress",
    "running": "in_progress",
    "doing": "in_progress",
    "complete": "done",
    "completed": "done",
    "done": "done",
    "blocked": "blocked",
}
TASK_TYPE_LABELS = ("任务类型", "Task Type", "task_type")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _slugify(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", _text(text).lower()).strip("-")
    return normalized or "project"


def _optional_text(value: Any) -> str | None:
    text = _text(value)
    return text or None


def _timestamp_text(value: Any) -> str | None:
    if isinstance(value, dict):
        return _optional_text(value.get("timestamp"))
    return _optional_text(value)


def _completed_timestamp(value: Any) -> str | None:
    text = _optional_text(value)
    if text in {None, "", "0", "null", "None"}:
        return None
    return text


def _normalize_progress(value: Any) -> int | None:
    text = _text(value)
    if not text:
        return None
    try:
        progress = int(text)
    except ValueError:
        return None
    if 0 <= progress <= 100:
        return progress
    return None


def _normalize_status(value: Any) -> str | None:
    normalized = TASK_STATUS_ALIASES.get(_text(value).lower())
    return normalized if normalized in VALID_TASK_STATUSES else None


def _normalize_task_type(value: Any) -> str | None:
    normalized = _text(value).lower()
    return normalized if normalized in VALID_TASK_TYPES else None


def _normalize_kind(value: Any) -> str | None:
    normalized = _text(value).lower()
    return normalized if normalized in VALID_EVENT_KINDS else None


def _extract_task_title(summary: str, parsed: dict[str, Any] | None = None) -> str:
    if isinstance(parsed, dict):
        body = _text(parsed.get("body"))
        if body:
            return body
    stripped = SUMMARY_PREFIX_RE.sub("", _text(summary), count=1).strip()
    return stripped or _text(summary)


def _parsed_summary(summary: str) -> dict[str, Any]:
    parsed = parse_task_summary(summary)
    return parsed if isinstance(parsed, dict) else {}


def _task_number_for_sort(task: dict[str, Any]) -> int:
    return int(_parsed_summary(_text(task.get("summary"))).get("number") or 0)


def _extract_task_type_from_description(description: str) -> str | None:
    lines = str(description or "").splitlines()
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        for label in TASK_TYPE_LABELS:
            match = re.match(rf"^{re.escape(label)}\s*[：:]\s*(.+)$", line, flags=re.IGNORECASE)
            if not match:
                continue
            normalized = _normalize_task_type(match.group(1))
            if normalized:
                return normalized
    return None


def parse_pm_event_block(raw_content: str) -> dict[str, Any]:
    text = str(raw_content or "")
    match = PM_EVENT_BLOCK_RE.search(text)
    if not match:
        return {
            "has_block": False,
            "parsed": False,
            "content": text.strip(),
            "raw_content": text,
            "meta": {},
        }

    stripped_content = PM_EVENT_BLOCK_RE.sub("", text, count=1).strip()
    meta: dict[str, Any] = {}
    parsed = True
    for raw_line in str(match.group("body") or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" not in line:
            parsed = False
            continue
        key, value = line.split(":", 1)
        normalized_key = key.strip().lower()
        normalized_value = value.strip()
        if normalized_key == "schema":
            meta["schema"] = normalized_value
            if normalized_value != "v1":
                parsed = False
        elif normalized_key == "kind":
            meta["kind"] = _normalize_kind(normalized_value)
            if meta["kind"] is None:
                parsed = False
        elif normalized_key == "task_type":
            meta["task_type"] = _normalize_task_type(normalized_value)
            if normalized_value and meta["task_type"] is None:
                parsed = False
        elif normalized_key == "status":
            meta["status"] = _normalize_status(normalized_value)
            if normalized_value and meta["status"] is None:
                parsed = False
        elif normalized_key == "progress":
            meta["progress"] = _normalize_progress(normalized_value)
            if normalized_value and meta["progress"] is None:
                parsed = False
        elif normalized_key == "started_at":
            meta["started_at"] = _optional_text(normalized_value)
        elif normalized_key == "ended_at":
            meta["ended_at"] = _optional_text(normalized_value)
        else:
            parsed = False

    if meta.get("schema") != "v1" or not meta.get("kind"):
        parsed = False

    return {
        "has_block": True,
        "parsed": parsed,
        "content": stripped_content,
        "raw_content": text,
        "meta": meta,
    }


def comment_to_board_event(comment: dict[str, Any], *, task_guid: str = "", task_id: str = "") -> dict[str, Any]:
    raw_content = _text(comment.get("content"))
    parsed_block = parse_pm_event_block(raw_content)
    meta = parsed_block.get("meta") if isinstance(parsed_block.get("meta"), dict) else {}
    creator = comment.get("creator") if isinstance(comment.get("creator"), dict) else {}
    creator_payload = {
        "id": _optional_text(creator.get("id")),
        "type": _optional_text(creator.get("type")),
        "name": _optional_text(creator.get("name")),
    }
    if not any(creator_payload.values()):
        creator_payload = {}

    resolved_kind = _normalize_kind(meta.get("kind")) or "note"
    return {
        "id": _text(comment.get("id") or comment.get("guid")),
        "taskGuid": _text(task_guid or comment.get("resource_id")),
        "taskId": _optional_text(task_id),
        "kind": resolved_kind,
        "type": _normalize_task_type(meta.get("task_type")),
        "status": _normalize_status(meta.get("status")),
        "progress": _normalize_progress(meta.get("progress")),
        "startedAt": _optional_text(meta.get("started_at")),
        "endedAt": _optional_text(meta.get("ended_at")),
        "content": _text(parsed_block.get("content")) or raw_content,
        "rawContent": _text(parsed_block.get("raw_content")) or raw_content,
        "createdAt": _optional_text(comment.get("created_at")),
        "updatedAt": _optional_text(comment.get("updated_at")),
        "creator": creator_payload or None,
        "parsed": bool(parsed_block.get("parsed")),
    }


def _event_time_key(event: dict[str, Any]) -> str:
    return _text(event.get("updatedAt") or event.get("createdAt"))


def _comment_time_key(comment: dict[str, Any]) -> str:
    return _text(comment.get("updated_at") or comment.get("created_at"))


def _sort_comments(comments: list[dict[str, Any]], *, ascending: bool) -> list[dict[str, Any]]:
    return sorted(
        [item for item in comments if isinstance(item, dict)],
        key=_comment_time_key,
        reverse=not ascending,
    )


def _sort_events(events: list[dict[str, Any]], *, ascending: bool) -> list[dict[str, Any]]:
    return sorted(
        [item for item in events if isinstance(item, dict)],
        key=_event_time_key,
        reverse=not ascending,
    )


def _task_primary_list(task: dict[str, Any]) -> dict[str, Any]:
    tasklists = task.get("tasklists") if isinstance(task.get("tasklists"), list) else []
    for item in tasklists:
        if isinstance(item, dict):
            return item
    return {}


def _build_project_meta() -> dict[str, Any]:
    context = load_json_file(pm_file("current-context.json"))
    context_project = context.get("project") if isinstance(context, dict) and isinstance(context.get("project"), dict) else {}
    repo_root = Path(project_root_path()).resolve()
    task_cfg = ACTIVE_CONFIG.get("task") if isinstance(ACTIVE_CONFIG.get("task"), dict) else {}
    doc_cfg = ACTIVE_CONFIG.get("doc") if isinstance(ACTIVE_CONFIG.get("doc"), dict) else {}
    name = _text(context_project.get("name") or project_name() or repo_root.name)
    return {
        "id": _slugify(name),
        "name": name,
        "repoRoot": str(repo_root),
        "taskBackend": _text(context_project.get("task_backend") or task_cfg.get("backend") or "feishu"),
        "docBackend": _text(context_project.get("doc_backend") or doc_cfg.get("backend") or "feishu"),
        "tasklistGuid": _optional_text(context_project.get("tasklist_guid") or task_cfg.get("tasklist_guid")),
        "tasklistName": _optional_text(context_project.get("tasklist_name") or task_cfg.get("tasklist_name")),
        "generatedAt": _optional_text(context.get("generated_at")) or now_iso(),
    }


def _board_tasklists(*, include_all_visible_tasklists: bool, tasklist_guid: str = "") -> list[dict[str, Any]]:
    target_guid = _text(tasklist_guid)
    target_guids = {
        item.strip()
        for item in target_guid.split(",")
        if item.strip()
    }
    if include_all_visible_tasklists:
        rows = [
            item
            for item in list_visible_tasklists()
            if isinstance(item, dict) and _text(item.get("guid"))
        ]
        if target_guids:
            rows = [item for item in rows if _text(item.get("guid")) in target_guids]
        if rows:
            return rows
    tasklist = ensure_tasklist()
    if isinstance(tasklist, dict) and _text(tasklist.get("guid")):
        if target_guids and _text(tasklist.get("guid")) not in target_guids:
            return []
        return [tasklist]
    return []


def _tasklists_by_guid(tasklists: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        _text(item.get("guid")): item
        for item in tasklists
        if isinstance(item, dict) and _text(item.get("guid"))
    }


def _task_row_time_key(task: dict[str, Any]) -> str:
    return _text(task.get("updated_at") or task.get("created_at"))


def _sort_task_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [item for item in rows if isinstance(item, dict)],
        key=lambda item: (_task_row_time_key(item), _task_number_for_sort(item)),
        reverse=True,
    )


def _dedup_rows_by_guid(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    dedup: dict[str, dict[str, Any]] = {}
    for item in _sort_task_rows(rows):
        guid = _text(item.get("guid"))
        if not guid or guid in dedup:
            continue
        dedup[guid] = item
    return list(dedup.values())


def _selected_task_rows(rows: list[dict[str, Any]], *, include_completed: bool, limit: int) -> tuple[list[dict[str, Any]], bool]:
    selected = rows if include_completed else [item for item in rows if not _completed_timestamp(item.get("completed_at"))]
    ordered = _sort_task_rows(selected)
    if limit > 0 and len(ordered) > limit:
        return ordered[:limit], True
    return ordered, False


def _build_board_column(
    tasklist: dict[str, Any],
    *,
    include_completed: bool,
    limit: int,
    comment_limit: int,
    tasklists_by_guid: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    tasklist_guid = _text(tasklist.get("guid"))
    open_rows = list_tasklist_tasks(tasklist_guid, completed=False) if tasklist_guid else []
    completed_rows = list_tasklist_tasks(tasklist_guid, completed=True) if tasklist_guid else []
    all_rows = _dedup_rows_by_guid(open_rows + completed_rows)
    selected_rows, has_more_tasks = _selected_task_rows(all_rows, include_completed=include_completed, limit=limit)

    board_tasks: list[dict[str, Any]] = []
    recent_events: list[dict[str, Any]] = []
    for row in selected_rows:
        guid = _text(row.get("guid"))
        detail = get_task_record_by_guid(guid) if guid else row
        comments = list_task_comments(guid, comment_limit) if guid and comment_limit != 0 else []
        board_task = build_board_task(detail, comments=comments, tasklists_by_guid=tasklists_by_guid)
        board_tasks.append(board_task)
        task_id = _text(board_task.get("taskId"))
        recent_events.extend(comment_to_board_event(item, task_guid=guid, task_id=task_id) for item in comments if isinstance(item, dict))

    column = {
        "id": tasklist_guid or _slugify(_text(tasklist.get("name"))),
        "kind": "tasklist",
        "title": _text(tasklist.get("name")) or "Untitled",
        "tasklistGuid": _optional_text(tasklist.get("guid")),
        "tasklistUrl": _optional_text(tasklist.get("url")),
        "updatedAt": _optional_text(tasklist.get("updated_at")),
        "visibleTaskCount": len(board_tasks),
        "hasMoreTasks": has_more_tasks,
        "stats": _status_counts_from_rows(all_rows),
        "tasks": board_tasks,
    }
    return column, all_rows, recent_events


def _task_id_from_task_payload(task: dict[str, Any]) -> str:
    parsed = _parsed_summary(_text(task.get("summary")))
    if _text(parsed.get("task_id")):
        return _text(parsed.get("task_id"))
    return _text(parse_task_id_from_description(_text(task.get("description"))))


def _find_visible_task_by_id(task_id: str, *, include_completed: bool) -> dict[str, Any]:
    normalized_task_id = _text(task_id)
    if not normalized_task_id:
        raise SystemExit("missing task id")

    for tasklist in _board_tasklists(include_all_visible_tasklists=True):
        tasklist_guid = _text(tasklist.get("guid"))
        if not tasklist_guid:
            continue
        rows = list_tasklist_tasks(tasklist_guid, completed=False)
        if include_completed:
            rows += list_tasklist_tasks(tasklist_guid, completed=True)
        for row in _dedup_rows_by_guid(rows):
            parsed_task_id = _text((_parsed_summary(_text(row.get("summary"))) or {}).get("task_id"))
            if parsed_task_id == normalized_task_id:
                guid = _text(row.get("guid"))
                return get_task_record_by_guid(guid) if guid else row
        for row in _dedup_rows_by_guid(rows):
            guid = _text(row.get("guid"))
            if not guid:
                continue
            detail = get_task_record_by_guid(guid)
            if _task_id_from_task_payload(detail) == normalized_task_id:
                return detail

    raise SystemExit(f"task not found across visible Feishu tasklists: {normalized_task_id}")


def _task_status(task: dict[str, Any], latest_event: dict[str, Any] | None = None) -> str:
    if _completed_timestamp(task.get("completed_at")):
        return "done"
    if isinstance(latest_event, dict):
        latest_status = _normalize_status(latest_event.get("status"))
        if latest_status:
            return latest_status
        latest_kind = _normalize_kind(latest_event.get("kind"))
        if latest_kind == "complete":
            return "done"
        if latest_kind == "blocked":
            return "blocked"
        if latest_kind in {"progress", "start"}:
            return "in_progress"
    return _normalize_status(task.get("status")) or "todo"


def build_board_task(
    task: dict[str, Any],
    *,
    comments: list[dict[str, Any]] | None = None,
    tasklists_by_guid: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_task = task if isinstance(task, dict) else {}
    guid = _text(normalized_task.get("guid"))
    summary = _text(normalized_task.get("summary"))
    description = _text(normalized_task.get("description"))
    parsed_summary = parse_task_summary(summary) or {}
    task_id = _text(parsed_summary.get("task_id") or parse_task_id_from_description(description))
    ordered_comments = _sort_comments(comments or [], ascending=False)
    events_desc = [comment_to_board_event(item, task_guid=guid, task_id=task_id) for item in ordered_comments]
    latest_event = events_desc[0] if events_desc else None
    primary_list = _task_primary_list(normalized_task)
    tasklist_guid = _optional_text(primary_list.get("tasklist_guid") or primary_list.get("tasklistGuid") or primary_list.get("guid"))
    tasklist_meta = (tasklists_by_guid or {}).get(tasklist_guid or "") if isinstance(tasklists_by_guid, dict) else {}
    status = _task_status(normalized_task, latest_event=latest_event)
    progress = 100 if status == "done" else _normalize_progress((latest_event or {}).get("progress"))
    return {
        "taskId": task_id,
        "guid": guid,
        "url": _optional_text(normalized_task.get("url")),
        "title": _extract_task_title(summary, parsed_summary),
        "description": _optional_text(description),
        "status": status,
        "type": _normalize_task_type((latest_event or {}).get("type")) or _extract_task_type_from_description(description),
        "progress": progress,
        "createdAt": _optional_text(normalized_task.get("created_at")),
        "updatedAt": _optional_text(normalized_task.get("updated_at")),
        "startedAt": _timestamp_text(normalized_task.get("start")) or _optional_text((latest_event or {}).get("startedAt")),
        "dueAt": _timestamp_text(normalized_task.get("due")),
        "completedAt": _completed_timestamp(normalized_task.get("completed_at")),
        "sectionGuid": _optional_text(primary_list.get("section_guid") or primary_list.get("sectionGuid")),
        "tasklistGuid": tasklist_guid,
        "tasklistName": _optional_text(tasklist_meta.get("name")),
        "members": list(normalized_task.get("members") or []),
        "attachments": list(normalized_task.get("attachments") or []),
        "latestEvent": latest_event,
    }


def _status_counts_from_rows(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"todo": 0, "in_progress": 0, "blocked": 0, "done": 0}
    for item in tasks:
        status = "done" if _completed_timestamp(item.get("completed_at")) else (_normalize_status(item.get("status")) or "todo")
        counts[status] += 1
    return {
        "totalTasks": len(tasks),
        "todoTasks": counts["todo"],
        "inProgressTasks": counts["in_progress"],
        "blockedTasks": counts["blocked"],
        "doneTasks": counts["done"],
    }


def _review_state_records() -> list[dict[str, Any]]:
    state = load_json_file(pm_file("project-review-state.json"))
    records = state.get("reviews") if isinstance(state, dict) else []
    return [item for item in records if isinstance(item, dict)]


def _extract_matching_project(record: dict[str, Any], current_project_name: str) -> dict[str, Any]:
    card = record.get("card_preview") if isinstance(record.get("card_preview"), dict) else {}
    bundle = record.get("bundle") if isinstance(record.get("bundle"), dict) else {}
    for collection in (card.get("projects"), bundle.get("projects")):
        if not isinstance(collection, list):
            continue
        for item in collection:
            if not isinstance(item, dict):
                continue
            if _text(item.get("project")) == current_project_name:
                return item
    return {}


def _review_match_score(record: dict[str, Any], current_project_name: str) -> int:
    project_name_value = _text(record.get("project_name"))
    bundle = record.get("bundle") if isinstance(record.get("bundle"), dict) else {}
    bundle_project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
    if project_name_value == current_project_name:
        return 4
    if _text(bundle_project.get("name")) == current_project_name:
        return 3
    if _extract_matching_project(record, current_project_name):
        return 2
    if project_name_value in {"全部项目", "all-projects", "all projects"}:
        return 1
    return 0


def _review_risks(record: dict[str, Any]) -> list[dict[str, Any]]:
    card = record.get("card_preview") if isinstance(record.get("card_preview"), dict) else {}
    bundle = record.get("bundle") if isinstance(record.get("bundle"), dict) else {}
    candidates: list[dict[str, Any]] = []
    for collection in (card.get("risk_items"), card.get("top_risks"), bundle.get("findings")):
        if not isinstance(collection, list):
            continue
        for item in collection:
            if isinstance(item, dict):
                candidates.append(item)
        if candidates:
            break

    result: list[dict[str, Any]] = []
    for item in candidates[:2]:
        title = _text(item.get("card_title") or item.get("title") or item.get("summary"))
        if not title:
            continue
        summary = _text(item.get("card_summary") or item.get("summary"))
        line_text = _text(item.get("line"))
        result.append(
            {
                "severity": _optional_text(item.get("severity")),
                "title": title,
                "file": _optional_text(item.get("file")),
                "line": int(line_text) if line_text.isdigit() else None,
                "suggestion": summary or None,
            }
        )
    return result


def build_review_summary(record: dict[str, Any], *, current_project_name: str) -> dict[str, Any]:
    card = record.get("card_preview") if isinstance(record.get("card_preview"), dict) else {}
    match = _extract_matching_project(record, current_project_name)
    done_items = [item for item in (card.get("done_items") or []) if _text(item)]
    summary = _text(card.get("review_summary") or match.get("summary"))
    done = _text(match.get("done")) or ("；".join(_text(item) for item in done_items[:2]) if done_items else "")
    pending = _text(match.get("pending"))
    next_step = _text(card.get("next_action") or match.get("next_step"))
    delivery = record.get("delivery") if isinstance(record.get("delivery"), dict) else {}
    return {
        "reviewId": _text(record.get("review_id")),
        "status": _text(record.get("status") or "draft"),
        "projectName": _text(record.get("project_name") or current_project_name),
        "triggerKind": _text(record.get("trigger_kind") or ((record.get("bundle") or {}).get("trigger") or {}).get("kind")),
        "title": _text(card.get("title")) or "项目回顾",
        "summary": summary or None,
        "done": done or None,
        "pending": pending or None,
        "nextStep": next_step or None,
        "risks": _review_risks(record),
        "createdAt": _optional_text(record.get("created_at")),
        "updatedAt": _optional_text(record.get("updated_at")),
        "sentAt": _optional_text(record.get("sent_at")),
        "delivery": {
            "chatId": _optional_text(delivery.get("chat_id") or delivery.get("chatId")),
            "messageId": _optional_text(delivery.get("message_id") or delivery.get("messageId")),
        },
    }


def load_latest_review_summary(*, current_project_name: str) -> dict[str, Any] | None:
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for record in _review_state_records():
        score = _review_match_score(record, current_project_name)
        if score <= 0:
            continue
        candidates.append((score, _text(record.get("updated_at") or record.get("created_at")), record))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return build_review_summary(candidates[0][2], current_project_name=current_project_name)


def _related_review_summaries(task: dict[str, Any], *, current_project_name: str) -> list[dict[str, Any]]:
    review_ids = sorted(
        {
            match.group(0)
            for text in (_text(task.get("summary")), _text(task.get("description")))
            for match in REVIEW_ID_RE.finditer(text)
        }
    )
    if not review_ids:
        return []
    records_by_id = {str(item.get("review_id") or ""): item for item in _review_state_records()}
    summaries: list[dict[str, Any]] = []
    for review_id in review_ids:
        record = records_by_id.get(review_id)
        if isinstance(record, dict):
            summaries.append(build_review_summary(record, current_project_name=current_project_name))
    return summaries


def build_project_board(
    *,
    include_completed: bool = False,
    tasklist_guid: str = "",
    limit: int = 20,
    comment_limit: int = 5,
    recent_events_limit: int = 10,
    include_all_visible_tasklists: bool = False,
) -> dict[str, Any]:
    project_meta = _build_project_meta()
    tasklists = _board_tasklists(
        include_all_visible_tasklists=include_all_visible_tasklists,
        tasklist_guid=tasklist_guid,
    )
    tasklists_by_guid = _tasklists_by_guid(tasklists)

    columns: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    recent_events: list[dict[str, Any]] = []
    board_tasks: list[dict[str, Any]] = []

    if tasklists:
        sortable_columns: list[tuple[int, str, dict[str, Any]]] = []
        for tasklist in tasklists:
            column, column_rows, column_events = _build_board_column(
                tasklist,
                include_completed=include_completed,
                limit=limit,
                comment_limit=comment_limit,
                tasklists_by_guid=tasklists_by_guid,
            )
            sortable_columns.append(
                (
                    int(column["stats"]["todoTasks"]) + int(column["stats"]["inProgressTasks"]) + int(column["stats"]["blockedTasks"]),
                    _text(column.get("updatedAt")),
                    column,
                )
            )
            all_rows.extend(column_rows)
            recent_events.extend(column_events)
            board_tasks.extend(column.get("tasks") or [])
        sortable_columns.sort(key=lambda item: (item[0], item[1]), reverse=True)
        columns = [item[2] for item in sortable_columns]
    else:
        rows = [item for item in task_pool(include_completed=True) if isinstance(item, dict)]
        rows = _dedup_rows_by_guid(rows)
        selected_rows, _ = _selected_task_rows(rows, include_completed=include_completed, limit=limit)
        all_rows = rows
        board_tasks = []
        for row in selected_rows:
            guid = _text(row.get("guid"))
            detail = get_task_record_by_guid(guid) if guid else row
            comments = list_task_comments(guid, comment_limit) if guid and comment_limit != 0 else []
            board_task = build_board_task(detail, comments=comments, tasklists_by_guid=tasklists_by_guid)
            board_tasks.append(board_task)
            task_id = _text(board_task.get("taskId"))
            recent_events.extend(comment_to_board_event(item, task_guid=guid, task_id=task_id) for item in comments if isinstance(item, dict))

    dedup_tasks: dict[str, dict[str, Any]] = {}
    for item in [row for row in board_tasks if isinstance(row, dict)]:
        guid = _text(item.get("guid"))
        if guid and guid not in dedup_tasks:
            dedup_tasks[guid] = item
    board_tasks = sorted(
        dedup_tasks.values(),
        key=lambda item: (_text(item.get("updatedAt") or item.get("createdAt")), _text(item.get("guid"))),
        reverse=True,
    )

    dedup_events: dict[str, dict[str, Any]] = {}
    for event in _sort_events(recent_events, ascending=False):
        event_id = _text(event.get("id"))
        if event_id and event_id not in dedup_events:
            dedup_events[event_id] = event
    recent_events = list(dedup_events.values())
    if recent_events_limit > 0:
        recent_events = recent_events[:recent_events_limit]

    return {
        "project": project_meta,
        "scope": "all_visible_tasklists" if include_all_visible_tasklists else "configured_tasklist",
        "columns": columns,
        "stats": _status_counts_from_rows(_dedup_rows_by_guid(all_rows)),
        "tasks": board_tasks,
        "recentEvents": recent_events,
        "latestReview": load_latest_review_summary(current_project_name=_text(project_meta.get("name"))),
    }


def build_task_board_detail(
    *,
    task_id: str = "",
    task_guid: str = "",
    include_completed: bool = True,
    comment_limit: int = 20,
) -> dict[str, Any]:
    if task_guid:
        task = get_task_record_by_guid(task_guid)
    else:
        try:
            task = get_task_record(task_id, include_completed=include_completed)
        except SystemExit as exc:
            if "task not found" not in _text(exc).lower():
                raise
            task = _find_visible_task_by_id(task_id, include_completed=include_completed)
    guid = _text(task.get("guid"))
    comments = list_task_comments(guid, comment_limit) if guid and comment_limit != 0 else []
    parsed_summary = _parsed_summary(_text(task.get("summary")))
    resolved_task_id = _text(parsed_summary.get("task_id") or task_id or parse_task_id_from_description(_text(task.get("description"))))
    ordered_events = [
        comment_to_board_event(item, task_guid=guid, task_id=resolved_task_id)
        for item in _sort_comments(comments, ascending=True)
    ]
    project_meta = _build_project_meta()
    tasklists_by_guid = _tasklists_by_guid(_board_tasklists(include_all_visible_tasklists=True))
    board_task = build_board_task(task, comments=comments, tasklists_by_guid=tasklists_by_guid)
    return {
        "project": project_meta,
        "task": board_task,
        "events": ordered_events,
        "relatedReviews": _related_review_summaries(task, current_project_name=_text(project_meta.get("name"))),
    }


__all__ = [
    "build_project_board",
    "build_review_summary",
    "build_task_board_detail",
    "build_board_task",
    "comment_to_board_event",
    "load_latest_review_summary",
    "parse_pm_event_block",
]
