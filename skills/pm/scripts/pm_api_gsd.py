from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_config import ACTIVE_CONFIG
from pm_config import coder_config
from pm_config import doc_config
from pm_config import doc_folder_name
from pm_config import doc_titles
from pm_config import pm_file
from pm_config import project_name
from pm_config import project_root_path
from pm_config import task_prefix
from pm_docs import create_doc as create_project_doc
from pm_docs import create_root_folder as create_project_root_folder
from pm_docs import ensure_project_docs as ensure_pm_docs
from pm_docs import extract_drive_node as extract_project_drive_node
from pm_docs import find_root_folder_by_name as find_project_root_folder_by_name
from pm_docs import update_doc as update_project_doc
from pm_gsd import build_gsd_progress_snapshot
from pm_gsd import build_gsd_required_reads as build_pm_gsd_required_reads
from pm_gsd import build_gsd_route as build_pm_gsd_route
from pm_gsd import build_gsd_task_contract as build_pm_gsd_task_contract
from pm_gsd import build_gsd_task_description as build_pm_gsd_task_description
from pm_gsd import build_gsd_task_hints as build_pm_gsd_task_hints
from pm_gsd import build_gsd_task_summary_body as build_pm_gsd_task_summary_body
from pm_gsd import existing_gsd_reads as load_pm_existing_gsd_reads
from pm_gsd import extract_gsd_task_binding as parse_pm_gsd_task_binding
from pm_gsd import gsd_phase_context_path as build_pm_gsd_phase_context_path
from pm_gsd import list_gsd_phase_plans
from pm_gsd import locate_gsd_doc
from pm_gsd_materializer import materialize_gsd_tasks as materialize_pm_gsd_tasks
from pm_io import load_json_file
from pm_io import now_iso
from pm_io import write_repo_json
from pm_runtime import run_openclaw_agent
from pm_scan import build_bootstrap_info
from pm_scan import detect_project_mode

from pm_api_support import details_of
from pm_api_support import doc_backend_name
from pm_api_support import gsd_bindings_path
from pm_api_support import run_bridge
from pm_api_support import sanitize_feishu_markdown
from pm_api_tasks import build_completion_changes
from pm_api_tasks import build_normalized_summary_from_text
from pm_api_tasks import create_task
from pm_api_tasks import create_task_comment
from pm_api_tasks import ensure_tasklist
from pm_api_tasks import extract_task_number
from pm_api_tasks import get_task_record
from pm_api_tasks import get_task_record_by_guid
from pm_api_tasks import parse_task_id_from_description
from pm_api_tasks import parse_task_summary
from pm_api_tasks import patch_task
from pm_api_tasks import task_pool


def _repo_doc_paths(root: Path) -> dict[str, Path]:
    planning_root = root / ".planning"
    return {
        "project": planning_root / "PROJECT.md",
        "requirements": planning_root / "REQUIREMENTS.md",
        "roadmap": planning_root / "ROADMAP.md",
        "state": planning_root / "STATE.md",
    }


def load_gsd_binding_index() -> dict[str, Any]:
    payload = load_json_file(gsd_bindings_path())
    return payload if isinstance(payload, dict) else {"bindings": []}


def extract_gsd_task_binding(description: str) -> dict[str, str]:
    return parse_pm_gsd_task_binding(description)


def gsd_phase_context_path(phase_dir: str, phase: str) -> str:
    return build_pm_gsd_phase_context_path(phase_dir, phase)


def existing_gsd_reads(root: Path, paths: list[str]) -> list[str]:
    return load_pm_existing_gsd_reads(root, paths)


def resolve_task_gsd_contract(task: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(task, dict) or not task:
        return {}
    embedded = task.get("gsd_contract")
    if isinstance(embedded, dict) and embedded:
        return embedded
    task_guid = str(task.get("guid") or "").strip()
    task_id = str(task.get("task_id") or "").strip()
    for item in load_gsd_binding_index().get("bindings") or []:
        if not isinstance(item, dict):
            continue
        if task_guid and str(item.get("task_guid") or "").strip() == task_guid:
            contract = item.get("contract")
            return contract if isinstance(contract, dict) else {}
        if task_id and str(item.get("task_id") or "").strip() == task_id:
            contract = item.get("contract")
            return contract if isinstance(contract, dict) else {}
    binding = extract_gsd_task_binding(str(task.get("description") or ""))
    if not any(str(value or "").strip() for value in binding.values()):
        return {}
    return {
        "source": str(binding.get("source") or "").strip(),
        "phase": str(binding.get("phase") or "").strip(),
        "plan_id": str(binding.get("plan_id") or "").strip(),
        "plan_path": str(binding.get("plan_path") or "").strip(),
        "summary_path": str(binding.get("summary_path") or "").strip(),
        "context_path": str(binding.get("context_path") or "").strip(),
        "recommended_mode": str(binding.get("recommended_mode") or "").strip(),
        "required_reads": existing_gsd_reads(
            project_root_path(),
            [
                str(binding.get("plan_path") or "").strip(),
                str(binding.get("context_path") or "").strip(),
                ".planning/STATE.md",
                ".planning/ROADMAP.md",
                ".planning/REQUIREMENTS.md",
                ".planning/PROJECT.md",
            ],
        ),
    }


def attach_gsd_contracts(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("current_task", "next_task"):
        item = payload.get(key)
        if not isinstance(item, dict) or not item:
            continue
        contract = resolve_task_gsd_contract(item)
        if isinstance(contract, dict) and contract:
            item["gsd_contract"] = contract
    return payload


def find_root_folder_by_name(name: str) -> dict[str, Any] | None:
    return find_project_root_folder_by_name(run_bridge, details_of, name)


def extract_drive_node(payload: dict[str, Any]) -> dict[str, Any]:
    return extract_project_drive_node(details_of, payload)


def create_root_folder(name: str) -> dict[str, Any]:
    return create_project_root_folder(run_bridge, details_of, name)


def create_doc(title: str, markdown: str, *, folder_token: str = "") -> dict[str, Any]:
    return create_project_doc(run_bridge, details_of, title, markdown, folder_token=folder_token)


def update_doc(doc_id: str, markdown: str, *, mode: str = "overwrite", new_title: str = "") -> dict[str, Any]:
    return update_project_doc(run_bridge, details_of, doc_id, markdown, mode=mode, new_title=new_title)


def append_state_doc(markdown: str) -> dict[str, Any] | None:
    cleaned = sanitize_feishu_markdown(markdown)
    if not cleaned.strip():
        return None
    if doc_backend_name() == "repo":
        state_path = _repo_doc_paths(project_root_path())["state"]
        state_path.parent.mkdir(parents=True, exist_ok=True)
        existing = state_path.read_text(encoding="utf-8") if state_path.exists() else "# STATE\n"
        separator = "" if existing.endswith("\n") else "\n"
        state_path.write_text(existing + separator + cleaned + "\n", encoding="utf-8")
        return {"status": "repo_local_appended", "path": str(state_path)}
    doc = doc_config()
    doc_id = str(doc.get("state_doc_url") or doc.get("state_doc_token") or "").strip()
    if not doc_id:
        return None
    payload = run_bridge("feishu_update_doc", "", {"doc_id": doc_id, "mode": "append", "markdown": cleaned})
    return details_of(payload)


def comment_task_guid(task_guid: str, content: str) -> dict[str, Any] | None:
    return create_task_comment(task_guid, content)


def ensure_project_docs(root: Path, *, dry_run: bool = False) -> dict[str, Any]:
    if doc_backend_name() == "repo":
        bootstrap = build_bootstrap_info(root)
        titles = doc_titles()
        paths = _repo_doc_paths(root)
        if not dry_run:
            paths["project"].parent.mkdir(parents=True, exist_ok=True)
            defaults = {
                "project": f"# {project_name()}\n\n- 仓库：`{root}`\n- 项目模式：{bootstrap.get('project_mode') or detect_project_mode(root)}\n",
                "requirements": f"# {project_name()} REQUIREMENTS\n",
                "roadmap": f"# {project_name()} ROADMAP\n",
                "state": f"# {project_name()} STATE\n",
            }
            for key, path in paths.items():
                if not path.exists():
                    path.write_text(defaults[key], encoding="utf-8")
        docs = {
            "dry_run": dry_run,
            "folder_name": str(root / ".planning"),
            "folder_token": "",
            "folder_url": str(root / ".planning"),
            "folder_created": False,
            "folder_status": "repo_local",
            **titles,
            "project_doc_token": "",
            "requirements_doc_token": "",
            "roadmap_doc_token": "",
            "state_doc_token": "",
            "project_doc_url": str(paths["project"]),
            "requirements_doc_url": str(paths["requirements"]),
            "roadmap_doc_url": str(paths["roadmap"]),
            "state_doc_url": str(paths["state"]),
            "project_doc_status": "repo_local",
            "requirements_doc_status": "repo_local",
            "roadmap_doc_status": "repo_local",
            "state_doc_status": "repo_local",
        }
        ACTIVE_CONFIG.setdefault("doc", {})
        if isinstance(ACTIVE_CONFIG.get("doc"), dict):
            ACTIVE_CONFIG["doc"].update(docs)
        return docs
    bootstrap = build_bootstrap_info(root)
    docs = ensure_pm_docs(
        run_bridge,
        details_of,
        root=root,
        cfg=doc_config(),
        folder_name=doc_folder_name(),
        titles=doc_titles(),
        project_name=project_name(),
        project_mode=str(bootstrap.get("project_mode") or detect_project_mode(root)),
        bootstrap_action=str(bootstrap.get("recommended_action") or ""),
        dry_run=dry_run,
    )
    ACTIVE_CONFIG.setdefault("doc", {})
    if isinstance(ACTIVE_CONFIG.get("doc"), dict):
        ACTIVE_CONFIG["doc"].update(docs)
    return docs


def sync_gsd_docs(*, root: Path, include: list[str] | None = None) -> dict[str, Any]:
    if doc_backend_name() == "repo":
        docs = ensure_project_docs(root)
        include_set = {item.strip().lower() for item in (include or ["project", "requirements", "roadmap", "state"]) if item.strip()}
        results: dict[str, Any] = {}
        for name in ("project", "requirements", "roadmap", "state"):
            if name not in include_set:
                continue
            source = locate_gsd_doc(root, f"{name.upper()}.md")
            target = _repo_doc_paths(root)[name]
            results[name] = {
                "status": "repo_local" if source and source == target else "missing_source",
                "source_path": str(source) if source else str(target),
                "doc_id": str(target),
            }
        return {"repo_root": str(root), "docs": results, "doc_backend": "repo", "doc_index": docs}
    docs = ensure_project_docs(root)
    titles = doc_titles()
    include_set = {item.strip().lower() for item in (include or ["project", "requirements", "roadmap", "state"]) if item.strip()}
    results: dict[str, Any] = {}
    for name in ("project", "requirements", "roadmap", "state"):
        if name not in include_set:
            continue
        source = locate_gsd_doc(root, f"{name.upper()}.md")
        doc_id = str(docs.get(f"{name}_doc_url") or docs.get(f"{name}_doc_token") or "").strip()
        if source is None:
            results[name] = {
                "status": "missing_source",
                "source_path": str(root / ".planning" / f"{name.upper()}.md"),
            }
            continue
        if not doc_id:
            results[name] = {
                "status": "missing_target",
                "source_path": str(source),
            }
            continue
        markdown = source.read_text(encoding="utf-8")
        result = update_doc(doc_id, markdown, mode="overwrite", new_title=titles[name])
        results[name] = {
            "status": "synced",
            "source_path": str(source),
            "doc_id": doc_id,
            "result": result,
        }
    return {
        "repo_root": str(root),
        "docs": results,
    }


def sync_gsd_progress(*, root: Path, phase: str = "", task_guid: str = "", append_to_state: bool = True) -> dict[str, Any]:
    snapshot = build_gsd_progress_snapshot(root, phase=phase)
    markdown = str(snapshot.get("markdown") or "").strip()
    state_append_result = None
    task_comment_result = None
    if append_to_state and markdown:
        state_append_result = append_state_doc("\n\n" + markdown)
    if task_guid.strip() and markdown:
        task_comment_result = comment_task_guid(task_guid, markdown)
    return {
        "repo_root": str(root),
        "phase": snapshot.get("phase") or "",
        "snapshot": snapshot,
        "state_append_result": state_append_result,
        "task_comment_result": task_comment_result,
    }


def build_gsd_task_summary_body(plan: dict[str, Any]) -> str:
    return build_pm_gsd_task_summary_body(plan)


def build_gsd_required_reads(root: Path, plan: dict[str, Any]) -> list[str]:
    return build_pm_gsd_required_reads(root, plan)


def build_gsd_task_hints(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    return build_pm_gsd_task_hints(root, plan)


def route_gsd_work(root: Path, *, phase: str = "", prefer_pm_tasks: bool = True) -> dict[str, Any]:
    project_mode = detect_project_mode(root)
    return build_pm_gsd_route(
        root,
        phase=phase,
        prefer_pm_tasks=prefer_pm_tasks,
        project_mode=project_mode,
    )


def build_gsd_task_description(task_id: str, plan: dict[str, Any], *, repo_root: Path) -> str:
    return build_pm_gsd_task_description(task_id, plan, repo_root=repo_root)


def materialize_gsd_tasks(*, root: Path, phase: str = "") -> dict[str, Any]:
    phase_payload = list_gsd_phase_plans(root, phase=phase)
    return materialize_pm_gsd_tasks(
        root=root,
        phase_payload=phase_payload,
        ensure_tasklist=ensure_tasklist,
        task_pool=task_pool,
        get_task_record_by_guid=get_task_record_by_guid,
        extract_task_number=extract_task_number,
        parse_task_summary=parse_task_summary,
        parse_task_id_from_description=parse_task_id_from_description,
        extract_gsd_task_binding=extract_gsd_task_binding,
        task_prefix=task_prefix,
        build_normalized_summary_from_text=build_normalized_summary_from_text,
        build_gsd_task_summary_body=build_gsd_task_summary_body,
        build_gsd_task_description=lambda task_id, plan, repo_root: build_gsd_task_description(task_id, plan, repo_root=repo_root),
        build_gsd_task_contract=build_pm_gsd_task_contract,
        create_task=create_task,
        patch_task=patch_task,
        build_completion_changes=lambda task, completed_at: build_completion_changes(task, completed_at=completed_at),
        now_iso=now_iso,
        binding_index_path=gsd_bindings_path(),
        write_repo_json=write_repo_json,
    )


def build_gsd_plan_phase_message(
    *,
    phase: str = "",
    research: bool = False,
    skip_research: bool = False,
    gaps: bool = False,
    skip_verify: bool = False,
    prd: str = "",
    reviews: bool = False,
) -> str:
    parts = ["$gsd-plan-phase"]
    if str(phase or "").strip():
        parts.append(str(phase).strip())
    if research:
        parts.append("--research")
    if skip_research:
        parts.append("--skip-research")
    if gaps:
        parts.append("--gaps")
    if skip_verify:
        parts.append("--skip-verify")
    if str(prd or "").strip():
        parts.extend(["--prd", str(prd).strip()])
    if reviews:
        parts.append("--reviews")
    parts.append("--text")
    return " ".join(parts)


def execute_gsd_plan_phase(
    *,
    root: Path,
    phase: str = "",
    agent_id: str = "",
    timeout_seconds: int = 0,
    thinking: str = "",
    research: bool = False,
    skip_research: bool = False,
    gaps: bool = False,
    skip_verify: bool = False,
    prd: str = "",
    reviews: bool = False,
) -> dict[str, Any]:
    project = ACTIVE_CONFIG.get("project") if isinstance(ACTIVE_CONFIG.get("project"), dict) else {}
    coder = coder_config()
    project_agent_id = str(project.get("agent") or "").strip()
    resolved_agent_id = str(agent_id or project_agent_id or "main").strip() or "main"
    resolved_timeout = int(timeout_seconds or coder.get("timeout") or 1800)
    resolved_thinking = str(thinking or coder.get("thinking") or "high").strip() or "high"
    message = build_gsd_plan_phase_message(
        phase=phase,
        research=research,
        skip_research=skip_research,
        gaps=gaps,
        skip_verify=skip_verify,
        prd=prd,
        reviews=reviews,
    )
    result = run_openclaw_agent(
        agent_id=resolved_agent_id,
        message=message,
        cwd=str(root),
        timeout_seconds=resolved_timeout,
        thinking=resolved_thinking,
    )
    snapshot = build_gsd_progress_snapshot(root, phase=phase)
    return {
        "backend": "openclaw",
        "agent_id": resolved_agent_id,
        "project_agent_id": project_agent_id,
        "coder_agent_id": str(coder.get("agent_id") or "").strip(),
        "timeout": resolved_timeout,
        "thinking": resolved_thinking,
        "message": message,
        "result": result,
        "phase": str(snapshot.get("phase") or phase or "").strip(),
        "snapshot": snapshot,
    }


def resolve_workflow_task_guid(task_id: str, task_guid: str, *, include_completed: bool = False) -> str:
    resolved_task_guid = str(task_guid or "").strip()
    if resolved_task_guid or not str(task_id or "").strip():
        return resolved_task_guid
    task = get_task_record(task_id, include_completed=include_completed)
    return str(task.get("guid") or "").strip()


def workflow_force_replan(
    *,
    research: bool = False,
    skip_research: bool = False,
    gaps: bool = False,
    skip_verify: bool = False,
    prd: str = "",
    reviews: bool = False,
) -> bool:
    return any(
        (
            bool(research),
            bool(skip_research),
            bool(gaps),
            bool(skip_verify),
            bool(reviews),
            bool(str(prd or "").strip()),
        )
    )


def maybe_execute_phase_planning(
    *,
    root: Path,
    route: dict[str, Any],
    phase: str = "",
    agent_id: str = "",
    timeout_seconds: int = 0,
    thinking: str = "",
    research: bool = False,
    skip_research: bool = False,
    gaps: bool = False,
    skip_verify: bool = False,
    prd: str = "",
    reviews: bool = False,
) -> dict[str, Any] | None:
    force_replan = workflow_force_replan(
        research=research,
        skip_research=skip_research,
        gaps=gaps,
        skip_verify=skip_verify,
        prd=prd,
        reviews=reviews,
    )
    if str(route.get("route") or "") == "materialize-tasks" and not force_replan:
        return None
    return execute_gsd_plan_phase(
        root=root,
        phase=phase,
        agent_id=agent_id,
        timeout_seconds=timeout_seconds,
        thinking=thinking,
        research=research,
        skip_research=skip_research,
        gaps=gaps,
        skip_verify=skip_verify,
        prd=prd,
        reviews=reviews,
    )


def maybe_sync_gsd_progress(
    *,
    root: Path,
    phase: str,
    task_guid: str,
    sync_progress: bool,
    append_state: bool,
) -> dict[str, Any] | None:
    if not sync_progress:
        return None
    return sync_gsd_progress(
        root=root,
        phase=phase,
        task_guid=task_guid,
        append_to_state=append_state,
    )


def refresh_gsd_workflow_context(root: Path) -> dict[str, Any]:
    from pm_api_context import refresh_context_cache

    refreshed = refresh_context_cache()
    return {
        "context_path": str(pm_file("current-context.json", str(root))),
        "doc_index": refreshed.get("doc_index") or {},
        "gsd": refreshed.get("gsd") or {},
    }


def plan_gsd_phase_workflow(
    *,
    root: Path,
    phase: str = "",
    task_id: str = "",
    task_guid: str = "",
    include_completed: bool = False,
    agent_id: str = "",
    timeout_seconds: int = 0,
    thinking: str = "",
    research: bool = False,
    skip_research: bool = False,
    gaps: bool = False,
    skip_verify: bool = False,
    prd: str = "",
    reviews: bool = False,
    sync_docs: bool = True,
    sync_progress: bool = True,
    append_state: bool = True,
) -> dict[str, Any]:
    resolved_task_guid = resolve_workflow_task_guid(task_id, task_guid, include_completed=include_completed)
    selected_phase_input = str(phase or "").strip()
    route = route_gsd_work(root, phase=selected_phase_input, prefer_pm_tasks=True)
    planning = maybe_execute_phase_planning(
        root=root,
        route=route,
        phase=selected_phase_input,
        agent_id=agent_id,
        timeout_seconds=timeout_seconds,
        thinking=thinking,
        research=research,
        skip_research=skip_research,
        gaps=gaps,
        skip_verify=skip_verify,
        prd=prd,
        reviews=reviews,
    )
    selected_phase = str((planning or {}).get("phase") or route.get("phase") or selected_phase_input).strip()
    docs_sync = sync_gsd_docs(root=root) if sync_docs else None
    materialization = materialize_gsd_tasks(root=root, phase=selected_phase)
    materialized_phase = str(materialization.get("phase") or selected_phase).strip()
    progress_sync = maybe_sync_gsd_progress(
        root=root,
        phase=materialized_phase,
        task_guid=resolved_task_guid,
        sync_progress=sync_progress,
        append_state=append_state,
    )
    return {
        "status": "planned" if planning else "routed",
        "repo_root": str(root),
        "phase": materialized_phase,
        "route": route,
        "planning": planning,
        "docs_sync": docs_sync,
        "task_materialization": materialization,
        "progress_sync": progress_sync,
        "task_guid": resolved_task_guid,
        **refresh_gsd_workflow_context(root),
    }
