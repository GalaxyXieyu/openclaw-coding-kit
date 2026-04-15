from __future__ import annotations

import copy
import mimetypes
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from pm_config import pm_file
from pm_io import load_json_file, now_iso, write_repo_json
from pm_task_members import normalize_task_members

LOCAL_BACKEND_FILE = "local-tasks.json"
SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    normalized = str(text or "").strip().lower()
    slug = SLUG_RE.sub("-", normalized).strip("-")
    return slug or "default"


def local_backend_path() -> Path:
    return pm_file(LOCAL_BACKEND_FILE)


def _empty_store() -> dict[str, Any]:
    return {
        "version": 1,
        "backend": "local",
        "tasklists": [],
        "tasks": [],
    }


def load_local_store() -> dict[str, Any]:
    payload = load_json_file(local_backend_path())
    if not isinstance(payload, dict):
        return _empty_store()
    tasklists = payload.get("tasklists")
    tasks = payload.get("tasks")
    payload.setdefault("version", 1)
    payload["backend"] = "local"
    payload["tasklists"] = tasklists if isinstance(tasklists, list) else []
    payload["tasks"] = tasks if isinstance(tasks, list) else []
    return payload


def save_local_store(payload: dict[str, Any]) -> Path:
    path = local_backend_path()
    write_repo_json(path, payload)
    return path


def _task_status(task: dict[str, Any]) -> str:
    if str(task.get("completed_at") or "").strip():
        return "completed"
    start = task.get("start")
    started = isinstance(start, dict) and str(start.get("timestamp") or "").strip() not in {"", "0"}
    return "in_progress" if started else "todo"


def _normalize_task(task: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(task)
    normalized.setdefault("summary", "")
    normalized.setdefault("description", "")
    normalized.setdefault("guid", "")
    normalized.setdefault("url", "")
    normalized.setdefault("created_at", "")
    normalized.setdefault("updated_at", "")
    normalized.setdefault("completed_at", "")
    normalized.setdefault("start", {})
    normalized.setdefault("due", {})
    normalized.setdefault("members", [])
    normalized.setdefault("attachments", [])
    normalized.setdefault("tasklists", [])
    normalized.setdefault("comments", [])
    normalized["status"] = _task_status(normalized)
    return normalized


def inspect_tasklist(*, name: str, configured_guid: str = "") -> dict[str, Any]:
    store = load_local_store()
    resolved_name = str(name or "").strip()
    tasklists = [item for item in store.get("tasklists") or [] if isinstance(item, dict)]
    if configured_guid:
        for item in tasklists:
            if str(item.get("guid") or "").strip() == configured_guid:
                return {"status": "configured_match", "tasklist": copy.deepcopy(item), "matches": [copy.deepcopy(item)], "resolved_name": resolved_name}
    matches = [copy.deepcopy(item) for item in tasklists if str(item.get("name") or "").strip() == resolved_name]
    if len(matches) == 1:
        return {"status": "unique_match", "tasklist": matches[0], "matches": matches, "resolved_name": resolved_name}
    if len(matches) > 1:
        return {"status": "ambiguous", "tasklist": None, "matches": matches, "resolved_name": resolved_name}
    return {"status": "missing", "tasklist": None, "matches": [], "resolved_name": resolved_name}


def ensure_tasklist(*, name: str, configured_guid: str = "") -> dict[str, Any]:
    inspection = inspect_tasklist(name=name, configured_guid=configured_guid)
    tasklist = inspection.get("tasklist")
    if isinstance(tasklist, dict) and str(tasklist.get("guid") or "").strip():
        return tasklist
    resolved_name = str(inspection.get("resolved_name") or name or "").strip() or "Local Tasks"
    guid = str(configured_guid or f"local:{_slugify(resolved_name)}").strip()
    tasklist = {
        "guid": guid,
        "name": resolved_name,
        "url": f"local://tasklist/{guid}",
        "owner": {"id": "local-user", "name": "local-user"},
    }
    store = load_local_store()
    tasklists = [item for item in store.get("tasklists") or [] if isinstance(item, dict)]
    tasklists = [item for item in tasklists if str(item.get("guid") or "").strip() != guid]
    tasklists.append(tasklist)
    store["tasklists"] = tasklists
    save_local_store(store)
    return copy.deepcopy(tasklist)


def list_tasklist_tasks(tasklist_guid: str, *, completed: bool) -> list[dict[str, Any]]:
    guid = str(tasklist_guid or "").strip()
    rows: list[dict[str, Any]] = []
    for item in load_local_store().get("tasks") or []:
        if not isinstance(item, dict):
            continue
        task = _normalize_task(item)
        task_tasklists = task.get("tasklists") or []
        belongs = any(str(entry.get("tasklist_guid") or entry.get("guid") or "").strip() == guid for entry in task_tasklists if isinstance(entry, dict))
        if not belongs:
            continue
        is_completed = bool(str(task.get("completed_at") or "").strip())
        if is_completed != completed:
            continue
        rows.append(task)
    rows.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("guid") or "")))
    return rows


def get_task_by_guid(task_guid: str) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    for item in load_local_store().get("tasks") or []:
        if isinstance(item, dict) and str(item.get("guid") or "").strip() == guid:
            return _normalize_task(item)
    raise SystemExit(f"failed to load local task by guid: {guid}")


def create_task(
    *,
    summary: str,
    description: str,
    tasklists: list[dict[str, Any]] | None = None,
    current_user_id: str = "",
    members: list[dict[str, Any]] | None = None,
    gsd_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    store = load_local_store()
    guid = f"local-task-{uuid.uuid4().hex[:12]}"
    created_at = now_iso()
    resolved_members = normalize_task_members(members)
    if not resolved_members and str(current_user_id or "").strip():
        resolved_members = [{"id": str(current_user_id).strip(), "role": "assignee"}]
    task = {
        "guid": guid,
        "url": f"local://task/{guid}",
        "summary": str(summary or "").strip(),
        "description": str(description or "").strip(),
        "created_at": created_at,
        "updated_at": created_at,
        "completed_at": "",
        "start": {},
        "due": {},
        "members": resolved_members,
        "attachments": [],
        "comments": [],
        "tasklists": [copy.deepcopy(item) for item in (tasklists or []) if isinstance(item, dict)],
    }
    if isinstance(gsd_contract, dict) and gsd_contract:
        task["gsd_contract"] = copy.deepcopy(gsd_contract)
    tasks = [item for item in store.get("tasks") or [] if isinstance(item, dict)]
    tasks.append(task)
    store["tasks"] = tasks
    save_local_store(store)
    return _normalize_task(task)


def patch_task(task_guid: str, changes: dict[str, Any]) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    store = load_local_store()
    tasks = [item for item in store.get("tasks") or [] if isinstance(item, dict)]
    for index, item in enumerate(tasks):
        if str(item.get("guid") or "").strip() != guid:
            continue
        updated = copy.deepcopy(item)
        for key, value in changes.items():
            if key == "task_guid":
                continue
            updated[key] = copy.deepcopy(value)
        updated["updated_at"] = now_iso()
        tasks[index] = updated
        store["tasks"] = tasks
        save_local_store(store)
        return _normalize_task(updated)
    raise SystemExit(f"failed to patch local task: {guid}")


def list_comments(resource_id: str, *, direction: str = "desc", page_size: int = 20) -> list[dict[str, Any]]:
    task = get_task_by_guid(resource_id)
    comments = [copy.deepcopy(item) for item in (task.get("comments") or []) if isinstance(item, dict)]
    comments.sort(key=lambda item: str(item.get("created_at") or ""), reverse=str(direction or "").strip().lower() != "asc")
    if page_size > 0:
        comments = comments[:page_size]
    return comments


def create_comment(task_guid: str, content: str) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    store = load_local_store()
    tasks = [item for item in store.get("tasks") or [] if isinstance(item, dict)]
    for index, item in enumerate(tasks):
        if str(item.get("guid") or "").strip() != guid:
            continue
        updated = copy.deepcopy(item)
        comments = [copy.deepcopy(entry) for entry in (updated.get("comments") or []) if isinstance(entry, dict)]
        comment = {
            "guid": f"local-comment-{uuid.uuid4().hex[:12]}",
            "content": str(content or "").strip(),
            "resource_id": guid,
            "created_at": now_iso(),
        }
        comments.append(comment)
        updated["comments"] = comments
        updated["updated_at"] = now_iso()
        tasks[index] = updated
        store["tasks"] = tasks
        save_local_store(store)
        return copy.deepcopy(comment)
    raise SystemExit(f"failed to create local task comment: {guid}")


def list_attachments(task_guid: str, *, download_dir: str = "") -> dict[str, Any]:
    task = get_task_by_guid(task_guid)
    attachments = [copy.deepcopy(item) for item in (task.get("attachments") or []) if isinstance(item, dict)]
    downloads: list[dict[str, Any]] = []
    if download_dir:
        output_dir = Path(download_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        for index, item in enumerate(attachments, start=1):
            source_path = Path(str(item.get("source_path") or "")).expanduser()
            if not source_path.exists() or not source_path.is_file():
                downloads.append({"index": index, "name": str(item.get("name") or ""), "error": "missing_source_path", "source_path": str(source_path)})
                continue
            target_path = output_dir / str(item.get("name") or source_path.name)
            if target_path.exists():
                target_path = target_path.with_name(f"{target_path.stem}_{index}{target_path.suffix}")
            shutil.copy2(source_path, target_path)
            downloads.append({"index": index, "name": str(item.get("name") or ""), "saved_path": str(target_path), "size": int(item.get("size") or 0)})
    return {
        "status": "ok",
        "task_guid": task_guid,
        "attachment_count": len(attachments),
        "attachments": attachments,
        "downloads": downloads,
    }


def add_attachments(task_guid: str, file_args: list[str]) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    if not guid:
        raise SystemExit("task guid is required")
    files: list[Path] = []
    for raw in file_args:
        path = Path(str(raw or "")).expanduser()
        if not path.exists():
            raise SystemExit(f"upload file not found: {path}")
        if not path.is_file():
            raise SystemExit(f"upload path is not a file: {path}")
        files.append(path)
    if not files:
        return {
            "status": "skipped",
            "task_guid": guid,
            "uploaded_count": 0,
            "uploaded_files": [],
            "attachments": [],
            "auto_started": False,
            "start_result": None,
        }
    store = load_local_store()
    tasks = [item for item in store.get("tasks") or [] if isinstance(item, dict)]
    for index, item in enumerate(tasks):
        if str(item.get("guid") or "").strip() != guid:
            continue
        updated = copy.deepcopy(item)
        attachments = [copy.deepcopy(entry) for entry in (updated.get("attachments") or []) if isinstance(entry, dict)]
        uploaded_items: list[dict[str, Any]] = []
        for path in files:
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            attachment = {
                "guid": f"local-attachment-{uuid.uuid4().hex[:12]}",
                "name": path.name,
                "source_path": str(path.resolve()),
                "size": path.stat().st_size,
                "content_type": mime_type,
                "url": f"local://attachment/{path.name}",
                "uploaded_at": now_iso(),
            }
            attachments.append(attachment)
            uploaded_items.append(copy.deepcopy(attachment))
        updated["attachments"] = attachments
        updated["updated_at"] = now_iso()
        tasks[index] = updated
        store["tasks"] = tasks
        save_local_store(store)
        return {
            "status": "ok",
            "task_guid": guid,
            "uploaded_count": len(uploaded_items),
            "uploaded_files": [str(path) for path in files],
            "attachments": uploaded_items,
            "auto_started": False,
            "start_result": None,
        }
    raise SystemExit(f"failed to upload local task attachments: {guid}")
