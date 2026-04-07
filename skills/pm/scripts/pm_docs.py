from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

BridgeFn = Callable[..., dict[str, Any]]
DetailsFn = Callable[[dict[str, Any]], dict[str, Any]]


def _normalize_name(name: str) -> str:
    return " ".join(str(name or "").split()).strip()


def list_drive_files(run_bridge: BridgeFn, details_of: DetailsFn, *, folder_token: str = "") -> list[dict[str, Any]]:
    page_token = ""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    while True:
        args: dict[str, Any] = {"page_size": 200}
        if folder_token:
            args["folder_token"] = folder_token
        if page_token:
            args["page_token"] = page_token
        payload = run_bridge("feishu_drive_file", "list", args)
        details = details_of(payload)
        for item in details.get("files") or []:
            if not isinstance(item, dict):
                continue
            token = str(item.get("token") or item.get("file_token") or "").strip()
            if token and token not in seen:
                rows.append(item)
                seen.add(token)
        page_token = str(details.get("page_token") or "").strip()
        if not details.get("has_more") or not page_token:
            break
    return rows


def _candidate_text(items: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for item in items:
        parts.append(
            f"{str(item.get('name') or '').strip()} | token={str(item.get('token') or item.get('file_token') or '').strip()} | "
            f"url={str(item.get('url') or '').strip() or '-'}"
        )
    return "; ".join(parts)


def find_root_folders_by_name(run_bridge: BridgeFn, details_of: DetailsFn, name: str) -> list[dict[str, Any]]:
    normalized = _normalize_name(name)
    if not normalized:
        return []
    matches: list[dict[str, Any]] = []
    for item in list_drive_files(run_bridge, details_of):
        if str(item.get("type") or "") != "folder":
            continue
        if _normalize_name(str(item.get("name") or "")) != normalized:
            continue
        matches.append(item)
    return matches


def find_root_folder_by_name(run_bridge: BridgeFn, details_of: DetailsFn, name: str) -> dict[str, Any] | None:
    matches = find_root_folders_by_name(run_bridge, details_of, name)
    return matches[0] if len(matches) == 1 else None


def find_files_in_folder_by_name(
    run_bridge: BridgeFn,
    details_of: DetailsFn,
    *,
    folder_token: str,
    name: str,
    allowed_types: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    normalized = _normalize_name(name)
    if not folder_token or not normalized:
        return []
    matches: list[dict[str, Any]] = []
    for item in list_drive_files(run_bridge, details_of, folder_token=folder_token):
        item_type = str(item.get("type") or "").strip()
        if allowed_types and item_type not in allowed_types:
            continue
        if _normalize_name(str(item.get("name") or "")) != normalized:
            continue
        matches.append(item)
    return matches


def extract_drive_node(details_of: DetailsFn, payload: dict[str, Any]) -> dict[str, Any]:
    details = details_of(payload)
    for key in ("file", "folder", "node", "meta"):
        value = details.get(key)
        if isinstance(value, dict):
            return value
    return details if isinstance(details, dict) else {}


def create_root_folder(run_bridge: BridgeFn, details_of: DetailsFn, name: str) -> dict[str, Any]:
    payload = run_bridge("feishu_drive_file", "create_folder", {"name": name, "folder_token": ""})
    node = extract_drive_node(details_of, payload)
    token = str(node.get("token") or node.get("file_token") or "").strip()
    if token:
        return node
    found = find_root_folder_by_name(run_bridge, details_of, name)
    if isinstance(found, dict):
        return found
    raise SystemExit(f"failed to create folder: {name}")


def create_doc(run_bridge: BridgeFn, details_of: DetailsFn, title: str, markdown: str, *, folder_token: str = "") -> dict[str, Any]:
    args = {"title": title, "markdown": markdown}
    if folder_token:
        args["folder_token"] = folder_token
    payload = run_bridge("feishu_create_doc", "", args)
    return details_of(payload)


def update_doc(
    run_bridge: BridgeFn,
    details_of: DetailsFn,
    doc_id: str,
    markdown: str,
    *,
    mode: str = "overwrite",
    new_title: str = "",
) -> dict[str, Any]:
    args: dict[str, Any] = {
        "doc_id": doc_id,
        "mode": mode,
        "markdown": markdown,
    }
    if new_title:
        args["new_title"] = new_title
    payload = run_bridge("feishu_update_doc", "", args)
    return details_of(payload)


def ensure_project_docs(
    run_bridge: BridgeFn,
    details_of: DetailsFn,
    *,
    root: Path,
    cfg: dict[str, Any],
    folder_name: str,
    titles: dict[str, str],
    project_name: str,
    project_mode: str,
    bootstrap_action: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    folder_token = str(cfg.get("folder_token") or "").strip()
    folder_url = str(cfg.get("folder_url") or "").strip()
    folder_created = False
    folder_status = "configured" if folder_token else "missing"
    if not folder_token:
        folder_matches = find_root_folders_by_name(run_bridge, details_of, folder_name)
        if len(folder_matches) == 1:
            found = folder_matches[0]
            folder_token = str(found.get("token") or found.get("file_token") or "").strip()
            folder_url = str(found.get("url") or "").strip()
            folder_status = "adopted"
        elif len(folder_matches) > 1:
            raise SystemExit(f"multiple Feishu folders matched '{folder_name}': {_candidate_text(folder_matches)}")
        elif dry_run:
            folder_status = "missing"
        else:
            created_folder = create_root_folder(run_bridge, details_of, folder_name)
            folder_token = str(created_folder.get("token") or created_folder.get("file_token") or "").strip()
            folder_url = str(created_folder.get("url") or "").strip()
            folder_created = bool(folder_token)
            folder_status = "created" if folder_created else "missing"
    tokens = {
        "project_doc_token": str(cfg.get("project_doc_token") or "").strip(),
        "requirements_doc_token": str(cfg.get("requirements_doc_token") or "").strip(),
        "roadmap_doc_token": str(cfg.get("roadmap_doc_token") or "").strip(),
        "state_doc_token": str(cfg.get("state_doc_token") or "").strip(),
    }
    urls = {
        "project_doc_url": str(cfg.get("project_doc_url") or "").strip(),
        "requirements_doc_url": str(cfg.get("requirements_doc_url") or "").strip(),
        "roadmap_doc_url": str(cfg.get("roadmap_doc_url") or "").strip(),
        "state_doc_url": str(cfg.get("state_doc_url") or "").strip(),
    }
    doc_statuses = {
        "project_doc_status": "configured" if tokens["project_doc_token"] else "missing",
        "requirements_doc_status": "configured" if tokens["requirements_doc_token"] else "missing",
        "roadmap_doc_status": "configured" if tokens["roadmap_doc_token"] else "missing",
        "state_doc_status": "configured" if tokens["state_doc_token"] else "missing",
    }

    def ensure_named_doc(key: str, title: str, markdown: str) -> None:
        token_key = f"{key}_doc_token"
        url_key = f"{key}_doc_url"
        status_key = f"{key}_doc_status"
        if tokens[token_key]:
            return
        matches = find_files_in_folder_by_name(
            run_bridge,
            details_of,
            folder_token=folder_token,
            name=title,
            allowed_types=("doc", "docx"),
        )
        if len(matches) == 1:
            found = matches[0]
            tokens[token_key] = str(found.get("token") or found.get("file_token") or "").strip()
            urls[url_key] = str(found.get("url") or "").strip()
            doc_statuses[status_key] = "adopted"
            return
        if len(matches) > 1:
            raise SystemExit(f"multiple Feishu docs matched '{title}' in folder '{folder_name}': {_candidate_text(matches)}")
        if dry_run or not folder_token:
            doc_statuses[status_key] = "missing"
            return
        created = create_doc(run_bridge, details_of, title, markdown, folder_token=folder_token)
        tokens[token_key] = str(created.get("doc_id") or "").strip()
        urls[url_key] = str(created.get("doc_url") or "").strip()
        doc_statuses[status_key] = "created"

    project_md = f"# {project_name}\n\n- 仓库：`{root}`\n- 项目模式：{project_mode}\n"
    requirements_md = f"# {project_name} REQUIREMENTS\n\n- 当前状态：等待 GSD requirements 同步。\n"
    roadmap_md = f"# {project_name} ROADMAP\n\n- 当前建议动作：{bootstrap_action}\n- 后续可在此沉淀阶段规划与里程碑。\n"
    state_md = f"# {project_name} STATE\n\n- 当前状态：已初始化 PM\n- next：{bootstrap_action}\n"
    ensure_named_doc("project", titles["project"], project_md)
    ensure_named_doc("requirements", titles["requirements"], requirements_md)
    ensure_named_doc("roadmap", titles["roadmap"], roadmap_md)
    ensure_named_doc("state", titles["state"], state_md)
    return {
        "dry_run": dry_run,
        "folder_name": folder_name,
        "folder_token": folder_token,
        "folder_url": folder_url,
        "folder_created": folder_created,
        "folder_status": folder_status,
        **titles,
        **tokens,
        **urls,
        **doc_statuses,
    }
