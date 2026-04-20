from __future__ import annotations

from typing import Any, Callable, Optional

ExtractDispatchIdsFn = Callable[[dict[str, Any]], tuple[str, str]]
CommentTaskFn = Callable[[str, str], Optional[dict[str, Any]]]
AppendStateFn = Callable[[str], Optional[dict[str, Any]]]
RefreshContextFn = Callable[..., dict[str, Any]]
NowTextFn = Callable[[], str]


def effective_task(bundle: dict[str, Any]) -> dict[str, Any]:
    current = bundle.get("current_task")
    if isinstance(current, dict) and current:
        return current
    next_task = bundle.get("next_task")
    if isinstance(next_task, dict) and next_task:
        return next_task
    return {}


def extract_text_payloads(agent_result: dict[str, Any]) -> list[str]:
    result = agent_result.get("result") if isinstance(agent_result, dict) else None
    payloads = result.get("payloads") if isinstance(result, dict) else None
    texts: list[str] = []
    if isinstance(payloads, list):
        for item in payloads:
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if text:
                    texts.append(text)
    return texts


def extract_dispatch_status(dispatch_result: dict[str, Any], *, session_key: str = "", run_id: str = "") -> tuple[str, str]:
    result = dispatch_result.get("result") if isinstance(dispatch_result.get("result"), dict) else {}
    result_details = result.get("details") if isinstance(result.get("details"), dict) else {}
    details = dispatch_result.get("details") if isinstance(dispatch_result.get("details"), dict) else {}
    status = str(result_details.get("status") or details.get("status") or dispatch_result.get("status") or "").strip().lower()
    error = str(result_details.get("error") or details.get("error") or dispatch_result.get("error") or "").strip()
    if not status and (session_key or run_id):
        status = "accepted"
    if error and status in {"", "ok"} and not (session_key or run_id):
        status = "error"
    return status, error


def extract_description_field(description: str, label: str) -> str:
    prefix = f"{label}:"
    for line in str(description or "").splitlines():
        text = str(line).strip()
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return ""


def extract_bullet_section(description: str, label: str) -> list[str]:
    items: list[str] = []
    in_section = False
    for raw_line in str(description or "").splitlines():
        line = str(raw_line).strip()
        if not in_section:
            if line == label:
                in_section = True
            continue
        if not line:
            break
        if not line.startswith("- "):
            break
        items.append(line[2:].strip())
    return items


def unique_reads(*groups: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            item = str(raw or "").strip()
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
    return result


def build_coder_handoff_contract(bundle: dict[str, Any]) -> dict[str, Any]:
    current = bundle.get("current_task") if isinstance(bundle.get("current_task"), dict) else {}
    next_task = bundle.get("next_task") if isinstance(bundle.get("next_task"), dict) else {}
    task = effective_task(bundle)
    active_task_source = "current_task" if current else "next_task" if next_task else ""
    description = str(task.get("description") or "").strip()
    structured_contract = task.get("gsd_contract") if isinstance(task.get("gsd_contract"), dict) else {}
    gsd_plan_path = str(structured_contract.get("plan_path") or "").strip() or extract_description_field(description, "GSD Plan Path")
    gsd_context_path = str(structured_contract.get("context_path") or "").strip() or extract_description_field(description, "GSD Context Path")
    gsd_required_reads = [str(item).strip() for item in (structured_contract.get("required_reads") or []) if str(item).strip()]
    if not gsd_required_reads:
        gsd_required_reads = extract_bullet_section(description, "GSD Required Reads:")
    bundle_required_reads = [str(item).strip() for item in (bundle.get("required_reads") or []) if str(item).strip()]
    required_reads = unique_reads(bundle_required_reads, [gsd_plan_path, gsd_context_path], gsd_required_reads)

    source_of_truth: list[str] = [
        "pm.json and .pm/coder-context.json define runtime/config context.",
    ]
    if active_task_source:
        source_of_truth.append(f"{active_task_source} description is the execution index card.")
    else:
        source_of_truth.append("No active task is selected yet; create or activate a task before coding.")
    if gsd_plan_path or gsd_context_path or gsd_required_reads:
        source_of_truth.append("GSD Plan Path and GSD Required Reads define phase-specific execution context.")
    else:
        source_of_truth.append("If no GSD fields are present, fall back to PM task/doc context.")

    return {
        "active_task_source": active_task_source,
        "active_task_id": str(task.get("task_id") or "").strip(),
        "active_task_summary": str(task.get("summary") or "").strip(),
        "task_description_present": bool(description),
        "gsd_contract_present": bool(structured_contract),
        "gsd_plan_path": gsd_plan_path,
        "gsd_context_path": gsd_context_path,
        "gsd_required_reads": gsd_required_reads,
        "required_reads": required_reads,
        "source_of_truth": source_of_truth,
    }


def persist_run_side_effects(
    bundle: dict[str, Any],
    agent_result: dict[str, Any],
    *,
    comment_task_guid: CommentTaskFn,
    append_state_doc: AppendStateFn,
    refresh_context_cache: RefreshContextFn,
    now_text: NowTextFn,
) -> dict[str, Any]:
    texts = extract_text_payloads(agent_result)
    task = effective_task(bundle)
    task_guid = str(task.get("guid") or "").strip()
    task_id = str(task.get("task_id") or "").strip()
    summary_lines = texts[:6]
    joined = "\n".join(summary_lines).strip()
    summary_one_line = joined.replace("\n", " / ") if joined else ""
    comment_result = None
    state_result = None
    if joined:
        comment_body = joined
        if task_id:
            comment_body = f"执行进展 {task_id}：\n" + comment_body
        comment_result = comment_task_guid(task_guid, comment_body)
        state_lines = ["", "", "## PM Run Update", f"- 时间：{now_text()}"]
        if task_id:
            state_lines.append(f"- 任务：{task_id}")
        state_lines.append(f"- 摘要：{summary_one_line}")
        state_md = "\n".join(state_lines)
        state_result = append_state_doc(state_md)
        refresh_context_cache(task_guid=task_guid)
    return {
        "payload_texts": texts,
        "comment_result": comment_result,
        "state_doc_result": state_result,
    }


def persist_dispatch_side_effects(
    bundle: dict[str, Any],
    dispatch_result: dict[str, Any],
    *,
    agent_id: str,
    runtime: str,
    extract_dispatch_ids: ExtractDispatchIdsFn,
    comment_task_guid: CommentTaskFn,
    append_state_doc: AppendStateFn,
    refresh_context_cache: RefreshContextFn,
    now_text: NowTextFn,
) -> dict[str, Any]:
    task = effective_task(bundle)
    task_guid = str(task.get("guid") or "").strip()
    task_id = str(task.get("task_id") or "").strip()
    session_key, run_id = extract_dispatch_ids(dispatch_result)
    status, error = extract_dispatch_status(dispatch_result, session_key=session_key, run_id=run_id)
    failed = status in {"error", "failed"} or bool(error)
    lines = [f"{runtime} {agent_id} 派发失败。"] if failed else [f"已派发 {runtime} {agent_id} 异步执行。"]
    if task_id:
        lines.append(f"任务：{task_id}")
    if error:
        lines.append(f"error: {error}")
    if session_key:
        lines.append(f"session_key: {session_key}")
    if run_id:
        lines.append(f"run_id: {run_id}")
    comment_result = comment_task_guid(task_guid, "\n".join(lines)) if task_guid else None
    state_md = "\n".join([
        "",
        "",
        "## PM Dispatch Update",
        f"- 时间：{now_text()}",
        f"- 状态：{'失败' if failed else '已派发'}",
        f"- runtime：{runtime}",
        f"- agent：{agent_id}",
        *([f"- 任务：{task_id}"] if task_id else []),
        *([f"- error：{error}"] if error else []),
        *([f"- session_key：{session_key}"] if session_key else []),
        *([f"- run_id：{run_id}"] if run_id else []),
    ])
    state_result = append_state_doc(state_md)
    if task_guid:
        refresh_context_cache(task_guid=task_guid)
    return {
        "comment_result": comment_result,
        "state_doc_result": state_result,
        "status": status or ("error" if failed else "accepted"),
        "error": error,
        "session_key": session_key,
        "run_id": run_id,
    }


def build_run_message(bundle: dict[str, Any]) -> str:
    project = bundle.get("project") or {}
    bootstrap = bundle.get("bootstrap") or {}
    current = bundle.get("current_task") or {}
    next_task = bundle.get("next_task") or {}
    contract = bundle.get("handoff_contract") if isinstance(bundle.get("handoff_contract"), dict) else build_coder_handoff_contract(bundle)
    lines = [
        "You are the coder worker for this project.",
        f"Project: {project.get('name') or ''}",
        f"Repo: {project.get('repo_root') or ''}",
        f"Config: {bundle.get('inputs', {}).get('config') or ''}",
        f"Context: {bundle.get('inputs', {}).get('context_path') or ''}",
        f"Bootstrap: {bundle.get('inputs', {}).get('bootstrap_path') or ''}",
        f"Recommended bootstrap action: {bootstrap.get('recommended_action') or ''}",
        f"Project mode: {bootstrap.get('project_mode') or ''}",
    ]
    if current:
        lines.append(f"Current task: {current.get('task_id') or ''} {current.get('summary') or ''}".strip())
    elif next_task:
        lines.append(f"Next task: {next_task.get('task_id') or ''} {next_task.get('summary') or ''}".strip())
    if str(contract.get("active_task_source") or "").strip():
        lines.append(f"Active task source of truth: {contract.get('active_task_source')}")
    for item in bundle.get("recommended_flow") or []:
        lines.append(f"- {item}")
    lines.extend([
        "Read pm.json and .pm/coder-context.json first.",
        "If planning is still fuzzy, read .pm/plan-context.json or .pm/refine-context.json when present.",
        "Treat the structured handoff contract and active task as the execution index card for this run.",
        "Use task/doc as the collaboration surface.",
        "When done, return a concise execution summary with evidence.",
    ])
    for item in contract.get("source_of_truth") or []:
        lines.append(f"Source of truth: {item}")
    gsd_plan_path = str(contract.get("gsd_plan_path") or "").strip()
    gsd_required_reads = [str(item).strip() for item in (contract.get("gsd_required_reads") or []) if str(item).strip()]
    if gsd_plan_path:
        lines.append(f"Read GSD plan first: {gsd_plan_path}")
    if gsd_required_reads:
        lines.append("Read the GSD-required files referenced by the handoff contract before coding.")
    required_reads = [str(item).strip() for item in (contract.get("required_reads") or []) if str(item).strip()]
    if required_reads:
        lines.append("Required reads:")
        lines.extend(f"- {item}" for item in required_reads)
    if gsd_plan_path or gsd_required_reads:
        lines.append("Do not guess the phase context from memory; use the handoff contract and .planning files as source of truth.")
    return "\n".join(str(x) for x in lines if str(x).strip())
