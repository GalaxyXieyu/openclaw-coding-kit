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


def _build_existing_task_index(
    *,
    existing_rows: list[dict[str, Any]],
    get_task_record_by_guid: GetTaskRecordByGuidFn,
    extract_task_number: ExtractTaskNumberFn,
    parse_task_summary: ParseTaskSummaryFn,
    parse_task_id_from_description: ParseTaskIdFromDescriptionFn,
    extract_gsd_task_binding: ExtractGsdTaskBindingFn,
    task_prefix: str,
) -> tuple[dict[str, dict[str, Any]], set[int]]:
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
                used_numbers.add(int(parsed_id[len(task_prefix) :]))
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
    return existing_by_plan_path, used_numbers


def _build_task_id_allocator(task_prefix: str, used_numbers: set[int]) -> Callable[[], str]:
    next_number = max(used_numbers, default=0) + 1

    def allocate_task_id() -> str:
        nonlocal next_number
        while next_number in used_numbers:
            next_number += 1
        task_id = f"{task_prefix}{next_number}"
        used_numbers.add(next_number)
        next_number += 1
        return task_id

    return allocate_task_id


def _materialized_task_entry(
    *,
    task_id: str,
    task_guid: str,
    url: str,
    plan_path: str,
    status: str,
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "task_guid": task_guid,
        "url": url,
        "plan_path": plan_path,
        "status": status,
    }


def _binding_entry(*, task_id: str, task_guid: str, plan_path: str, contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "task_guid": task_guid,
        "plan_path": plan_path,
        "summary_path": str(contract.get("summary_path") or "").strip(),
        "contract": contract,
    }


def _sync_task_completion_from_summary(
    *,
    plan: dict[str, Any],
    task: dict[str, Any],
    task_id: str,
    task_guid: str,
    plan_path: str,
    now_iso: NowIsoFn,
    patch_task: PatchTaskFn,
    build_completion_changes: BuildCompletionChangesFn | None,
    completed_synced: list[dict[str, Any]],
) -> None:
    if not bool(plan.get("has_summary")):
        return
    if not task_guid or str(task.get("completed_at") or "").strip():
        return
    completed_at = now_iso()
    completion_changes = (
        build_completion_changes(task, completed_at) if build_completion_changes is not None else {"completed_at": completed_at}
    )
    patch_task(task_guid, completion_changes)
    completed_synced.append(
        _materialized_task_entry(
            task_id=task_id,
            task_guid=task_guid,
            url=str(task.get("url") or ""),
            plan_path=plan_path,
            status="completed_from_summary",
        )
    )


def _sync_existing_plan_task(
    *,
    root: Path,
    plan: dict[str, Any],
    existing: dict[str, Any],
    allocate_task_id: Callable[[], str],
    build_gsd_task_summary_body: BuildGsdTaskSummaryBodyFn,
    build_normalized_summary_from_text: BuildNormalizedSummaryFn,
    build_gsd_task_description: BuildGsdTaskDescriptionFn,
    build_gsd_task_contract: BuildGsdTaskContractFn,
    patch_task: PatchTaskFn,
    now_iso: NowIsoFn,
    build_completion_changes: BuildCompletionChangesFn | None,
    updated: list[dict[str, Any]],
    untouched: list[dict[str, Any]],
    completed_synced: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
) -> None:
    task = existing["task"]
    guid = str(task.get("guid") or "").strip()
    task_id = str(existing.get("task_id") or "").strip() or allocate_task_id()
    plan_path = str(plan.get("plan_path") or "").strip()
    contract = build_gsd_task_contract(root, plan)
    summary_body = build_gsd_task_summary_body(plan)
    normalized_summary = build_normalized_summary_from_text(task_id, summary_body)
    description = build_gsd_task_description(task_id, plan, root)

    patch_args: dict[str, Any] = {}
    if str(task.get("summary") or "").strip() != normalized_summary:
        patch_args["summary"] = normalized_summary
    if str(task.get("description") or "").strip() != description:
        patch_args["description"] = description
    existing_contract = task.get("gsd_contract") if isinstance(task.get("gsd_contract"), dict) else {}
    if existing_contract != contract:
        patch_args["gsd_contract"] = contract

    if patch_args:
        patch_task(guid, patch_args)
        updated.append(
            _materialized_task_entry(
                task_id=task_id,
                task_guid=guid,
                url=str(task.get("url") or ""),
                plan_path=plan_path,
                status="updated",
            )
        )
    else:
        untouched.append(
            _materialized_task_entry(
                task_id=task_id,
                task_guid=guid,
                url=str(task.get("url") or ""),
                plan_path=plan_path,
                status="unchanged",
            )
        )
    _sync_task_completion_from_summary(
        plan=plan,
        task=task,
        task_id=task_id,
        task_guid=guid,
        plan_path=plan_path,
        now_iso=now_iso,
        patch_task=patch_task,
        build_completion_changes=build_completion_changes,
        completed_synced=completed_synced,
    )
    bindings.append(_binding_entry(task_id=task_id, task_guid=guid, plan_path=plan_path, contract=contract))


def _create_plan_task(
    *,
    root: Path,
    plan: dict[str, Any],
    tasklist_guid: str,
    current_user_id: str,
    allocate_task_id: Callable[[], str],
    build_gsd_task_summary_body: BuildGsdTaskSummaryBodyFn,
    build_normalized_summary_from_text: BuildNormalizedSummaryFn,
    build_gsd_task_description: BuildGsdTaskDescriptionFn,
    build_gsd_task_contract: BuildGsdTaskContractFn,
    create_task: CreateTaskFn,
    patch_task: PatchTaskFn,
    now_iso: NowIsoFn,
    build_completion_changes: BuildCompletionChangesFn | None,
    created: list[dict[str, Any]],
    completed_synced: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
) -> None:
    task_id = allocate_task_id()
    plan_path = str(plan.get("plan_path") or "").strip()
    contract = build_gsd_task_contract(root, plan)
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
        _materialized_task_entry(
            task_id=task_id,
            task_guid=guid,
            url=str(task.get("url") or ""),
            plan_path=plan_path,
            status="created",
        )
    )
    _sync_task_completion_from_summary(
        plan=plan,
        task=task,
        task_id=task_id,
        task_guid=guid,
        plan_path=plan_path,
        now_iso=now_iso,
        patch_task=patch_task,
        build_completion_changes=build_completion_changes,
        completed_synced=completed_synced,
    )
    bindings.append(_binding_entry(task_id=task_id, task_guid=guid, plan_path=plan_path, contract=contract))


def _phase_plans(phase_payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [item for item in (phase_payload.get("plans") or []) if isinstance(item, dict)]


def _tasklist_context(tasklist: dict[str, Any]) -> tuple[str, str]:
    owner = tasklist.get("owner") if isinstance(tasklist.get("owner"), dict) else {}
    return str(tasklist.get("guid") or "").strip(), str(owner.get("id") or "").strip()


def _build_materialization_lookup(
    *,
    task_pool: TaskPoolFn,
    get_task_record_by_guid: GetTaskRecordByGuidFn,
    extract_task_number: ExtractTaskNumberFn,
    parse_task_summary: ParseTaskSummaryFn,
    parse_task_id_from_description: ParseTaskIdFromDescriptionFn,
    extract_gsd_task_binding: ExtractGsdTaskBindingFn,
    task_prefix: TaskPrefixFn,
) -> tuple[dict[str, dict[str, Any]], Callable[[], str]]:
    existing_rows = task_pool(include_completed=True, fetch_description_if_needed=False)
    prefix = task_prefix()
    existing_by_plan_path, used_numbers = _build_existing_task_index(
        existing_rows=existing_rows,
        get_task_record_by_guid=get_task_record_by_guid,
        extract_task_number=extract_task_number,
        parse_task_summary=parse_task_summary,
        parse_task_id_from_description=parse_task_id_from_description,
        extract_gsd_task_binding=extract_gsd_task_binding,
        task_prefix=prefix,
    )
    return existing_by_plan_path, _build_task_id_allocator(prefix, used_numbers)


def _materialize_plan(
    *,
    root: Path,
    plan: dict[str, Any],
    existing: dict[str, Any] | None,
    tasklist_guid: str,
    current_user_id: str,
    allocate_task_id: Callable[[], str],
    build_gsd_task_summary_body: BuildGsdTaskSummaryBodyFn,
    build_normalized_summary_from_text: BuildNormalizedSummaryFn,
    build_gsd_task_description: BuildGsdTaskDescriptionFn,
    build_gsd_task_contract: BuildGsdTaskContractFn,
    create_task: CreateTaskFn,
    patch_task: PatchTaskFn,
    now_iso: NowIsoFn,
    build_completion_changes: BuildCompletionChangesFn | None,
    created: list[dict[str, Any]],
    updated: list[dict[str, Any]],
    untouched: list[dict[str, Any]],
    completed_synced: list[dict[str, Any]],
    bindings: list[dict[str, Any]],
) -> None:
    if existing is not None:
        _sync_existing_plan_task(
            root=root,
            plan=plan,
            existing=existing,
            allocate_task_id=allocate_task_id,
            build_gsd_task_summary_body=build_gsd_task_summary_body,
            build_normalized_summary_from_text=build_normalized_summary_from_text,
            build_gsd_task_description=build_gsd_task_description,
            build_gsd_task_contract=build_gsd_task_contract,
            patch_task=patch_task,
            now_iso=now_iso,
            build_completion_changes=build_completion_changes,
            updated=updated,
            untouched=untouched,
            completed_synced=completed_synced,
            bindings=bindings,
        )
        return
    _create_plan_task(
        root=root,
        plan=plan,
        tasklist_guid=tasklist_guid,
        current_user_id=current_user_id,
        allocate_task_id=allocate_task_id,
        build_gsd_task_summary_body=build_gsd_task_summary_body,
        build_normalized_summary_from_text=build_normalized_summary_from_text,
        build_gsd_task_description=build_gsd_task_description,
        build_gsd_task_contract=build_gsd_task_contract,
        create_task=create_task,
        patch_task=patch_task,
        now_iso=now_iso,
        build_completion_changes=build_completion_changes,
        created=created,
        completed_synced=completed_synced,
        bindings=bindings,
    )


def _materialize_plans(
    *,
    plans: list[dict[str, Any]],
    root: Path,
    existing_by_plan_path: dict[str, dict[str, Any]],
    tasklist_guid: str,
    current_user_id: str,
    allocate_task_id: Callable[[], str],
    build_gsd_task_summary_body: BuildGsdTaskSummaryBodyFn,
    build_normalized_summary_from_text: BuildNormalizedSummaryFn,
    build_gsd_task_description: BuildGsdTaskDescriptionFn,
    build_gsd_task_contract: BuildGsdTaskContractFn,
    create_task: CreateTaskFn,
    patch_task: PatchTaskFn,
    now_iso: NowIsoFn,
    build_completion_changes: BuildCompletionChangesFn | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    created: list[dict[str, Any]] = []
    updated: list[dict[str, Any]] = []
    untouched: list[dict[str, Any]] = []
    completed_synced: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []

    for plan in plans:
        plan_path = str(plan.get("plan_path") or "").strip()
        _materialize_plan(
            root=root,
            plan=plan,
            existing=existing_by_plan_path.get(plan_path),
            tasklist_guid=tasklist_guid,
            current_user_id=current_user_id,
            allocate_task_id=allocate_task_id,
            build_gsd_task_summary_body=build_gsd_task_summary_body,
            build_normalized_summary_from_text=build_normalized_summary_from_text,
            build_gsd_task_description=build_gsd_task_description,
            build_gsd_task_contract=build_gsd_task_contract,
            create_task=create_task,
            patch_task=patch_task,
            now_iso=now_iso,
            build_completion_changes=build_completion_changes,
            created=created,
            updated=updated,
            untouched=untouched,
            completed_synced=completed_synced,
            bindings=bindings,
        )
    return created, updated, untouched, completed_synced, bindings


def _write_binding_index(
    *,
    binding_index_path: Path,
    phase_payload: dict[str, Any],
    bindings: list[dict[str, Any]],
    now_iso: NowIsoFn,
    write_repo_json: WriteRepoJsonFn,
) -> None:
    write_repo_json(
        binding_index_path,
        {
            "generated_at": now_iso(),
            "phase": str(phase_payload.get("phase") or ""),
            "bindings": bindings,
        },
    )


def _materialization_result(
    *,
    root: Path,
    phase_payload: dict[str, Any],
    tasklist_guid: str,
    binding_index_path: Path,
    plans: list[dict[str, Any]],
    created: list[dict[str, Any]],
    updated: list[dict[str, Any]],
    untouched: list[dict[str, Any]],
    completed_synced: list[dict[str, Any]],
) -> dict[str, Any]:
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
    plans = _phase_plans(phase_payload)
    tasklist = ensure_tasklist()
    tasklist_guid, current_user_id = _tasklist_context(tasklist)
    existing_by_plan_path, allocate_task_id = _build_materialization_lookup(
        task_pool=task_pool,
        get_task_record_by_guid=get_task_record_by_guid,
        extract_task_number=extract_task_number,
        parse_task_summary=parse_task_summary,
        parse_task_id_from_description=parse_task_id_from_description,
        extract_gsd_task_binding=extract_gsd_task_binding,
        task_prefix=task_prefix,
    )

    created, updated, untouched, completed_synced, bindings = _materialize_plans(
        plans=plans,
        root=root,
        existing_by_plan_path=existing_by_plan_path,
        tasklist_guid=tasklist_guid,
        current_user_id=current_user_id,
        allocate_task_id=allocate_task_id,
        build_gsd_task_summary_body=build_gsd_task_summary_body,
        build_normalized_summary_from_text=build_normalized_summary_from_text,
        build_gsd_task_description=build_gsd_task_description,
        build_gsd_task_contract=build_gsd_task_contract,
        create_task=create_task,
        patch_task=patch_task,
        now_iso=now_iso,
        build_completion_changes=build_completion_changes,
    )

    _write_binding_index(
        binding_index_path=binding_index_path,
        phase_payload=phase_payload,
        bindings=bindings,
        now_iso=now_iso,
        write_repo_json=write_repo_json,
    )
    return _materialization_result(
        root=root,
        phase_payload=phase_payload,
        tasklist_guid=tasklist_guid,
        binding_index_path=binding_index_path,
        plans=plans,
        created=created,
        updated=updated,
        untouched=untouched,
        completed_synced=completed_synced,
    )
