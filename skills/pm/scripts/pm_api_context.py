from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_config import ACTIVE_CONFIG
from pm_config import pm_file
from pm_config import project_name
from pm_config import project_root_path
from pm_config import task_kind
from pm_config import task_prefix
from pm_config import tasklist_name
from pm_context import build_coder_context as build_pm_coder_context
from pm_context import build_context_payload as build_pm_context_payload
from pm_context import build_planning_bundle as build_pm_planning_bundle
from pm_context import choose_next_task as choose_pm_next_task
from pm_context import refresh_context_cache as refresh_pm_context_cache
from pm_context import task_brief as build_task_brief
from pm_io import now_iso
from pm_io import now_text
from pm_io import write_repo_json
from pm_scan import build_bootstrap_info
from pm_scan import detect_gsd_assets
from pm_scan import repo_scan
from pm_worker import build_coder_handoff_contract as build_worker_handoff_contract
from pm_worker import build_run_message as build_worker_run_message
from pm_worker import persist_dispatch_side_effects as persist_worker_dispatch_side_effects
from pm_worker import persist_run_side_effects as persist_worker_run_side_effects

from pm_api_gsd import append_state_doc
from pm_api_gsd import attach_gsd_contracts
from pm_api_gsd import comment_task_guid
from pm_api_gsd import route_gsd_work
from pm_api_tasks import extract_task_number
from pm_api_tasks import get_task_record
from pm_api_tasks import get_task_record_by_guid
from pm_api_tasks import list_task_comments
from pm_api_tasks import parse_task_id_from_description
from pm_api_tasks import parse_task_summary
from pm_api_tasks import task_pool
from pm_api_tasks import ensure_tasklist


def build_run_message(bundle: dict[str, Any]) -> str:
    return build_worker_run_message(bundle)


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
    from pm_dispatch import extract_dispatch_ids

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
    payload, _ = build_pm_coder_context(
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
