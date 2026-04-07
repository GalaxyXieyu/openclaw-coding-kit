#!/usr/bin/env python3
"""Feishu-first taskflow utilities for project workspaces."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_auth import build_auth_link as build_pm_auth_link
from pm_auth import ensure_attachment_token as ensure_pm_attachment_token
from pm_auth import feishu_credentials as load_feishu_credentials
from pm_auth import get_channel_app_info as get_pm_channel_app_info
from pm_auth import openclaw_config as load_openclaw_config
from pm_auth import request_json as auth_request_json
from pm_auth import request_user_oauth_link as request_pm_user_oauth_link
from pm_bootstrap import bootstrap_task_template as build_bootstrap_task_template
from pm_bootstrap import ensure_bootstrap_task as create_bootstrap_task
from pm_bridge import details_of as bridge_details_of
from pm_bridge import bridge_script_path as resolve_bridge_script_path
from pm_bridge import run_bridge as invoke_bridge
from pm_cli import build_parser as build_pm_parser
from pm_commands import build_command_handlers
from pm_config import ACTIVE_CONFIG
from pm_config import OPENCLAW_CONFIG_PATHS
from pm_config import coder_config
from pm_config import default_config
from pm_config import doc_config
from pm_config import doc_folder_name
from pm_config import doc_titles
from pm_config import ensure_pm_dir
from pm_config import find_openclaw_config_path
from pm_config import load_config
from pm_config import pm_dir_path
from pm_config import pm_file
from pm_config import project_name
from pm_config import project_root_path
from pm_config import repo_root
from pm_config import resolve_config_path
from pm_config import task_kind
from pm_config import task_prefix
from pm_config import tasklist_name
from pm_context import build_coder_context as build_pm_coder_context
from pm_context import build_context_payload as build_pm_context_payload
from pm_context import build_planning_bundle as build_pm_planning_bundle
from pm_context import choose_next_task as choose_pm_next_task
from pm_context import refresh_context_cache as refresh_pm_context_cache
from pm_context import task_brief as build_task_brief
from pm_dispatch import build_run_label as format_run_label
from pm_dispatch import extract_dispatch_ids, spawn_acp_session as dispatch_acp_session
from pm_docs import create_doc as create_project_doc
from pm_docs import create_root_folder as create_project_root_folder
from pm_docs import ensure_project_docs as ensure_pm_docs
from pm_docs import extract_drive_node as extract_project_drive_node
from pm_docs import find_root_folder_by_name as find_project_root_folder_by_name
from pm_docs import update_doc as update_project_doc
from pm_gsd import build_gsd_progress_snapshot
from pm_gsd import build_gsd_route as build_pm_gsd_route
from pm_gsd import build_gsd_task_contract as build_pm_gsd_task_contract
from pm_gsd import build_gsd_task_description as build_pm_gsd_task_description
from pm_gsd import build_gsd_task_hints as build_pm_gsd_task_hints
from pm_gsd import build_gsd_task_summary_body as build_pm_gsd_task_summary_body
from pm_gsd import build_gsd_required_reads as build_pm_gsd_required_reads
from pm_gsd import existing_gsd_reads as load_pm_existing_gsd_reads
from pm_gsd import extract_gsd_task_binding as parse_pm_gsd_task_binding
from pm_gsd import gsd_phase_context_path as build_pm_gsd_phase_context_path
from pm_gsd import list_gsd_phase_plans
from pm_gsd import locate_gsd_doc
from pm_gsd_materializer import materialize_gsd_tasks as materialize_pm_gsd_tasks
from pm_attachments import attachment_auth_result as build_pm_attachment_auth_result
from pm_attachments import list_task_attachments as list_pm_task_attachments
from pm_attachments import task_id_for_output as format_pm_task_id_for_output
from pm_attachments import upload_task_attachments as upload_pm_task_attachments
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
from pm_io import STATE_DIR
from pm_io import load_json_file
from pm_io import now_iso
from pm_io import now_text
from pm_io import remove_file
from pm_io import save_json_file
from pm_io import unix_ts
from pm_io import write_repo_json
from pm_local_backend import create_comment as create_local_task_comment
from pm_local_backend import create_task as create_local_task
from pm_local_backend import add_attachments as add_local_task_attachments
from pm_local_backend import ensure_tasklist as ensure_local_tasklist
from pm_local_backend import get_task_by_guid as get_local_task_by_guid
from pm_local_backend import inspect_tasklist as inspect_local_tasklist
from pm_local_backend import list_attachments as list_local_task_attachments
from pm_local_backend import list_comments as list_local_task_comments
from pm_local_backend import list_tasklist_tasks as list_local_tasklist_tasks
from pm_local_backend import patch_task as patch_local_task
from pm_runtime import resolve_runtime_path
from pm_runtime import run_codex_cli
from pm_runtime import run_openclaw_agent
from pm_scan import build_bootstrap_info
from pm_scan import detect_gsd_assets
from pm_scan import detect_project_mode
from pm_scan import repo_scan
from pm_workspace import build_workspace_profile as build_pm_workspace_profile
from pm_workspace import default_doc_folder_name as build_pm_default_doc_folder_name
from pm_workspace import default_tasklist_name as build_pm_default_tasklist_name
from pm_workspace import english_project_name as resolve_pm_english_project_name
from pm_workspace import project_display_name as resolve_pm_project_display_name
from pm_workspace import project_slug as build_pm_project_slug
from pm_workspace import register_workspace as register_pm_workspace
from pm_workspace import scaffold_workspace as scaffold_pm_workspace
from pm_workspace import default_workspace_root as resolve_pm_default_workspace_root
from pm_worker import build_run_message as build_worker_run_message
from pm_worker import build_coder_handoff_contract as build_worker_handoff_contract
from pm_worker import effective_task as resolve_effective_task
from pm_worker import persist_dispatch_side_effects as persist_worker_dispatch_side_effects
from pm_worker import persist_run_side_effects as persist_worker_run_side_effects

SKILL_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT_CANDIDATES = (
    SKILL_ROOT.parent / "openclaw-lark-bridge" / "scripts" / "invoke_openclaw_tool.py",
    Path.home() / ".codex/skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py",
)
BRIDGE_SCRIPT_ENV_VARS = ("OPENCLAW_LARK_BRIDGE_SCRIPT", "OPENCLAW_BRIDGE_SCRIPT")
TOKEN_PATH = STATE_DIR / "attachment-oauth-token.json"
PENDING_AUTH_PATH = STATE_DIR / "attachment-oauth-pending.json"
DEFAULT_ATTACHMENT_SCOPES = (
    "task:task:read",
    "task:attachment:read",
    "task:attachment:write",
    "offline_access",
)


def _bridge_script_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []
    explicit = resolve_runtime_path(env_vars=BRIDGE_SCRIPT_ENV_VARS)
    if explicit is not None:
        candidates.append(explicit)
    for candidate in BRIDGE_SCRIPT_CANDIDATES:
        expanded = candidate.expanduser()
        if expanded not in candidates:
            candidates.append(expanded)
    return tuple(candidates)


def bridge_script_path() -> Path:
    return resolve_bridge_script_path(_bridge_script_candidates())


def get_channel_app_info() -> dict[str, str]:
    return get_pm_channel_app_info(find_openclaw_config_path)


def build_auth_link(*, scopes: list[str], token_type: str = 'user') -> dict[str, Any]:
    return build_pm_auth_link(find_openclaw_config_path, scopes=scopes, token_type=token_type)


def request_user_oauth_link(*, scopes: list[str]) -> dict[str, Any]:
    return request_pm_user_oauth_link(find_openclaw_config_path, scopes=scopes)


def openclaw_config() -> dict[str, Any]:
    return load_openclaw_config(OPENCLAW_CONFIG_PATHS)


def feishu_credentials() -> dict[str, str]:
    return load_feishu_credentials(OPENCLAW_CONFIG_PATHS)


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any], str]:
    return auth_request_json(url, method=method, headers=headers, form=form, body=body, timeout=timeout)


def ensure_attachment_token(required_scopes: tuple[str, ...] = DEFAULT_ATTACHMENT_SCOPES) -> dict[str, Any]:
    return ensure_pm_attachment_token(
        state_dir=STATE_DIR,
        token_path=TOKEN_PATH,
        pending_auth_path=PENDING_AUTH_PATH,
        required_scopes=required_scopes,
        config_paths=OPENCLAW_CONFIG_PATHS,
    )


def task_backend_name() -> str:
    task_cfg = ACTIVE_CONFIG.get("task") if isinstance(ACTIVE_CONFIG.get("task"), dict) else {}
    return str(task_cfg.get("backend") or default_config()["task"]["backend"]).strip() or "feishu"


def doc_backend_name() -> str:
    doc_cfg = ACTIVE_CONFIG.get("doc") if isinstance(ACTIVE_CONFIG.get("doc"), dict) else {}
    return str(doc_cfg.get("backend") or default_config()["doc"]["backend"]).strip() or "feishu"


def gsd_bindings_path() -> Path:
    return pm_file("gsd-task-bindings.json")


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


def ensure_task_started(task: dict[str, Any]) -> Optional[dict[str, Any]]:
    if task_backend_name() == "local":
        if str(task.get("guid") or "").strip() and not str(((task.get("start") or {}).get("timestamp") or "")).strip():
            return patch_local_task(str(task.get("guid") or "").strip(), {"start": {"timestamp": now_iso(), "is_all_day": False}})
        return None
    return ensure_pm_task_started(task, run_bridge=run_bridge, now_iso=now_iso)


def task_id_for_output(task_id: str) -> str:
    return format_pm_task_id_for_output(task_id, normalize_task_key_fn=normalize_task_key)


def run_bridge(
    tool: str,
    action: str,
    args: dict[str, Any] | None = None,
    *,
    session_key: str = "",
    message_channel: str = "",
    account_id: str = "",
    message_to: str = "",
    thread_id: str = "",
) -> dict[str, Any]:
    return invoke_bridge(
        _bridge_script_candidates(),
        tool,
        action,
        args,
        session_key=session_key,
        message_channel=message_channel,
        account_id=account_id,
        message_to=message_to,
        thread_id=thread_id,
    )


def details_of(payload: dict[str, Any]) -> dict[str, Any]:
    return bridge_details_of(payload)


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


def build_run_label(root: Path, agent_id: str, task_id: str) -> str:
    return format_run_label(root, agent_id, task_id)


def spawn_acp_session(
    *,
    agent_id: str,
    message: str,
    cwd: str,
    timeout_seconds: int = 900,
    thinking: str = "high",
    label: str = "",
    session_key: str = "main",
) -> dict[str, Any]:
    return dispatch_acp_session(
        run_bridge,
        agent_id=agent_id,
        message=message,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        thinking=thinking,
        label=label,
        session_key=session_key,
    )


def sanitize_feishu_markdown(text: str) -> str:
    raw = str(text or "")
    if not raw.strip():
        return ""

    def replace_link(match: re.Match[str]) -> str:
        label = str(match.group(1) or "").strip()
        target = str(match.group(2) or "").strip()
        lowered = target.lower()
        if lowered.startswith(("http://", "https://", "applink://", "#")):
            return match.group(0)
        if label:
            return f"`{label}`"
        return target

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, raw)


def create_task(
    *,
    summary: str,
    description: str,
    tasklists: list[dict[str, Any]] | None = None,
    current_user_id: str = "",
    gsd_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if task_backend_name() == "local":
        return create_local_task(
            summary=summary,
            description=description,
            tasklists=tasklists,
            current_user_id=current_user_id,
            gsd_contract=gsd_contract,
        )
    create_args: dict[str, Any] = {
        "summary": summary,
        "description": description,
        "tasklists": [item for item in (tasklists or []) if isinstance(item, dict)],
    }
    if current_user_id:
        create_args["current_user_id"] = current_user_id
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


def persist_run_side_effects(bundle: dict[str, Any], agent_result: dict[str, Any]) -> dict[str, Any]:
    return persist_worker_run_side_effects(
        bundle,
        agent_result,
        comment_task_guid=comment_task_guid,
        append_state_doc=append_state_doc,
        refresh_context_cache=refresh_context_cache,
        now_text=now_text,
    )


def persist_dispatch_side_effects(bundle: dict[str, Any], dispatch_result: dict[str, Any], *, agent_id: str, runtime: str) -> dict[str, Any]:
    return persist_worker_dispatch_side_effects(
        bundle,
        dispatch_result,
        agent_id=agent_id,
        runtime=runtime,
        extract_dispatch_ids=extract_dispatch_ids,
        comment_task_guid=comment_task_guid,
        append_state_doc=append_state_doc,
        refresh_context_cache=refresh_context_cache,
        now_text=now_text,
    )


def build_run_message(bundle: dict[str, Any]) -> str:
    return build_worker_run_message(bundle)


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


def extract_gsd_task_binding(description: str) -> dict[str, str]:
    return parse_pm_gsd_task_binding(description)


def build_gsd_task_summary_body(plan: dict[str, Any]) -> str:
    return build_pm_gsd_task_summary_body(plan)


def gsd_phase_context_path(phase_dir: str, phase: str) -> str:
    return build_pm_gsd_phase_context_path(phase_dir, phase)


def existing_gsd_reads(root: Path, paths: list[str]) -> list[str]:
    return load_pm_existing_gsd_reads(root, paths)


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
    resolved_task_guid = str(task_guid or "").strip()
    if not resolved_task_guid and str(task_id or "").strip():
        task = get_task_record(task_id, include_completed=include_completed)
        resolved_task_guid = str(task.get("guid") or "").strip()

    selected_phase_input = str(phase or "").strip()
    route = route_gsd_work(root, phase=selected_phase_input, prefer_pm_tasks=True)
    force_replan = any(
        (
            bool(research),
            bool(skip_research),
            bool(gaps),
            bool(skip_verify),
            bool(reviews),
            bool(str(prd or "").strip()),
        )
    )

    planning = None
    if str(route.get("route") or "") != "materialize-tasks" or force_replan:
        planning = execute_gsd_plan_phase(
            root=root,
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
    progress_sync = None
    if sync_progress:
        progress_sync = sync_gsd_progress(
            root=root,
            phase=materialized_phase,
            task_guid=resolved_task_guid,
            append_to_state=append_state,
        )
    refreshed = refresh_context_cache()
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
        "context_path": str(pm_file("current-context.json", str(root))),
        "doc_index": refreshed.get("doc_index") or {},
        "gsd": refreshed.get("gsd") or {},
    }


def task_brief(item: dict[str, Any]) -> dict[str, Any]:
    return build_task_brief(item, parse_task_summary=parse_task_summary)


def choose_next_task(open_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    return choose_pm_next_task(open_rows, extract_task_number=extract_task_number)


def build_context_payload(*, selected_task: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = build_pm_context_payload(
        selected_task=selected_task,
        active_config=ACTIVE_CONFIG,
        project_root_path=project_root_path,
        ensure_tasklist=ensure_tasklist,
        task_pool=task_pool,
        extract_task_number=extract_task_number,
        get_task_record_by_guid=get_task_record_by_guid,
        list_task_comments=list_task_comments,
        project_name=project_name,
        tasklist_name=tasklist_name,
        task_prefix=task_prefix,
        task_kind=task_kind,
        repo_scan=repo_scan,
        build_bootstrap_info=build_bootstrap_info,
        detect_gsd_assets=detect_gsd_assets,
        parse_task_summary=parse_task_summary,
        parse_task_id_from_description=parse_task_id_from_description,
        now_iso=now_iso,
    )
    payload["gsd_route"] = route_gsd_work(project_root_path(), prefer_pm_tasks=True)
    return attach_gsd_contracts(payload)


def refresh_context_cache(*, task_id: str = "", task_guid: str = "") -> dict[str, Any]:
    return refresh_pm_context_cache(
        task_id=task_id,
        task_guid=task_guid,
        build_context_payload_fn=build_context_payload,
        get_task_record_by_guid=get_task_record_by_guid,
        get_task_record=get_task_record,
        pm_file=pm_file,
        write_repo_json=write_repo_json,
    )


def write_pm_bundle(name: str, payload: dict[str, Any]) -> Path:
    path = pm_file(name)
    write_repo_json(path, payload)
    return path


def build_planning_bundle(mode: str, *, task_id: str = "", task_guid: str = "", focus: str = "") -> tuple[dict[str, Any], Path]:
    return build_pm_planning_bundle(
        mode,
        task_id=task_id,
        task_guid=task_guid,
        focus=focus,
        refresh_context_cache_fn=refresh_context_cache,
        now_iso=now_iso,
        write_pm_bundle=write_pm_bundle,
    )


def build_coder_context(*, task_id: str = "", task_guid: str = "") -> tuple[dict[str, Any], Path]:
    payload, path = build_pm_coder_context(
        task_id=task_id,
        task_guid=task_guid,
        refresh_context_cache_fn=refresh_context_cache,
        now_iso=now_iso,
        active_config=ACTIVE_CONFIG,
        pm_file=pm_file,
        write_pm_bundle=write_pm_bundle,
    )
    handoff_contract = build_worker_handoff_contract(payload)
    payload["handoff_contract"] = handoff_contract
    payload["required_reads"] = [str(item).strip() for item in (handoff_contract.get("required_reads") or []) if str(item).strip()]
    payload["source_of_truth"] = [str(item).strip() for item in (handoff_contract.get("source_of_truth") or []) if str(item).strip()]
    path = write_pm_bundle("coder-context.json", payload)
    return payload, path


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


def english_project_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return resolve_pm_english_project_name(project_name, english_name, agent_id)


def project_slug(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return build_pm_project_slug(project_name, english_name, agent_id)


def project_display_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return resolve_pm_project_display_name(project_name, english_name, agent_id)


def default_tasklist_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return build_pm_default_tasklist_name(project_name, english_name, agent_id)


def default_doc_folder_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return build_pm_default_doc_folder_name(project_name, english_name, agent_id)


def resolve_openclaw_config_path(explicit: str = "") -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    found = find_openclaw_config_path()
    if not found:
        raise SystemExit("openclaw.json not found; provide --openclaw-config")
    return found.resolve()


def resolve_workspace_root(*, openclaw_config_path: Path, agent_id: str, explicit: str = "") -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    config = load_json_file(openclaw_config_path)
    return resolve_pm_default_workspace_root(config, agent_id, openclaw_config_path)


def build_workspace_profile(
    *,
    project_name: str,
    english_name: str,
    agent_id: str,
    channel: str,
    group_id: str,
    repo_root: Path,
    workspace_root: Path,
    tasklist_name: str,
    doc_folder_name: str,
    task_prefix: str,
    default_worker: str,
    reviewer_worker: str,
    task_backend_type: str = "feishu-task",
) -> dict[str, Any]:
    return build_pm_workspace_profile(
        project_name=project_name,
        english_name=english_name,
        agent_id=agent_id,
        channel=channel,
        group_id=group_id,
        repo_root=repo_root,
        workspace_root=workspace_root,
        tasklist_name=tasklist_name,
        doc_folder_name=doc_folder_name,
        task_prefix=task_prefix,
        default_worker=default_worker,
        reviewer_worker=reviewer_worker,
        task_backend_type=task_backend_type,
    )


def scaffold_workspace(*, output: Path, profile: dict[str, Any], force: bool = False, dry_run: bool = False) -> dict[str, Any]:
    return scaffold_pm_workspace(output=output, profile=profile, force=force, dry_run=dry_run)


def register_workspace(
    *,
    config_path: Path,
    agent_id: str,
    workspace_root: Path,
    group_id: str,
    channel: str,
    skills: list[str],
    allow_agents: list[str],
    model_primary: str = "",
    replace_binding: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    return register_pm_workspace(
        config_path=config_path,
        agent_id=agent_id,
        workspace_root=workspace_root,
        group_id=group_id,
        channel=channel,
        skills=skills,
        allow_agents=allow_agents,
        model_primary=model_primary,
        replace_binding=replace_binding,
        dry_run=dry_run,
    )


def build_cli_api() -> SimpleNamespace:
    return SimpleNamespace(
        ACTIVE_CONFIG=ACTIVE_CONFIG,
        attachment_auth_result=attachment_auth_result,
        build_auth_link=build_auth_link,
        build_coder_context=build_coder_context,
        build_completion_comment=build_completion_comment,
        build_context_payload=build_context_payload,
        build_description=build_description,
        build_planning_bundle=build_planning_bundle,
        build_run_label=build_run_label,
        build_run_message=build_run_message,
        build_workspace_profile=build_workspace_profile,
        coder_config=coder_config,
        create_task=create_task,
        create_task_comment=create_task_comment,
        current_head_commit_url=current_head_commit_url,
        default_config=default_config,
        default_doc_folder_name=default_doc_folder_name,
        default_tasklist_name=default_tasklist_name,
        details_of=details_of,
        english_project_name=english_project_name,
        execute_gsd_plan_phase=execute_gsd_plan_phase,
        ensure_bootstrap_task=ensure_bootstrap_task,
        ensure_pm_dir=ensure_pm_dir,
        ensure_project_docs=ensure_project_docs,
        ensure_task_started=ensure_task_started,
        ensure_tasklist=ensure_tasklist,
        extract_task_number=extract_task_number,
        feishu_credentials=feishu_credentials,
        find_existing_task_by_summary=find_existing_task_by_summary,
        get_task_record=get_task_record,
        get_task_record_by_guid=get_task_record_by_guid,
        inspect_tasklist=inspect_tasklist,
        list_task_comments=list_task_comments,
        list_task_attachments=list_task_attachments,
        load_config=load_config,
        load_json_file=load_json_file,
        materialize_gsd_tasks=materialize_gsd_tasks,
        next_task_id=next_task_id,
        normalize_task_titles=normalize_task_titles,
        normalize_task_key=normalize_task_key,
        now_iso=now_iso,
        parse_task_summary=parse_task_summary,
        plan_gsd_phase_workflow=plan_gsd_phase_workflow,
        persist_dispatch_side_effects=persist_dispatch_side_effects,
        persist_run_side_effects=persist_run_side_effects,
        patch_task=patch_task,
        pm_dir_path=pm_dir_path,
        pm_file=pm_file,
        project_display_name=project_display_name,
        project_slug=project_slug,
        project_root_path=project_root_path,
        refresh_context_cache=refresh_context_cache,
        register_workspace=register_workspace,
        request_json=request_json,
        request_user_oauth_link=request_user_oauth_link,
        resolve_config_path=resolve_config_path,
        resolve_effective_task=resolve_effective_task,
        resolve_openclaw_config_path=resolve_openclaw_config_path,
        resolve_optional_text_input=resolve_optional_text_input,
        resolve_text_input=resolve_text_input,
        resolve_workspace_root=resolve_workspace_root,
        run_bridge=run_bridge,
        run_codex_cli=run_codex_cli,
        run_openclaw_agent=run_openclaw_agent,
        route_gsd_work=route_gsd_work,
        scaffold_workspace=scaffold_workspace,
        sync_gsd_docs=sync_gsd_docs,
        sync_gsd_progress=sync_gsd_progress,
        spawn_acp_session=spawn_acp_session,
        task_id_for_output=task_id_for_output,
        task_kind=task_kind,
        task_pool=task_pool,
        task_prefix=task_prefix,
        tasklist_name=tasklist_name,
        upload_task_attachments=upload_task_attachments,
        write_pm_bundle=write_pm_bundle,
    )


def build_parser():
    handlers = build_command_handlers(build_cli_api())
    return build_pm_parser(handlers=handlers)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    command_name = str(getattr(args, "command", "") or "")
    ACTIVE_CONFIG.clear()
    ACTIVE_CONFIG.update(load_config(args.config))
    if hasattr(args, "repo_root") and not getattr(args, "repo_root", ""):
        args.repo_root = repo_root()
    if hasattr(args, "kind") and not getattr(args, "kind", ""):
        args.kind = task_kind()
    if command_name not in {"init", "workspace-init"} and hasattr(args, "tasklist_name") and not getattr(args, "tasklist_name", ""):
        args.tasklist_name = tasklist_name()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
