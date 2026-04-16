from __future__ import annotations

from types import SimpleNamespace

from pm_config import ACTIVE_CONFIG
from pm_config import coder_config
from pm_config import default_config
from pm_config import ensure_pm_dir
from pm_config import load_config
from pm_config import pm_dir_path
from pm_config import pm_file
from pm_config import project_root_path
from pm_config import resolve_config_path
from pm_config import task_kind
from pm_config import task_prefix
from pm_config import tasklist_name
from pm_io import load_json_file
from pm_io import now_iso
from pm_runtime import run_codex_cli
from pm_runtime import run_openclaw_agent
from pm_worker import effective_task as resolve_effective_task

from pm_api_context import build_coder_context
from pm_api_context import build_context_payload
from pm_api_context import build_planning_bundle
from pm_api_context import build_run_message
from pm_api_context import choose_next_task
from pm_api_context import persist_dispatch_side_effects
from pm_api_context import persist_run_side_effects
from pm_api_context import refresh_context_cache
from pm_api_context import task_brief
from pm_api_context import write_pm_bundle
from pm_api_gsd import append_state_doc
from pm_api_gsd import attach_gsd_contracts
from pm_api_gsd import build_gsd_plan_phase_message
from pm_api_gsd import build_gsd_required_reads
from pm_api_gsd import build_gsd_task_description
from pm_api_gsd import build_gsd_task_hints
from pm_api_gsd import build_gsd_task_summary_body
from pm_api_gsd import comment_task_guid
from pm_api_gsd import create_doc
from pm_api_gsd import create_root_folder
from pm_api_gsd import ensure_project_docs
from pm_api_gsd import execute_gsd_plan_phase
from pm_api_gsd import existing_gsd_reads
from pm_api_gsd import extract_drive_node
from pm_api_gsd import extract_gsd_task_binding
from pm_api_gsd import find_root_folder_by_name
from pm_api_gsd import gsd_phase_context_path
from pm_api_gsd import load_gsd_binding_index
from pm_api_gsd import materialize_gsd_tasks
from pm_api_gsd import plan_gsd_phase_workflow
from pm_api_gsd import resolve_task_gsd_contract
from pm_api_gsd import route_gsd_work
from pm_api_gsd import sync_gsd_docs
from pm_api_gsd import sync_gsd_progress
from pm_api_gsd import update_doc
from pm_api_support import build_auth_bundle
from pm_api_support import build_auth_link
from pm_api_support import build_permission_bundle
from pm_api_support import build_run_label
from pm_api_support import build_workspace_profile
from pm_api_support import bridge_script_path
from pm_api_support import default_doc_folder_name
from pm_api_support import default_tasklist_name
from pm_api_support import details_of
from pm_api_support import doc_backend_name
from pm_api_support import english_project_name
from pm_api_support import ensure_attachment_token
from pm_api_support import feishu_credentials
from pm_api_support import get_channel_app_info
from pm_api_support import gsd_bindings_path
from pm_api_support import list_app_scope_presets
from pm_api_support import load_openclaw_gateway_user_token
from pm_api_support import openclaw_config
from pm_api_support import project_display_name
from pm_api_support import project_slug
from pm_api_support import register_main_digest_source
from pm_api_support import register_nightly_review_job
from pm_api_support import register_workspace
from pm_api_support import request_json
from pm_api_support import request_user_oauth_link
from pm_api_support import resolve_openclaw_config_path
from pm_api_support import resolve_workspace_root
from pm_api_support import run_bridge
from pm_api_support import sanitize_feishu_markdown
from pm_api_support import scaffold_workspace
from pm_api_support import spawn_acp_session
from pm_api_support import task_backend_name
from pm_api_tasks import add_task_members
from pm_api_tasks import attachment_auth_result
from pm_api_tasks import bootstrap_task_template
from pm_api_tasks import build_completion_changes
from pm_api_tasks import build_completion_comment
from pm_api_tasks import build_description
from pm_api_tasks import build_normalized_summary_from_text
from pm_api_tasks import completion_due_mode
from pm_api_tasks import create_task
from pm_api_tasks import create_task_comment
from pm_api_tasks import current_head_commit_url
from pm_api_tasks import detail_for_row
from pm_api_tasks import ensure_bootstrap_task
from pm_api_tasks import ensure_description_has_task_id
from pm_api_tasks import ensure_task_started
from pm_api_tasks import ensure_tasklist
from pm_api_tasks import extract_task_number
from pm_api_tasks import find_existing_task_by_summary
from pm_api_tasks import find_task_summary
from pm_api_tasks import get_task_record
from pm_api_tasks import get_task_record_by_guid
from pm_api_tasks import inspect_tasklist
from pm_api_tasks import list_task_attachments
from pm_api_tasks import list_task_comments
from pm_api_tasks import list_tasklist_tasks
from pm_api_tasks import maybe_normalize_task_summary
from pm_api_tasks import next_task_id
from pm_api_tasks import normalize_task_key
from pm_api_tasks import normalize_task_titles
from pm_api_tasks import parse_task_id_from_description
from pm_api_tasks import parse_task_summary
from pm_api_tasks import patch_task
from pm_api_tasks import resolve_optional_text_input
from pm_api_tasks import resolve_text_input
from pm_api_tasks import task_assignment_auth_result
from pm_api_tasks import task_has_due
from pm_api_tasks import task_id_for_output
from pm_api_tasks import task_pool
from pm_api_tasks import upload_task_attachments


def _config_api_exports() -> dict[str, object]:
    return {
        "ACTIVE_CONFIG": ACTIVE_CONFIG,
        "coder_config": coder_config,
        "default_config": default_config,
        "ensure_pm_dir": ensure_pm_dir,
        "load_config": load_config,
        "pm_dir_path": pm_dir_path,
        "pm_file": pm_file,
        "project_root_path": project_root_path,
        "resolve_config_path": resolve_config_path,
        "task_kind": task_kind,
        "task_prefix": task_prefix,
        "tasklist_name": tasklist_name,
    }


def _context_api_exports() -> dict[str, object]:
    return {
        "build_context_payload": build_context_payload,
        "build_coder_context": build_coder_context,
        "build_planning_bundle": build_planning_bundle,
        "build_run_message": build_run_message,
        "persist_dispatch_side_effects": persist_dispatch_side_effects,
        "persist_run_side_effects": persist_run_side_effects,
        "refresh_context_cache": refresh_context_cache,
        "resolve_effective_task": resolve_effective_task,
        "write_pm_bundle": write_pm_bundle,
    }


def _gsd_api_exports() -> dict[str, object]:
    return {
        "append_state_doc": append_state_doc,
        "attach_gsd_contracts": attach_gsd_contracts,
        "build_gsd_plan_phase_message": build_gsd_plan_phase_message,
        "build_gsd_required_reads": build_gsd_required_reads,
        "build_gsd_task_description": build_gsd_task_description,
        "build_gsd_task_hints": build_gsd_task_hints,
        "build_gsd_task_summary_body": build_gsd_task_summary_body,
        "comment_task_guid": comment_task_guid,
        "create_doc": create_doc,
        "create_root_folder": create_root_folder,
        "ensure_project_docs": ensure_project_docs,
        "execute_gsd_plan_phase": execute_gsd_plan_phase,
        "existing_gsd_reads": existing_gsd_reads,
        "extract_drive_node": extract_drive_node,
        "extract_gsd_task_binding": extract_gsd_task_binding,
        "find_root_folder_by_name": find_root_folder_by_name,
        "gsd_phase_context_path": gsd_phase_context_path,
        "load_gsd_binding_index": load_gsd_binding_index,
        "materialize_gsd_tasks": materialize_gsd_tasks,
        "plan_gsd_phase_workflow": plan_gsd_phase_workflow,
        "resolve_task_gsd_contract": resolve_task_gsd_contract,
        "route_gsd_work": route_gsd_work,
        "sync_gsd_docs": sync_gsd_docs,
        "sync_gsd_progress": sync_gsd_progress,
        "update_doc": update_doc,
    }


def _support_api_exports() -> dict[str, object]:
    return {
        "build_auth_bundle": build_auth_bundle,
        "build_auth_link": build_auth_link,
        "build_permission_bundle": build_permission_bundle,
        "build_run_label": build_run_label,
        "build_workspace_profile": build_workspace_profile,
        "bridge_script_path": bridge_script_path,
        "default_doc_folder_name": default_doc_folder_name,
        "default_tasklist_name": default_tasklist_name,
        "details_of": details_of,
        "doc_backend_name": doc_backend_name,
        "english_project_name": english_project_name,
        "ensure_attachment_token": ensure_attachment_token,
        "feishu_credentials": feishu_credentials,
        "get_channel_app_info": get_channel_app_info,
        "gsd_bindings_path": gsd_bindings_path,
        "list_app_scope_presets": list_app_scope_presets,
        "load_json_file": load_json_file,
        "load_openclaw_gateway_user_token": load_openclaw_gateway_user_token,
        "now_iso": now_iso,
        "openclaw_config": openclaw_config,
        "project_display_name": project_display_name,
        "project_slug": project_slug,
        "register_main_digest_source": register_main_digest_source,
        "register_nightly_review_job": register_nightly_review_job,
        "register_workspace": register_workspace,
        "request_json": request_json,
        "request_user_oauth_link": request_user_oauth_link,
        "resolve_openclaw_config_path": resolve_openclaw_config_path,
        "resolve_workspace_root": resolve_workspace_root,
        "run_bridge": run_bridge,
        "run_codex_cli": run_codex_cli,
        "run_openclaw_agent": run_openclaw_agent,
        "sanitize_feishu_markdown": sanitize_feishu_markdown,
        "scaffold_workspace": scaffold_workspace,
        "spawn_acp_session": spawn_acp_session,
        "task_backend_name": task_backend_name,
    }


def _task_api_exports() -> dict[str, object]:
    return {
        "add_task_members": add_task_members,
        "attachment_auth_result": attachment_auth_result,
        "bootstrap_task_template": bootstrap_task_template,
        "build_completion_changes": build_completion_changes,
        "build_completion_comment": build_completion_comment,
        "build_description": build_description,
        "build_normalized_summary_from_text": build_normalized_summary_from_text,
        "choose_next_task": choose_next_task,
        "completion_due_mode": completion_due_mode,
        "create_task": create_task,
        "create_task_comment": create_task_comment,
        "current_head_commit_url": current_head_commit_url,
        "detail_for_row": detail_for_row,
        "ensure_bootstrap_task": ensure_bootstrap_task,
        "ensure_description_has_task_id": ensure_description_has_task_id,
        "ensure_task_started": ensure_task_started,
        "ensure_tasklist": ensure_tasklist,
        "extract_task_number": extract_task_number,
        "find_existing_task_by_summary": find_existing_task_by_summary,
        "find_task_summary": find_task_summary,
        "get_task_record": get_task_record,
        "get_task_record_by_guid": get_task_record_by_guid,
        "inspect_tasklist": inspect_tasklist,
        "list_task_attachments": list_task_attachments,
        "list_task_comments": list_task_comments,
        "list_tasklist_tasks": list_tasklist_tasks,
        "maybe_normalize_task_summary": maybe_normalize_task_summary,
        "next_task_id": next_task_id,
        "normalize_task_key": normalize_task_key,
        "normalize_task_titles": normalize_task_titles,
        "parse_task_id_from_description": parse_task_id_from_description,
        "parse_task_summary": parse_task_summary,
        "patch_task": patch_task,
        "resolve_optional_text_input": resolve_optional_text_input,
        "resolve_text_input": resolve_text_input,
        "task_assignment_auth_result": task_assignment_auth_result,
        "task_brief": task_brief,
        "task_has_due": task_has_due,
        "task_id_for_output": task_id_for_output,
        "task_pool": task_pool,
        "upload_task_attachments": upload_task_attachments,
    }


def build_cli_api() -> SimpleNamespace:
    api_exports: dict[str, object] = {}
    for group in (
        _config_api_exports(),
        _context_api_exports(),
        _gsd_api_exports(),
        _support_api_exports(),
        _task_api_exports(),
    ):
        api_exports.update(group)
    return SimpleNamespace(**api_exports)
