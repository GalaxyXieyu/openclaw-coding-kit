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
from pm_api_support import best_effort_release_stale_acp_label
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
from pm_api_support import inspect_workspace_registration
from pm_api_support import register_main_digest_source
from pm_api_support import register_nightly_review_job
from pm_api_support import register_workspace
from pm_api_support import request_json
from pm_api_support import unregister_main_digest_source
from pm_api_support import unregister_nightly_review_job
from pm_api_support import unregister_workspace
from pm_api_support import request_user_oauth_link
from pm_api_support import resolve_current_openclaw_context
from pm_api_support import resolve_dispatch_session_key
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


def build_cli_api() -> SimpleNamespace:
    return SimpleNamespace(
        ACTIVE_CONFIG=ACTIVE_CONFIG,
        add_task_members=add_task_members,
        attachment_auth_result=attachment_auth_result,
        build_auth_bundle=build_auth_bundle,
        build_auth_link=build_auth_link,
        best_effort_release_stale_acp_label=best_effort_release_stale_acp_label,
        build_completion_changes=build_completion_changes,
        build_completion_comment=build_completion_comment,
        build_context_payload=build_context_payload,
        build_coder_context=build_coder_context,
        build_description=build_description,
        build_permission_bundle=build_permission_bundle,
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
        extract_drive_node=extract_drive_node,
        ensure_pm_dir=ensure_pm_dir,
        ensure_project_docs=ensure_project_docs,
        ensure_task_started=ensure_task_started,
        ensure_tasklist=ensure_tasklist,
        extract_task_number=extract_task_number,
        feishu_credentials=feishu_credentials,
        find_existing_task_by_summary=find_existing_task_by_summary,
        find_root_folder_by_name=find_root_folder_by_name,
        get_task_record=get_task_record,
        get_task_record_by_guid=get_task_record_by_guid,
        inspect_tasklist=inspect_tasklist,
        list_app_scope_presets=list_app_scope_presets,
        list_task_attachments=list_task_attachments,
        list_task_comments=list_task_comments,
        load_config=load_config,
        load_json_file=load_json_file,
        materialize_gsd_tasks=materialize_gsd_tasks,
        next_task_id=next_task_id,
        normalize_task_key=normalize_task_key,
        normalize_task_titles=normalize_task_titles,
        now_iso=now_iso,
        parse_task_summary=parse_task_summary,
        patch_task=patch_task,
        persist_dispatch_side_effects=persist_dispatch_side_effects,
        persist_run_side_effects=persist_run_side_effects,
        plan_gsd_phase_workflow=plan_gsd_phase_workflow,
        pm_dir_path=pm_dir_path,
        pm_file=pm_file,
        project_display_name=project_display_name,
        project_root_path=project_root_path,
        project_slug=project_slug,
        refresh_context_cache=refresh_context_cache,
        register_main_digest_source=register_main_digest_source,
        register_nightly_review_job=register_nightly_review_job,
        register_workspace=register_workspace,
        request_json=request_json,
        inspect_workspace_registration=inspect_workspace_registration,
        unregister_main_digest_source=unregister_main_digest_source,
        unregister_nightly_review_job=unregister_nightly_review_job,
        unregister_workspace=unregister_workspace,
        request_user_oauth_link=request_user_oauth_link,
        resolve_current_openclaw_context=resolve_current_openclaw_context,
        resolve_dispatch_session_key=resolve_dispatch_session_key,
        resolve_config_path=resolve_config_path,
        resolve_effective_task=resolve_effective_task,
        resolve_openclaw_config_path=resolve_openclaw_config_path,
        resolve_optional_text_input=resolve_optional_text_input,
        resolve_text_input=resolve_text_input,
        resolve_workspace_root=resolve_workspace_root,
        route_gsd_work=route_gsd_work,
        run_bridge=run_bridge,
        run_codex_cli=run_codex_cli,
        run_openclaw_agent=run_openclaw_agent,
        scaffold_workspace=scaffold_workspace,
        spawn_acp_session=spawn_acp_session,
        sync_gsd_docs=sync_gsd_docs,
        sync_gsd_progress=sync_gsd_progress,
        task_assignment_auth_result=task_assignment_auth_result,
        task_id_for_output=task_id_for_output,
        task_kind=task_kind,
        task_pool=task_pool,
        task_prefix=task_prefix,
        tasklist_name=tasklist_name,
        upload_task_attachments=upload_task_attachments,
        write_pm_bundle=write_pm_bundle,
    )
