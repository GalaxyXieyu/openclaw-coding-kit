from __future__ import annotations

import re
import subprocess
from typing import Any, Callable, Optional

RunBridgeFn = Callable[..., dict[str, Any]]
DetailsFn = Callable[[dict[str, Any]], dict[str, Any]]
TasklistNameFn = Callable[[], str]
TaskPrefixFn = Callable[[], str]
NormalizeTitlesFn = Callable[..., dict[str, Any]]
MaybeNormalizeFn = Callable[..., dict[str, Any]]
ParseTaskSummaryFn = Callable[[str], Optional[dict[str, Any]]]
ParseTaskIdFromDescriptionFn = Callable[[str], str]
BuildNormalizedSummaryFn = Callable[[str, str], str]
EnsureDescriptionTaskIdFn = Callable[[str, str], str]
NowIsoFn = Callable[[], str]
NowTextFn = Callable[[], str]
DescriptionRequirementsFn = Callable[[], list[str]]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def list_tasklists(run_bridge: RunBridgeFn, details_of: DetailsFn) -> list[dict[str, Any]]:
    page_token = ""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    while True:
        args: dict[str, Any] = {"page_size": 100}
        if page_token:
            args["page_token"] = page_token
        payload = run_bridge("feishu_task_tasklist", "list", args)
        details = details_of(payload)
        for item in details.get("tasklists") or []:
            if not isinstance(item, dict):
                continue
            guid = str(item.get("guid") or "").strip()
            if guid and guid not in seen:
                rows.append(item)
                seen.add(guid)
        page_token = str(details.get("page_token") or "").strip()
        if not details.get("has_more") or not page_token:
            break
    return rows


def _tasklist_candidates_text(matches: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in matches:
        parts.append(
            f"{str(item.get('name') or '').strip()} | guid={str(item.get('guid') or '').strip()} | "
            f"url={str(item.get('url') or '').strip() or '-'}"
        )
    return "; ".join(parts)


def inspect_tasklist(
    run_bridge: RunBridgeFn,
    details_of: DetailsFn,
    *,
    tasklist_name: TasklistNameFn,
    name: Optional[str] = None,
    configured_guid: str = "",
) -> dict[str, Any]:
    resolved_name = _normalize_text((name or "").strip() or tasklist_name())
    guid_hint = str(configured_guid or "").strip()
    tasklists = list_tasklists(run_bridge, details_of)
    if guid_hint:
        for item in tasklists:
            if str(item.get("guid") or "").strip() == guid_hint:
                return {"status": "configured_match", "tasklist": item, "matches": [item], "resolved_name": resolved_name}
    matches = [item for item in tasklists if _normalize_text(str(item.get("name") or "")) == resolved_name]
    if len(matches) == 1:
        return {"status": "unique_match", "tasklist": matches[0], "matches": matches, "resolved_name": resolved_name}
    if len(matches) > 1:
        return {"status": "ambiguous", "tasklist": None, "matches": matches, "resolved_name": resolved_name}
    return {"status": "missing", "tasklist": None, "matches": [], "resolved_name": resolved_name}


def ensure_tasklist(
    run_bridge: RunBridgeFn,
    details_of: DetailsFn,
    *,
    tasklist_name: TasklistNameFn,
    name: Optional[str] = None,
    configured_guid: str = "",
) -> dict[str, Any]:
    inspection = inspect_tasklist(
        run_bridge,
        details_of,
        tasklist_name=tasklist_name,
        name=name,
        configured_guid=configured_guid,
    )
    resolved_name = str(inspection.get("resolved_name") or "").strip()
    tasklist = inspection.get("tasklist")
    if isinstance(tasklist, dict) and str(tasklist.get("guid") or "").strip():
        return tasklist
    if str(inspection.get("status") or "") == "ambiguous":
        matches = inspection.get("matches") if isinstance(inspection.get("matches"), list) else []
        raise SystemExit(f"multiple Feishu tasklists matched '{resolved_name}': {_tasklist_candidates_text(matches)}")
    created = run_bridge("feishu_task_tasklist", "create", {"name": resolved_name})
    created_details = details_of(created)
    tasklist = created_details.get("tasklist")
    if isinstance(tasklist, dict) and str(tasklist.get("guid") or "").strip():
        return tasklist
    follow_up = inspect_tasklist(
        run_bridge,
        details_of,
        tasklist_name=tasklist_name,
        name=resolved_name,
        configured_guid="",
    )
    tasklist = follow_up.get("tasklist")
    if isinstance(tasklist, dict) and str(tasklist.get("guid") or "").strip():
        return tasklist
    raise SystemExit(f"failed to resolve tasklist: {resolved_name}")


def list_tasklist_tasks(run_bridge: RunBridgeFn, details_of: DetailsFn, tasklist_guid: str, *, completed: bool) -> list[dict[str, Any]]:
    page_token = ""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    while True:
        args: dict[str, Any] = {
            "tasklist_guid": tasklist_guid,
            "completed": completed,
            "page_size": 100,
        }
        if page_token:
            args["page_token"] = page_token
        payload = run_bridge("feishu_task_tasklist", "tasks", args)
        details = details_of(payload)
        for item in details.get("tasks") or []:
            if not isinstance(item, dict):
                continue
            guid = str(item.get("guid") or "").strip()
            if guid and guid not in seen:
                rows.append(item)
                seen.add(guid)
        page_token = str(details.get("page_token") or "").strip()
        if not details.get("has_more") or not page_token:
            break
    return rows


def task_has_started(task: dict[str, Any]) -> bool:
    start = task.get("start")
    return isinstance(start, dict) and str(start.get("timestamp") or "").strip() not in {"", "0"}


def ensure_task_started(task: dict[str, Any], *, run_bridge: RunBridgeFn, now_iso: NowIsoFn) -> Optional[dict[str, Any]]:
    if task_has_started(task):
        return None
    guid = str(task.get("guid") or "").strip()
    if not guid:
        return None
    return run_bridge(
        "feishu_task_task",
        "patch",
        {
            "task_guid": guid,
            "start": {
                "timestamp": now_iso(),
                "is_all_day": False,
            },
        },
    )


def parse_task_summary(summary: str, *, task_prefix: TaskPrefixFn) -> Optional[dict[str, Any]]:
    text = (summary or "").strip()
    if not text:
        return None
    match = re.match(
        r"^\s*[\[【(（]?\s*(?P<prefix>[A-Za-z]+)\s*(?P<number>\d+)\s*[\]】)）]?\s*(?P<separator>[:：\-—.、]*)\s*(?P<body>.*)$",
        text,
    )
    if not match:
        return None
    expected_prefix = task_prefix()
    raw_prefix = str(match.group("prefix") or "").strip().upper()
    if raw_prefix != expected_prefix:
        return None
    number = int(match.group("number"))
    body = re.sub(r"\s+", " ", str(match.group("body") or "")).strip()
    task_id = f"{expected_prefix}{number}"
    normalized_summary = f"[{task_id}] {body}".strip() if body else f"[{task_id}]"
    return {
        "task_id": task_id,
        "number": number,
        "body": body,
        "summary": text,
        "normalized_summary": normalized_summary,
    }


def extract_task_number(summary: str, *, parse_task_summary: ParseTaskSummaryFn) -> int:
    parsed = parse_task_summary(summary)
    return int(parsed.get("number") or 0) if parsed else 0


def parse_task_id_from_description(description: str, *, task_prefix: TaskPrefixFn) -> str:
    text = str(description or "").strip()
    if not text:
        return ""
    match = re.search(r"(?:任务编号|Task\s*ID)\s*[：:]\s*([A-Za-z]+\d+)", text, flags=re.IGNORECASE)
    if not match:
        return ""
    raw = str(match.group(1) or "").strip().upper()
    parsed = re.match(r"^([A-Z]+)(\d+)$", raw)
    if not parsed:
        return ""
    expected_prefix = task_prefix()
    if str(parsed.group(1) or "").upper() != expected_prefix:
        return ""
    return f"{expected_prefix}{int(parsed.group(2))}"


def build_normalized_summary_from_text(task_id: str, summary: str, *, parse_task_summary: ParseTaskSummaryFn) -> str:
    body = str(summary or "").strip()
    while True:
        parsed = parse_task_summary(body)
        if parsed:
            next_body = str(parsed.get("body") or "").strip()
        else:
            next_body = re.sub(
                r"^\s*[\[【(（]?\s*[A-Za-z]+\s*\d+\s*[\]】)）]?\s*[:：\-—.、]*\s*",
                "",
                body,
            ).strip()
        if next_body == body:
            break
        body = next_body
    body = re.sub(r"\s+", " ", body).strip()
    return f"[{task_id}] {body}".strip() if body else f"[{task_id}]"


def normalize_summary_body(summary: str, *, parse_task_summary: ParseTaskSummaryFn) -> str:
    body = str(summary or "").strip()
    parsed = parse_task_summary(body)
    if parsed:
        body = str(parsed.get("body") or "").strip()
    body = re.sub(r"\s+", " ", body).strip()
    return body.casefold()


def ensure_description_has_task_id(
    description: str,
    task_id: str,
    *,
    parse_task_id_from_description: ParseTaskIdFromDescriptionFn,
) -> str:
    normalized = str(description or "").strip()
    if not normalized:
        return f"任务编号：{task_id}"
    existing = parse_task_id_from_description(normalized)
    if existing == task_id:
        return normalized
    if existing:
        return re.sub(
            r"((?:任务编号|Task\s*ID)\s*[：:]\s*)([A-Za-z]+\d+)",
            rf"\g<1>{task_id}",
            normalized,
            count=1,
            flags=re.IGNORECASE,
        )
    return f"任务编号：{task_id}\n\n{normalized}"


def maybe_normalize_task_summary(
    item: dict[str, Any],
    *,
    parse_task_summary: ParseTaskSummaryFn,
    parse_task_id_from_description: ParseTaskIdFromDescriptionFn,
    build_normalized_summary_from_text: BuildNormalizedSummaryFn,
    run_bridge: RunBridgeFn,
    details_of: DetailsFn,
    fetch_description_if_needed: bool = True,
    allow_patch: bool = True,
) -> dict[str, Any]:
    summary = str(item.get("summary") or "").strip()
    guid = str(item.get("guid") or "").strip()
    parsed = parse_task_summary(summary)
    normalized_summary = ""
    normalized_task_id = ""
    if parsed:
        normalized_task_id = str(parsed.get("task_id") or "")
        normalized_summary = str(parsed.get("normalized_summary") or "").strip()
    else:
        description = str(item.get("description") or "").strip()
        if not description and guid and fetch_description_if_needed:
            payload = run_bridge("feishu_task_task", "get", {"task_guid": guid})
            details = details_of(payload)
            task = details.get("task")
            if isinstance(task, dict):
                description = str(task.get("description") or "").strip()
        task_id_from_description = parse_task_id_from_description(description)
        if not task_id_from_description:
            return item
        normalized_task_id = task_id_from_description
        normalized_summary = build_normalized_summary_from_text(task_id_from_description, summary)
    item["normalized_task_id"] = normalized_task_id
    item["normalized_summary"] = normalized_summary
    if not allow_patch or not guid or not normalized_summary or normalized_summary == summary:
        if normalized_summary:
            item["summary"] = normalized_summary
        return item
    run_bridge("feishu_task_task", "patch", {"task_guid": guid, "summary": normalized_summary})
    item["summary"] = normalized_summary
    return item


def detail_for_row(row: dict[str, Any], *, run_bridge: RunBridgeFn, details_of: DetailsFn) -> dict[str, Any]:
    guid = str(row.get("guid") or "").strip()
    if not guid:
        return {}
    payload = run_bridge("feishu_task_task", "get", {"task_guid": guid})
    details = details_of(payload)
    task = details.get("task")
    return task if isinstance(task, dict) else {}


def sort_key_for_assignment(item: dict[str, Any]) -> tuple[int, str]:
    created_at = str(item.get("created_at") or "").strip()
    try:
        created_num = int(created_at or "0")
    except ValueError:
        created_num = 0
    return created_num, str(item.get("guid") or "")


def normalize_task_titles(
    *,
    include_completed: bool,
    task_prefix: TaskPrefixFn,
    ensure_tasklist_fn: Callable[[], dict[str, Any]],
    list_tasklist_tasks_fn: Callable[..., list[dict[str, Any]]],
    parse_task_summary: ParseTaskSummaryFn,
    parse_task_id_from_description: ParseTaskIdFromDescriptionFn,
    build_normalized_summary_from_text: BuildNormalizedSummaryFn,
    ensure_description_has_task_id: EnsureDescriptionTaskIdFn,
    detail_for_row_fn: Callable[[dict[str, Any]], dict[str, Any]],
    run_bridge: RunBridgeFn,
) -> dict[str, Any]:
    tasklist = ensure_tasklist_fn()
    tasklist_guid = str(tasklist.get("guid") or "").strip()
    rows = list_tasklist_tasks_fn(tasklist_guid, completed=False)
    if include_completed:
        rows += list_tasklist_tasks_fn(tasklist_guid, completed=True)

    details_by_guid: dict[str, dict[str, Any]] = {}
    used_numbers: set[int] = set()
    results: list[dict[str, Any]] = []
    pending_without_id: list[dict[str, Any]] = []
    prefix = task_prefix()

    for row in rows:
        guid = str(row.get("guid") or "").strip()
        if not guid:
            continue
        summary = str(row.get("summary") or "").strip()
        parsed_summary = parse_task_summary(summary)
        detail: dict[str, Any] = {}
        task_id = ""
        if parsed_summary:
            task_id = str(parsed_summary.get("task_id") or "")
            used_numbers.add(int(parsed_summary.get("number") or 0))
        else:
            detail = detail_for_row_fn(row)
            details_by_guid[guid] = detail
            task_id = parse_task_id_from_description(str(detail.get("description") or ""))
            if task_id:
                used_numbers.add(int(task_id[len(prefix) :]))
        result = {
            "guid": guid,
            "summary_before": summary,
            "task_id": task_id,
            "detail": detail,
            "row": row,
            "parsed_summary": parsed_summary,
        }
        results.append(result)
        if not task_id:
            pending_without_id.append(result)

    next_number = max(used_numbers, default=0) + 1
    for item in sorted(pending_without_id, key=sort_key_for_assignment):
        while next_number in used_numbers:
            next_number += 1
        assigned_task_id = f"{prefix}{next_number}"
        used_numbers.add(next_number)
        next_number += 1
        item["task_id"] = assigned_task_id

    changed: list[dict[str, Any]] = []
    untouched: list[dict[str, Any]] = []
    for item in results:
        guid = item["guid"]
        row = item["row"]
        task_id = str(item.get("task_id") or "").strip()
        if not task_id:
            untouched.append({"guid": guid, "summary": row.get("summary") or ""})
            continue
        detail = item.get("detail") or details_by_guid.get(guid) or {}
        if not detail:
            detail = detail_for_row_fn(row)
            details_by_guid[guid] = detail
        description = str(detail.get("description") or "").strip()
        summary_before = str(row.get("summary") or "").strip()
        normalized_summary = build_normalized_summary_from_text(task_id, summary_before)
        normalized_description = ensure_description_has_task_id(description, task_id)
        patch_args: dict[str, Any] = {"task_guid": guid}
        if normalized_summary != summary_before:
            patch_args["summary"] = normalized_summary
        if normalized_description != description:
            patch_args["description"] = normalized_description
        if len(patch_args) > 1:
            run_bridge("feishu_task_task", "patch", patch_args)
            row["summary"] = normalized_summary
            row["description"] = normalized_description
            changed.append(
                {
                    "guid": guid,
                    "task_id": task_id,
                    "summary_before": summary_before,
                    "summary_after": normalized_summary,
                    "description_updated": normalized_description != description,
                }
            )
        else:
            row["summary"] = normalized_summary
            row["description"] = normalized_description
            untouched.append(
                {
                    "guid": guid,
                    "task_id": task_id,
                    "summary": normalized_summary,
                }
            )
    return {
        "tasklist_guid": tasklist_guid,
        "scanned_count": len(results),
        "changed_count": len(changed),
        "changed": changed,
        "untouched_count": len(untouched),
        "untouched": untouched,
    }


def task_pool(
    *,
    include_completed: bool,
    normalize_task_titles: NormalizeTitlesFn,
    ensure_tasklist_fn: Callable[[], dict[str, Any]],
    list_tasklist_tasks_fn: Callable[..., list[dict[str, Any]]],
    maybe_normalize_task_summary: MaybeNormalizeFn,
    normalize_titles_before_list: bool = False,
    fetch_description_if_needed: bool = True,
) -> list[dict[str, Any]]:
    if normalize_titles_before_list:
        normalize_task_titles(include_completed=include_completed)
    tasklist = ensure_tasklist_fn()
    tasklist_guid = str(tasklist.get("guid") or "").strip()
    dedup: dict[str, dict[str, Any]] = {}
    rows = list_tasklist_tasks_fn(tasklist_guid, completed=False)
    if include_completed:
        rows += list_tasklist_tasks_fn(tasklist_guid, completed=True)
    for item in rows:
        guid = str(item.get("guid") or "").strip()
        if guid:
            maybe_normalize_task_summary(
                item,
                fetch_description_if_needed=fetch_description_if_needed,
                allow_patch=normalize_titles_before_list,
            )
            dedup[guid] = item
    return list(dedup.values())


def next_task_id(*, task_prefix: TaskPrefixFn, task_pool_fn: Callable[..., list[dict[str, Any]]], extract_task_number_fn: Callable[[str], int]) -> str:
    current = max(
        (
            extract_task_number_fn(str(item.get("normalized_summary") or item.get("summary") or ""))
            for item in task_pool_fn(include_completed=True)
        ),
        default=0,
    )
    return f"{task_prefix()}{current + 1}"


def normalize_task_key(task_key: str, *, task_prefix: TaskPrefixFn) -> str:
    raw = (task_key or "").strip().upper()
    if not raw:
        raise SystemExit("task id is required")
    if raw.startswith("[") and raw.endswith("]"):
        raw = raw[1:-1].strip()
    prefix = task_prefix()
    if not raw.startswith(prefix):
        raw = f"{prefix}{raw}"
    return raw


def find_task_summary(
    task_key: str,
    *,
    include_completed: bool,
    normalize_task_key_fn: Callable[[str], str],
    task_pool_fn: Callable[..., list[dict[str, Any]]],
    parse_task_summary: ParseTaskSummaryFn,
) -> dict[str, Any]:
    normalized = normalize_task_key_fn(task_key)
    for item in task_pool_fn(include_completed=include_completed):
        parsed = parse_task_summary(str(item.get("normalized_summary") or item.get("summary") or "")) or {}
        normalized_task_id = str(item.get("normalized_task_id") or parsed.get("task_id") or "")
        if normalized_task_id == normalized:
            return item
    state_hint = "including completed tasks" if include_completed else "among unfinished tasks"
    raise SystemExit(f"task not found in Feishu {state_hint}: {normalized}")


def find_existing_task_by_summary(
    summary: str,
    *,
    include_completed: bool,
    task_pool_fn: Callable[..., list[dict[str, Any]]],
    parse_task_summary: ParseTaskSummaryFn,
) -> dict[str, Any] | None:
    target = normalize_summary_body(summary, parse_task_summary=parse_task_summary)
    if not target:
        return None
    for item in task_pool_fn(include_completed=include_completed):
        candidate = normalize_summary_body(
            str(item.get("normalized_summary") or item.get("summary") or ""),
            parse_task_summary=parse_task_summary,
        )
        if candidate == target:
            return item
    return None


def get_task_record(
    task_key: str,
    *,
    include_completed: bool,
    find_task_summary_fn: Callable[..., dict[str, Any]],
    run_bridge: RunBridgeFn,
    details_of: DetailsFn,
) -> dict[str, Any]:
    summary_item = find_task_summary_fn(task_key, include_completed=include_completed)
    guid = str(summary_item.get("guid") or "").strip()
    if not guid:
        raise SystemExit(f"task missing guid: {task_key}")
    payload = run_bridge("feishu_task_task", "get", {"task_guid": guid})
    details = details_of(payload)
    task = details.get("task")
    if not isinstance(task, dict):
        raise SystemExit(f"failed to load task details: {task_key}")
    return task


def get_task_record_by_guid(
    task_guid: str,
    *,
    run_bridge: RunBridgeFn,
    details_of: DetailsFn,
    maybe_normalize_task_summary: MaybeNormalizeFn,
) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    if not guid:
        raise SystemExit("task guid is required")
    payload = run_bridge("feishu_task_task", "get", {"task_guid": guid})
    details = details_of(payload)
    task = details.get("task")
    if not isinstance(task, dict):
        raise SystemExit(f"failed to load task details by guid: {guid}")
    maybe_normalize_task_summary(task, fetch_description_if_needed=False, allow_patch=False)
    return task


def build_description(
    task_id: str,
    summary: str,
    request: str,
    repo_root: str,
    kind: str,
    *,
    now_text: NowTextFn,
    description_requirements: DescriptionRequirementsFn,
) -> str:
    lines = [
        f"任务编号：{task_id}",
        f"创建时间：{now_text()}",
        f"类型：{kind}",
        f"Repo：{repo_root}",
        "",
        "需求：",
        request.strip() or summary.strip(),
        "",
        "执行要求：",
    ]
    for item in description_requirements():
        text = str(item or "").strip()
        if text:
            lines.append(f"- {text}")
    return "\n".join(lines).strip()


def current_head_commit_url(root: str) -> str:
    repo = str(root or "").strip()
    if not repo:
        return ""
    try:
        sha_proc = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
        remote_proc = subprocess.run(["git", "-C", repo, "remote", "get-url", "origin"], capture_output=True, text=True, check=False)
    except OSError:
        return ""
    sha = sha_proc.stdout.strip() if sha_proc.returncode == 0 else ""
    remote_url = remote_proc.stdout.strip() if remote_proc.returncode == 0 else ""
    if not sha or not remote_url:
        return ""
    normalized_remote = remote_url
    if normalized_remote.startswith("git@"):
        normalized_remote = normalized_remote.replace(":", "/", 1)
        normalized_remote = normalized_remote.replace("git@", "https://", 1)
    if normalized_remote.startswith("ssh://git@"):
        normalized_remote = normalized_remote.replace("ssh://git@", "https://", 1)
    normalized_remote = normalized_remote.rstrip("/")
    if normalized_remote.endswith(".git"):
        normalized_remote = normalized_remote[:-4]
    if not normalized_remote.startswith(("http://", "https://")):
        return ""
    return f"{normalized_remote}/commit/{sha}"


def build_completion_comment(content: str, commit_url: str, uploaded_count: int) -> str:
    lines: list[str] = []
    text = (content or "").strip()
    if text:
        lines.append(text)
    elif commit_url or uploaded_count:
        lines.append("任务完成")
    if uploaded_count:
        lines.append(f"附件：已上传 {uploaded_count} 个")
    if commit_url:
        lines.append(f"Commit：{commit_url}")
    return "\n".join(lines).strip()
