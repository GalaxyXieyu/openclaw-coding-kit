from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

EnsureTasklistFn = Callable[[], dict[str, Any]]
TaskPoolFn = Callable[..., list[dict[str, Any]]]
GetTaskRecordByGuidFn = Callable[[str], dict[str, Any]]
ExtractTaskNumberFn = Callable[[str], int]
ParseTaskSummaryFn = Callable[[str], Optional[dict[str, Any]]]
ParseTaskIdFromDescriptionFn = Callable[[str], str]
ExtractGsdTaskBindingFn = Callable[[str], dict[str, str]]
TaskPrefixFn = Callable[[], str]
BuildNormalizedSummaryFn = Callable[[str, str], str]
BuildGsdTaskSummaryBodyFn = Callable[[dict[str, Any]], str]
BuildGsdTaskDescriptionFn = Callable[[str, dict[str, Any], Path], str]
BuildGsdTaskContractFn = Callable[[Path, dict[str, Any]], dict[str, Any]]
CreateTaskFn = Callable[..., dict[str, Any]]
PatchTaskFn = Callable[[str, dict[str, Any]], dict[str, Any]]
BuildCompletionChangesFn = Callable[[dict[str, Any], str], dict[str, Any]]
NowIsoFn = Callable[[], str]
WriteRepoJsonFn = Callable[[Path, dict[str, Any]], None]


def materialize_gsd_tasks(
    *,
    root: Path,
    phase_payload: dict[str, Any],
    ensure_tasklist: EnsureTasklistFn,
    task_pool: TaskPoolFn,
    get_task_record_by_guid: GetTaskRecordByGuidFn,
    extract_task_number: ExtractTaskNumberFn,
    parse_task_summary: ParseTaskSummaryFn,
    parse_task_id_from_description: ParseTaskIdFromDescriptionFn,
    extract_gsd_task_binding: ExtractGsdTaskBindingFn,
    task_prefix: TaskPrefixFn,
    build_normalized_summary_from_text: BuildNormalizedSummaryFn,
    build_gsd_task_summary_body: BuildGsdTaskSummaryBodyFn,
    build_gsd_task_description: BuildGsdTaskDescriptionFn,
    build_gsd_task_contract: BuildGsdTaskContractFn,
    create_task: CreateTaskFn,
    patch_task: PatchTaskFn,
    build_completion_changes: BuildCompletionChangesFn | None,
    now_iso: NowIsoFn,
    binding_index_path: Path,
    write_repo_json: WriteRepoJsonFn,
) -> dict[str, Any]:
    plans = [item for item in (phase_payload.get("plans") or []) if isinstance(item, dict)]
    tasklist = ensure_tasklist()
    tasklist_guid = str(tasklist.get("guid") or "").strip()
    owner = tasklist.get("owner") if isinstance(tasklist.get("owner"), dict) else {}
    current_user_id = str(owner.get("id") or "").strip()

    existing_rows = task_pool(include_completed=True, fetch_description_if_needed=False)
    existing_by_plan_path: dict[str, dict[str, Any]] = {}
    used_numbers: set[int] = set()

    for row in existing_rows:
        summary = str(row.get("normalized_summary") or row.get("summary") or "").strip()
        number = extract_task_number(summary)
        if number > 0:
            used_numbers.add(number)
        guid = str(row.get("guid") or "").strip()
        if not guid:
            continue
        detail = get_task_record_by_guid(guid)
        parsed = parse_task_summary(str(detail.get("summary") or "").strip()) or {}
        parsed_id = str(parsed.get("task_id") or parse_task_id_from_description(str(detail.get("description") or "")) or "").strip()
        if parsed_id:
            try:
                used_numbers.add(int(parsed_id[len(task_prefix()) :]))
            except ValueError:
                pass
        contract = detail.get("gsd_contract") if isinstance(detail.get("gsd_contract"), dict) else {}
        binding = extract_gsd_task_binding(str(detail.get("description") or ""))
        plan_path = str(contract.get("plan_path") or binding.get("plan_path") or "").strip()
        if plan_path:
            existing_by_plan_path[plan_path] = {
                "task": detail,
                "binding": binding,
                "task_id": parsed_id,
                "gsd_contract": contract,
            }

    next_number = max(used_numbers, default=0) + 1

    def allocate_task_id() -> str:
        nonlocal next_number
        while next_number in used_numbers:
            next_number += 1
        task_id = f"{task_prefix()}{next_number}"
        used_numbers.add(next_number)
        next_number += 1
        return task_id

    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    untouched: list[dict[str, Any]] = []
    completed_synced: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []

    for plan in plans:
        plan_path = str(plan.get("plan_path") or "").strip()
        contract = build_gsd_task_contract(root, plan)
        existing = existing_by_plan_path.get(plan_path)
        if existing:
            task = existing["task"]
            guid = str(task.get("guid") or "").strip()
            task_id = str(existing.get("task_id") or "").strip() or allocate_task_id()
            summary_body = build_gsd_task_summary_body(plan)
            normalized_summary = build_normalized_summary_from_text(task_id, summary_body)
            description = build_gsd_task_description(task_id, plan, root)
            patch_args: dict[str, Any] = {}
            if str(task.get("summary") or "").strip() != normalized_summary:
                patch_args["summary"] = normalized_summary
            if str(task.get("description") or "").strip() != description:
                patch_args["description"] = description
            patch_args["gsd_contract"] = contract
            if patch_args:
                patch_task(guid, patch_args)
                updated.append(
                    {
                        "task_id": task_id,
                        "task_guid": guid,
                        "url": task.get("url") or "",
                        "plan_path": plan_path,
                        "status": "updated",
                    }
                )
            else:
                untouched.append(
                    {
                        "task_id": task_id,
                        "task_guid": guid,
                        "url": task.get("url") or "",
                        "plan_path": plan_path,
                        "status": "unchanged",
                    }
                )
            if bool(plan.get("has_summary")) and not str(task.get("completed_at") or "").strip():
                completed_at = now_iso()
                completion_changes = (
                    build_completion_changes(task, completed_at)
                    if build_completion_changes is not None
                    else {"completed_at": completed_at}
                )
                patch_task(guid, completion_changes)
                completed_synced.append(
                    {
                        "task_id": task_id,
                        "task_guid": guid,
                        "url": task.get("url") or "",
                        "plan_path": plan_path,
                        "status": "completed_from_summary",
                    }
                )
            bindings.append(
                {
                    "task_id": task_id,
                    "task_guid": guid,
                    "plan_path": plan_path,
                    "summary_path": str(contract.get("summary_path") or "").strip(),
                    "contract": contract,
                }
            )
            continue

        task_id = allocate_task_id()
        summary_body = build_gsd_task_summary_body(plan)
        title = build_normalized_summary_from_text(task_id, summary_body)
        description = build_gsd_task_description(task_id, plan, root)
        task = create_task(
            summary=title,
            description=description,
            tasklists=[{"tasklist_guid": tasklist_guid}],
            current_user_id=current_user_id,
            gsd_contract=contract,
        )
        guid = str(task.get("guid") or "").strip()
        created.append(
            {
                "task_id": task_id,
                "task_guid": guid,
                "url": task.get("url") or "",
                "plan_path": plan_path,
                "status": "created",
            }
        )
        if bool(plan.get("has_summary")) and guid:
            completed_at = now_iso()
            completion_changes = (
                build_completion_changes(task, completed_at)
                if build_completion_changes is not None
                else {"completed_at": completed_at}
            )
            patch_task(guid, completion_changes)
            completed_synced.append(
                {
                    "task_id": task_id,
                    "task_guid": guid,
                    "url": task.get("url") or "",
                    "plan_path": plan_path,
                    "status": "completed_from_summary",
                }
            )
        bindings.append(
            {
                "task_id": task_id,
                "task_guid": guid,
                "plan_path": plan_path,
                "summary_path": str(contract.get("summary_path") or "").strip(),
                "contract": contract,
            }
        )

    write_repo_json(
        binding_index_path,
        {
            "generated_at": now_iso(),
            "phase": str(phase_payload.get("phase") or ""),
            "bindings": bindings,
        },
    )

    return {
        "repo_root": str(root),
        "phase": str(phase_payload.get("phase") or ""),
        "phase_dir": str(phase_payload.get("phase_dir") or ""),
        "phase_name": str(phase_payload.get("phase_name") or ""),
        "tasklist_guid": tasklist_guid,
        "plans_scanned": len(plans),
        "created_count": len(created),
        "updated_count": len(updated),
        "untouched_count": len(untouched),
        "completed_synced_count": len(completed_synced),
        "created": created,
        "updated": updated,
        "untouched": untouched,
        "completed_synced": completed_synced,
        "bindings_path": str(binding_index_path),
        "plans": plans,
    }
