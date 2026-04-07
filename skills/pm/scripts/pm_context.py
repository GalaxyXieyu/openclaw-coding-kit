from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

TaskBriefFn = Callable[[dict[str, Any]], dict[str, Any]]
ExtractTaskNumberFn = Callable[[str], int]
TaskPoolFn = Callable[..., list[dict[str, Any]]]
GetTaskRecordByGuidFn = Callable[[str], dict[str, Any]]
GetTaskRecordFn = Callable[[str], dict[str, Any]]
ProjectRootFn = Callable[[], Path]
EnsureTasklistFn = Callable[[], dict[str, Any]]
ProjectNameFn = Callable[[], str]
TasklistNameFn = Callable[[], str]
TaskPrefixFn = Callable[[], str]
TaskKindFn = Callable[[], str]
RepoScanFn = Callable[[Path], dict[str, Any]]
BootstrapInfoFn = Callable[[Path], dict[str, Any]]
GsdAssetsFn = Callable[[Path], dict[str, Any]]
ParseTaskSummaryFn = Callable[[str], Optional[dict[str, Any]]]
ParseTaskIdFromDescriptionFn = Callable[[str], str]
NowIsoFn = Callable[[], str]
PmFileFn = Callable[..., Path]
WriteRepoJsonFn = Callable[[Path, dict[str, Any]], Path]
ListTaskCommentsFn = Callable[[str, int], list[dict[str, Any]]]


def task_summary_text(item: dict[str, Any]) -> str:
    return str(item.get("normalized_summary") or item.get("summary") or "")


def task_number(item: dict[str, Any], *, extract_task_number: ExtractTaskNumberFn) -> int:
    return extract_task_number(task_summary_text(item))


def task_brief(item: dict[str, Any], *, parse_task_summary: ParseTaskSummaryFn) -> dict[str, Any]:
    parsed = parse_task_summary(task_summary_text(item)) or {}
    return {
        "task_id": str(parsed.get("task_id") or item.get("normalized_task_id") or ""),
        "summary": task_summary_text(item),
        "status": item.get("status") or "",
        "guid": item.get("guid") or "",
        "url": item.get("url") or "",
        "updated_at": item.get("updated_at") or "",
        "created_at": item.get("created_at") or "",
    }


def choose_next_task(open_rows: list[dict[str, Any]], *, extract_task_number: ExtractTaskNumberFn) -> Optional[dict[str, Any]]:
    numbered = [item for item in open_rows if task_number(item, extract_task_number=extract_task_number) > 0]
    if not numbered:
        return None
    numbered.sort(key=lambda item: (task_number(item, extract_task_number=extract_task_number), str(item.get("created_at") or "")))
    return numbered[0]


def build_context_payload(
    *,
    selected_task: Optional[dict[str, Any]] = None,
    active_config: dict[str, Any],
    project_root_path: ProjectRootFn,
    ensure_tasklist: EnsureTasklistFn,
    task_pool: TaskPoolFn,
    extract_task_number: ExtractTaskNumberFn,
    get_task_record_by_guid: GetTaskRecordByGuidFn,
    list_task_comments: ListTaskCommentsFn,
    project_name: ProjectNameFn,
    tasklist_name: TasklistNameFn,
    task_prefix: TaskPrefixFn,
    task_kind: TaskKindFn,
    repo_scan: RepoScanFn,
    build_bootstrap_info: BootstrapInfoFn,
    detect_gsd_assets: GsdAssetsFn,
    parse_task_summary: ParseTaskSummaryFn,
    parse_task_id_from_description: ParseTaskIdFromDescriptionFn,
    now_iso: NowIsoFn,
) -> dict[str, Any]:
    root = project_root_path()
    tasklist = ensure_tasklist()
    open_rows = [item for item in task_pool(include_completed=False) if task_number(item, extract_task_number=extract_task_number) > 0]
    open_rows.sort(key=lambda item: (task_number(item, extract_task_number=extract_task_number), str(item.get("created_at") or "")))
    next_task = choose_next_task(open_rows, extract_task_number=extract_task_number)
    current = selected_task or (
        get_task_record_by_guid(str(next_task.get("guid") or ""))
        if isinstance(next_task, dict) and str(next_task.get("guid") or "")
        else None
    )
    current_guid = str((current or {}).get("guid") or "").strip() if isinstance(current, dict) else ""
    comments: list[dict[str, Any]] = []
    if current_guid:
        comments = list_task_comments(current_guid, 10)
    task_cfg = active_config.get("task") if isinstance(active_config.get("task"), dict) else {}
    doc_cfg = active_config.get("doc") if isinstance(active_config.get("doc"), dict) else {}
    payload = {
        "generated_at": now_iso(),
        "project": {
            "name": project_name(),
            "repo_root": str(root),
            "config_path": str(active_config.get("_config_path") or ""),
            "tasklist_name": tasklist_name(),
            "tasklist_guid": str(tasklist.get("guid") or ""),
            "task_prefix": task_prefix(),
            "kind": task_kind(),
            "task_backend": str(task_cfg.get("backend") or "feishu") if isinstance(task_cfg, dict) else "feishu",
            "doc_backend": str(doc_cfg.get("backend") or "feishu") if isinstance(doc_cfg, dict) else "feishu",
        },
        "repo_scan": repo_scan(root),
        "bootstrap": build_bootstrap_info(root),
        "doc_index": {
            "folder_name": str(doc_cfg.get("folder_name") or "") if isinstance(doc_cfg, dict) else "",
            "folder_token": str(doc_cfg.get("folder_token") or "") if isinstance(doc_cfg, dict) else "",
            "folder_url": str(doc_cfg.get("folder_url") or "") if isinstance(doc_cfg, dict) else "",
            "project_doc_token": str(doc_cfg.get("project_doc_token") or "") if isinstance(doc_cfg, dict) else "",
            "project_doc_url": str(doc_cfg.get("project_doc_url") or "") if isinstance(doc_cfg, dict) else "",
            "requirements_doc_token": str(doc_cfg.get("requirements_doc_token") or "") if isinstance(doc_cfg, dict) else "",
            "requirements_doc_url": str(doc_cfg.get("requirements_doc_url") or "") if isinstance(doc_cfg, dict) else "",
            "roadmap_doc_token": str(doc_cfg.get("roadmap_doc_token") or "") if isinstance(doc_cfg, dict) else "",
            "roadmap_doc_url": str(doc_cfg.get("roadmap_doc_url") or "") if isinstance(doc_cfg, dict) else "",
            "state_doc_token": str(doc_cfg.get("state_doc_token") or "") if isinstance(doc_cfg, dict) else "",
            "state_doc_url": str(doc_cfg.get("state_doc_url") or "") if isinstance(doc_cfg, dict) else "",
        },
        "gsd": detect_gsd_assets(root),
        "open_tasks": [task_brief(item, parse_task_summary=parse_task_summary) for item in open_rows[:20]],
        "next_task": task_brief(next_task, parse_task_summary=parse_task_summary) if isinstance(next_task, dict) else None,
        "current_task": None,
        "recent_comments": comments,
    }
    if isinstance(current, dict) and current:
        parsed = parse_task_summary(task_summary_text(current)) or {}
        payload["current_task"] = {
            "task_id": str(parsed.get("task_id") or parse_task_id_from_description(str(current.get("description") or "")) or ""),
            "summary": str(parsed.get("normalized_summary") or task_summary_text(current)),
            "status": current.get("status") or "",
            "guid": current.get("guid") or "",
            "url": current.get("url") or "",
            "description": current.get("description") or "",
            "updated_at": current.get("updated_at") or "",
            "completed_at": current.get("completed_at") or "",
            "attachments": current.get("attachments") or [],
            "tasklists": current.get("tasklists") or [],
        }
    return payload


def refresh_context_cache(
    *,
    task_id: str = "",
    task_guid: str = "",
    build_context_payload_fn: Callable[..., dict[str, Any]],
    get_task_record_by_guid: GetTaskRecordByGuidFn,
    get_task_record: GetTaskRecordFn,
    pm_file: PmFileFn,
    write_repo_json: WriteRepoJsonFn,
) -> dict[str, Any]:
    selected_task: Optional[dict[str, Any]] = None
    if task_guid:
        selected_task = get_task_record_by_guid(task_guid)
    elif task_id:
        selected_task = get_task_record(task_id, include_completed=True)
    payload = build_context_payload_fn(selected_task=selected_task)
    context_path = pm_file("current-context.json")
    write_repo_json(context_path, payload)
    write_repo_json(pm_file("project-scan.json"), {"generated_at": payload["generated_at"], "repo_scan": payload["repo_scan"], "gsd": payload["gsd"]})
    write_repo_json(pm_file("bootstrap.json"), {"generated_at": payload["generated_at"], "project": payload.get("project") or {}, "bootstrap": payload.get("bootstrap") or {}, "gsd": payload.get("gsd") or {}})
    write_repo_json(pm_file("doc-index.json"), {"generated_at": payload["generated_at"], "doc_index": payload.get("doc_index") or {}})
    return payload


def build_planning_bundle(
    mode: str,
    *,
    task_id: str = "",
    task_guid: str = "",
    focus: str = "",
    refresh_context_cache_fn: Callable[..., dict[str, Any]],
    now_iso: NowIsoFn,
    write_pm_bundle: Callable[[str, dict[str, Any]], Path],
) -> tuple[dict[str, Any], Path]:
    context = refresh_context_cache_fn(task_id=task_id, task_guid=task_guid)
    current = context.get("current_task") if isinstance(context.get("current_task"), dict) else None
    if not current:
        current = context.get("next_task") if isinstance(context.get("next_task"), dict) else None
    bundle = {
        "generated_at": now_iso(),
        "mode": mode,
        "focus": focus.strip(),
        "project": context.get("project") or {},
        "repo_scan": context.get("repo_scan") or {},
        "bootstrap": context.get("bootstrap") or {},
        "gsd": context.get("gsd") or {},
        "current_task": current,
        "next_task": context.get("next_task"),
        "open_tasks": context.get("open_tasks") or [],
        "recent_comments": context.get("recent_comments") or [],
        "instructions": [
            "Use task as execution truth and doc as long-form truth.",
            "Prefer updating plan/refinement results back into the active task description or linked doc.",
            "Use repo scan and GSD assets as supporting context, not as the only source of truth.",
        ],
    }
    filename = "plan-context.json" if mode == "plan" else "refine-context.json"
    return bundle, write_pm_bundle(filename, bundle)


def build_coder_context(
    *,
    task_id: str = "",
    task_guid: str = "",
    refresh_context_cache_fn: Callable[..., dict[str, Any]],
    now_iso: NowIsoFn,
    active_config: dict[str, Any],
    pm_file: PmFileFn,
    write_pm_bundle: Callable[[str, dict[str, Any]], Path],
) -> tuple[dict[str, Any], Path]:
    context = refresh_context_cache_fn(task_id=task_id, task_guid=task_guid)
    bootstrap = context.get("bootstrap") if isinstance(context.get("bootstrap"), dict) else {}
    current = context.get("current_task") if isinstance(context.get("current_task"), dict) else None
    next_task = context.get("next_task") if isinstance(context.get("next_task"), dict) else None
    recommended: list[str] = []
    mode = str(bootstrap.get("project_mode") or "")
    action = str(bootstrap.get("recommended_action") or "")
    if mode == "brownfield" and action == "map-codebase":
        recommended.append("Run brownfield mapping before broad code changes; build task/doc understanding first.")
    if mode == "greenfield" and action == "new-project":
        recommended.append("Initialize the project structure and planning docs before implementation.")
    if current:
        recommended.append("Implement the current task first and update progress through pm when done.")
    elif next_task:
        recommended.append("No current task is active; start from next_task or refine the task plan before coding.")
    else:
        recommended.append("No task exists yet; create or refine a task before coding.")
    payload = {
        "generated_at": now_iso(),
        "project": context.get("project") or {},
        "repo_scan": context.get("repo_scan") or {},
        "bootstrap": bootstrap,
        "gsd": context.get("gsd") or {},
        "current_task": current,
        "next_task": next_task,
        "recent_comments": context.get("recent_comments") or [],
        "inputs": {
            "config": str(active_config.get("_config_path") or ""),
            "context_path": str(pm_file("current-context.json")),
            "bootstrap_path": str(pm_file("bootstrap.json")),
            "plan_path": str(pm_file("plan-context.json")),
            "refine_path": str(pm_file("refine-context.json")),
        },
        "recommended_flow": recommended,
        "required_reads": [
            "pm.json",
            ".pm/current-context.json",
            ".pm/bootstrap.json",
        ],
    }
    return payload, write_pm_bundle("coder-context.json", payload)
