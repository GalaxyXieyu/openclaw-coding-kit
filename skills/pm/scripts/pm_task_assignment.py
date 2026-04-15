from __future__ import annotations

import json
import urllib.parse
from typing import Any, Callable, Tuple

from pm_task_members import normalize_task_members

EnsureUserTokenFn = Callable[[tuple[str, ...]], dict[str, Any]]
BuildAuthLinkFn = Callable[..., dict[str, Any]]
RequestUserOAuthLinkFn = Callable[..., dict[str, Any]]
TaskIdForOutputFn = Callable[[str], str]
FeishuCredentialsFn = Callable[[], dict[str, str]]
RequestJsonFn = Callable[..., Tuple[int, dict[str, Any], str]]

DEFAULT_TASK_ASSIGNMENT_SCOPES = (
    "task:task:read",
    "task:task:write",
    "offline_access",
)


def _unwrap_token_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    token_payload = payload if isinstance(payload, dict) else {}
    nested = token_payload.get("token")
    if isinstance(nested, dict):
        return nested
    return token_payload


def task_assignment_auth_result(
    *,
    ensure_user_token: EnsureUserTokenFn,
    build_auth_link: BuildAuthLinkFn,
    request_user_oauth_link: RequestUserOAuthLinkFn,
) -> dict[str, Any]:
    try:
        raw_payload = ensure_user_token(DEFAULT_TASK_ASSIGNMENT_SCOPES)
        raw_status = str(raw_payload.get("status") or "").strip() if isinstance(raw_payload, dict) else ""
        token_payload = _unwrap_token_payload(raw_payload)
        access_token = str(token_payload.get("access_token") or "").strip()
        if raw_status and raw_status != "authorized" and not access_token:
            result = {
                "status": "authorization_required",
                "auth": build_auth_link(scopes=list(DEFAULT_TASK_ASSIGNMENT_SCOPES), token_type="user"),
                "oauth": request_user_oauth_link(scopes=list(DEFAULT_TASK_ASSIGNMENT_SCOPES)),
            }
            if isinstance(raw_payload, dict):
                for key, value in raw_payload.items():
                    if key not in {"status", "token"}:
                        result[key] = value
            return result
        return {
            "status": "authorized",
            "token": access_token,
            "token_payload": token_payload,
            "open_id": str(token_payload.get("open_id") or "").strip(),
        }
    except SystemExit as exc:
        message = str(exc)
        return {
            "status": "authorization_required",
            "message": message,
            "auth": build_auth_link(scopes=list(DEFAULT_TASK_ASSIGNMENT_SCOPES), token_type="user"),
            "oauth": request_user_oauth_link(scopes=list(DEFAULT_TASK_ASSIGNMENT_SCOPES)),
        }


def plan_task_assignee_backfill(
    task: dict[str, Any],
    desired_members: list[dict[str, Any]] | None,
    *,
    creator_only_user_id: str = "",
) -> dict[str, Any]:
    desired = normalize_task_members(desired_members)
    desired_assignees = [item for item in desired if str(item.get("role") or "") == "assignee"]
    if not desired_assignees:
        return {"action": "skip", "reason": "no_desired_assignee"}

    creator_id = str(((task.get("creator") or {}) if isinstance(task.get("creator"), dict) else {}).get("id") or "").strip()
    if creator_only_user_id and creator_id and creator_id != str(creator_only_user_id).strip():
        return {"action": "skip", "reason": "creator_mismatch", "creator_id": creator_id}

    current_members = normalize_task_members(task.get("members") if isinstance(task.get("members"), list) else [])
    current_assignees = {str(item.get("id") or "").strip() for item in current_members if str(item.get("role") or "") == "assignee"}
    if current_assignees:
        return {"action": "skip", "reason": "already_has_assignee", "current_assignees": sorted(item for item in current_assignees if item)}

    current_roles = {str(item.get("id") or "").strip(): str(item.get("role") or "").strip() for item in current_members}
    blocked: list[dict[str, str]] = []
    to_add: list[dict[str, str]] = []
    for item in desired_assignees:
        member_id = str(item.get("id") or "").strip()
        if not member_id:
            continue
        current_role = current_roles.get(member_id, "")
        if current_role and current_role != "assignee":
            blocked.append({"id": member_id, "current_role": current_role, "target_role": "assignee"})
            continue
        if not current_role:
            to_add.append({"id": member_id, "role": "assignee"})

    if blocked:
        return {"action": "skip", "reason": "role_change_required", "blocked_members": blocked}
    if not to_add:
        return {"action": "skip", "reason": "nothing_to_add"}
    return {"action": "add_members", "members": to_add}


def add_task_members(
    task: dict[str, Any],
    task_id: str,
    members: list[dict[str, Any]],
    *,
    task_id_for_output_fn: TaskIdForOutputFn,
    auth_result_fn: Callable[[], dict[str, Any]],
    feishu_credentials: FeishuCredentialsFn,
    request_json: RequestJsonFn,
) -> dict[str, Any]:
    auth = auth_result_fn()
    if auth.get("status") != "authorized":
        auth["task_id"] = task_id_for_output_fn(task_id)
        auth["task_guid"] = str(task.get("guid") or "").strip()
        auth["members"] = normalize_task_members(members)
        return auth

    task_guid = str(task.get("guid") or "").strip()
    if not task_guid:
        raise SystemExit(f"task missing guid: {task_id_for_output_fn(task_id)}")

    token = str(auth.get("token") or "").strip()
    if not token:
        raise SystemExit("missing user access token for task assignment")

    payload_body = json.dumps(
        {
            "members": normalize_task_members(members),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    openapi_base = feishu_credentials()["openapi_base"]
    status, payload, raw = request_json(
        f"{openapi_base}/open-apis/task/v2/tasks/{urllib.parse.quote(task_guid)}/add_members?user_id_type=open_id",
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        body=payload_body,
    )
    if status >= 400 or int(payload.get("code") or 0) != 0:
        raise SystemExit(f"failed to add task members: {raw}")

    data = payload.get("data")
    task_payload = data.get("task") if isinstance(data, dict) else {}
    return {
        "status": "ok",
        "task_id": task_id_for_output_fn(task_id),
        "task_guid": task_guid,
        "members": normalize_task_members(members),
        "task": task_payload if isinstance(task_payload, dict) else {},
    }
