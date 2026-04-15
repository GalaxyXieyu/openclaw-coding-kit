from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable


CommandHandler = Callable[[argparse.Namespace], int]


def emit_json(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def task_summary_text(item: dict[str, Any]) -> str:
    return str(item.get("normalized_summary") or item.get("summary") or "").strip()


def current_task_cfg(api: Any) -> dict[str, Any]:
    value = api.ACTIVE_CONFIG.get("task")
    return value if isinstance(value, dict) else {}


def current_doc_cfg(api: Any) -> dict[str, Any]:
    value = api.ACTIVE_CONFIG.get("doc")
    return value if isinstance(value, dict) else {}


def current_project_cfg(api: Any) -> dict[str, Any]:
    value = api.ACTIVE_CONFIG.get("project")
    return value if isinstance(value, dict) else {}


def current_task_backend(api: Any) -> str:
    return str(current_task_cfg(api).get("backend") or api.default_config()["task"]["backend"]).strip() or "feishu"


def current_doc_backend(api: Any) -> str:
    return str(current_doc_cfg(api).get("backend") or api.default_config()["doc"]["backend"]).strip() or "feishu"


def safe_project_label(api: Any, project_name: str, english_name: str = "", agent_id: str = "") -> str:
    try:
        return str(api.project_display_name(project_name, english_name, agent_id)).strip()
    except Exception:
        return str(project_name or "").strip()


def resolve_tasklist_name(
    api: Any,
    root: Any,
    project_name: str,
    *,
    explicit_name: str = "",
    english_name: str = "",
    agent_id: str = "",
) -> str:
    explicit = str(explicit_name or "").strip()
    if explicit:
        return explicit
    task_cfg = current_task_cfg(api)
    current_name = str(task_cfg.get("tasklist_name") or api.ACTIVE_CONFIG.get("tasklist_name") or "").strip()
    current_guid = str(task_cfg.get("tasklist_guid") or "").strip()
    config_exists = bool(Path(str(api.ACTIVE_CONFIG.get("_config_path") or "")).exists())
    legacy_names = {
        str(api.default_config()["task"].get("tasklist_name") or "").strip(),
        str(api.default_config().get("tasklist_name") or "").strip(),
    }
    if current_guid and current_name:
        return current_name
    if current_name and config_exists:
        inspection = api.inspect_tasklist(current_name, configured_guid=current_guid)
        if str(inspection.get("status") or "") in {"configured_match", "unique_match"}:
            return current_name
    if current_name and current_name not in legacy_names:
        return current_name
    try:
        return str(api.default_tasklist_name(project_name, english_name, agent_id)).strip()
    except Exception:
        return safe_project_label(api, project_name, english_name, agent_id) or str(root.name)


def resolve_doc_folder_name(
    api: Any,
    root: Any,
    project_name: str,
    *,
    explicit_name: str = "",
    english_name: str = "",
    agent_id: str = "",
) -> str:
    explicit = str(explicit_name or "").strip()
    if explicit:
        return explicit
    doc_cfg = current_doc_cfg(api)
    current_name = str(doc_cfg.get("folder_name") or "").strip()
    current_token = str(doc_cfg.get("folder_token") or "").strip()
    config_exists = bool(Path(str(api.ACTIVE_CONFIG.get("_config_path") or "")).exists())
    legacy_names = {
        str(api.default_config()["doc"].get("folder_name") or "").strip(),
        str(root.name or "").strip(),
        f"{root.name} Docs",
    }
    if current_token and current_name:
        return current_name
    if current_name and config_exists:
        return current_name
    if current_name and current_name not in legacy_names:
        return current_name
    try:
        return str(api.default_doc_folder_name(project_name, english_name, agent_id)).strip()
    except Exception:
        return safe_project_label(api, project_name, english_name, agent_id) or str(root.name)
