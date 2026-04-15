from __future__ import annotations

from typing import Any


def normalize_task_members(members: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    ordered_ids: list[str] = []
    roles_by_id: dict[str, str] = {}

    for item in members or []:
        if not isinstance(item, dict):
            continue
        member_id = str(item.get("id") or "").strip()
        if not member_id:
            continue
        role = str(item.get("role") or "assignee").strip().lower()
        normalized_role = role if role in {"assignee", "follower"} else "assignee"
        if member_id not in roles_by_id:
            ordered_ids.append(member_id)
            roles_by_id[member_id] = normalized_role
            continue
        if normalized_role == "assignee":
            roles_by_id[member_id] = "assignee"

    return [{"id": member_id, "role": roles_by_id[member_id]} for member_id in ordered_ids]


def resolve_default_task_members(
    *,
    task_config: dict[str, Any] | None,
    current_user_id: str = "",
) -> list[dict[str, str]]:
    configured = task_config if isinstance(task_config, dict) else {}
    requested_members: list[dict[str, Any]] = []

    default_members = configured.get("default_members")
    if isinstance(default_members, list):
        requested_members.extend(item for item in default_members if isinstance(item, dict))

    default_assignees = configured.get("default_assignees")
    if isinstance(default_assignees, list):
        for item in default_assignees:
            member_id = str(item or "").strip()
            if member_id:
                requested_members.append({"id": member_id, "role": "assignee"})

    default_assignee = str(configured.get("default_assignee") or "").strip()
    if default_assignee:
        requested_members.append({"id": default_assignee, "role": "assignee"})

    normalized = normalize_task_members(requested_members)
    has_assignee = any(str(item.get("role") or "") == "assignee" for item in normalized)
    current_id = str(current_user_id or "").strip()
    if not current_id:
        return normalized
    if not has_assignee:
        normalized.append({"id": current_id, "role": "assignee"})
        return normalize_task_members(normalized)
    if not any(str(item.get("id") or "").strip() == current_id for item in normalized):
        normalized.append({"id": current_id, "role": "follower"})
    return normalize_task_members(normalized)
