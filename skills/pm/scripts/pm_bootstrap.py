from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

TaskPoolFn = Callable[..., list[dict[str, Any]]]
ExtractTaskNumberFn = Callable[[str], int]
ParseSummaryFn = Callable[[str], Optional[dict[str, Any]]]
EnsureTasklistFn = Callable[[], dict[str, Any]]
NextTaskIdFn = Callable[[], str]
BuildDescriptionFn = Callable[[str, str, str, str, str], str]
RunBridgeFn = Callable[..., dict[str, Any]]
DetailsFn = Callable[[dict[str, Any]], dict[str, Any]]
GetTaskRecordByGuidFn = Callable[[str], dict[str, Any]]
BuildBootstrapInfoFn = Callable[[Path], dict[str, Any]]
DocConfigFn = Callable[[], dict[str, Any]]
DetectProjectModeFn = Callable[[Path], str]


def bootstrap_task_template(
    root: Path,
    *,
    build_bootstrap_info: BuildBootstrapInfoFn,
    doc_config: DocConfigFn,
    detect_project_mode: DetectProjectModeFn,
) -> dict[str, str]:
    bootstrap = build_bootstrap_info(root)
    docs = doc_config()
    mode = str(bootstrap.get("project_mode") or "").strip() or detect_project_mode(root)
    if mode == "brownfield":
        summary = "初始化 brownfield 项目映射与文档索引"
        request_lines = [
            "先完成 brownfield 初始化。",
            "",
            "目标：",
            "- 做一次 map-codebase，快速建立代码结构/模块/入口理解。",
            "- 更新 PROJECT / ROADMAP / STATE 三篇文档。",
            "- 基于现有代码沉淀后续任务拆解建议。",
        ]
    else:
        summary = "初始化 greenfield 项目规划与脚手架"
        request_lines = [
            "先完成 greenfield 初始化。",
            "",
            "目标：",
            "- 做一次 new-project bootstrap，明确项目目标、结构和首轮实现路径。",
            "- 更新 PROJECT / ROADMAP / STATE 三篇文档。",
            "- 产出首批可执行任务拆解建议。",
        ]
    doc_links = [
        ("PROJECT", str(docs.get("project_doc_url") or "").strip()),
        ("ROADMAP", str(docs.get("roadmap_doc_url") or "").strip()),
        ("STATE", str(docs.get("state_doc_url") or "").strip()),
    ]
    linked = [f"- {name}: {url}" for name, url in doc_links if url]
    if linked:
        request_lines.extend(["", "参考文档：", *linked])
    request = "\n".join(request_lines).strip()
    return {"summary": summary, "request": request}


def ensure_bootstrap_task(
    root: Path,
    *,
    task_pool: TaskPoolFn,
    extract_task_number: ExtractTaskNumberFn,
    parse_task_summary: ParseSummaryFn,
    ensure_tasklist: EnsureTasklistFn,
    next_task_id: NextTaskIdFn,
    build_description: BuildDescriptionFn,
    run_bridge: RunBridgeFn,
    details_of: DetailsFn,
    get_task_record_by_guid: GetTaskRecordByGuidFn,
    build_bootstrap_info: BuildBootstrapInfoFn,
    doc_config: DocConfigFn,
    detect_project_mode: DetectProjectModeFn,
) -> dict[str, Any]:
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
    template = bootstrap_task_template(
        root,
        build_bootstrap_info=build_bootstrap_info,
        doc_config=doc_config,
        detect_project_mode=detect_project_mode,
    )
    task_id = next_task_id()
    title = f"[{task_id}] {template['summary']}"
    description = build_description(task_id, template["summary"], template["request"], str(root), "bootstrap")
    create_args: dict[str, Any] = {
        "summary": title,
        "description": description,
        "tasklists": [{"tasklist_guid": str(tasklist.get("guid") or "").strip()}],
    }
    payload = run_bridge("feishu_task_task", "create", create_args)
    task = details_of(payload).get("task") if isinstance(details_of(payload).get("task"), dict) else {}
    guid = str(task.get("guid") or "").strip()
    if guid:
        task = get_task_record_by_guid(guid)
    return {
        "created": True,
        "reason": "created",
        "task": {
            "task_id": task_id,
            "summary": str(task.get("summary") or title),
            "guid": guid,
            "url": str(task.get("url") or "").strip(),
            "description": str(task.get("description") or description),
        },
        "result": payload,
    }
