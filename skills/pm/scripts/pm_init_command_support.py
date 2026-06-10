from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pm_command_support import (
    current_doc_backend,
    current_doc_cfg,
    current_project_cfg,
    current_task_backend,
    current_task_cfg,
    emit_json,
    resolve_doc_folder_name,
    resolve_tasklist_name,
)


def _emit(payload: dict[str, Any]) -> int:
    return emit_json(payload)


def _resolve_project_identity(api: Any, args: argparse.Namespace, root: Path) -> dict[str, str]:
    configured_project_name = str(current_project_cfg(api).get("name") or "").strip()
    if configured_project_name in {"", "未命名项目"}:
        configured_project_name = ""
    project_name = str(args.project_name or configured_project_name or root.name).strip() or root.name
    english_name = ""
    if str(args.english_name or "").strip():
        english_name = api.english_project_name(project_name, args.english_name, "")
    return {
        "project_name": project_name,
        "english_name": english_name,
    }


def _resolve_init_names(api: Any, args: argparse.Namespace, root: Path, identity: dict[str, str]) -> dict[str, str]:
    resolved_tasklist_name = resolve_tasklist_name(
        api,
        root,
        identity["project_name"],
        explicit_name=str(args.tasklist_name or "").strip(),
        english_name=identity["english_name"],
        agent_id="",
    )
    resolved_doc_folder_name = resolve_doc_folder_name(
        api,
        root,
        identity["project_name"],
        explicit_name=str(args.doc_folder_name or "").strip(),
        english_name=identity["english_name"],
        agent_id="",
    )
    configured_tasklist_guid = str(args.tasklist_guid or current_task_cfg(api).get("tasklist_guid") or "").strip()
    configured_doc_folder_token = str(args.doc_folder_token or current_doc_cfg(api).get("folder_token") or "").strip()
    return {
        "resolved_tasklist_name": resolved_tasklist_name,
        "resolved_doc_folder_name": resolved_doc_folder_name,
        "configured_tasklist_guid": configured_tasklist_guid,
        "configured_doc_folder_token": configured_doc_folder_token,
    }


def _prime_active_config(
    api: Any,
    *,
    root: Path,
    resolved_tasklist_name: str,
    configured_tasklist_guid: str,
    resolved_doc_folder_name: str,
    configured_doc_folder_token: str,
) -> None:
    api.ACTIVE_CONFIG["repo_root"] = str(root)
    api.ACTIVE_CONFIG.setdefault("task", {})
    if isinstance(api.ACTIVE_CONFIG.get("task"), dict):
        api.ACTIVE_CONFIG["task"]["tasklist_name"] = resolved_tasklist_name
        if configured_tasklist_guid:
            api.ACTIVE_CONFIG["task"]["tasklist_guid"] = configured_tasklist_guid
    api.ACTIVE_CONFIG["tasklist_name"] = resolved_tasklist_name
    api.ACTIVE_CONFIG.setdefault("doc", {})
    if isinstance(api.ACTIVE_CONFIG.get("doc"), dict):
        api.ACTIVE_CONFIG["doc"]["folder_name"] = resolved_doc_folder_name
        if configured_doc_folder_token:
            api.ACTIVE_CONFIG["doc"]["folder_token"] = configured_doc_folder_token


def _resolve_backends_and_auth(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    resolved_task_backend = str(args.task_backend or current_task_backend(api)).strip() or "feishu"
    resolved_doc_backend = str(args.doc_backend or current_doc_backend(api)).strip() or "feishu"
    auth_bundle = {
        "status": "skipped",
        "reason": "lark_cli_auth_managed_externally",
        "hint": "run `pm lark status` or `pm lark login --exec` to initialize official lark-cli auth",
    }
    return {
        "resolved_task_backend": resolved_task_backend,
        "resolved_doc_backend": resolved_doc_backend,
        "auth_bundle": auth_bundle,
    }


def _build_init_config_payload(
    api: Any,
    args: argparse.Namespace,
    *,
    root: Path,
    identity: dict[str, str],
    resolved_tasklist_name: str,
    resolved_doc_folder_name: str,
    configured_tasklist_guid: str,
    configured_doc_folder_token: str,
    resolved_task_backend: str,
    resolved_doc_backend: str,
) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    api.ACTIVE_CONFIG.setdefault("task", {})
    if isinstance(api.ACTIVE_CONFIG.get("task"), dict):
        api.ACTIVE_CONFIG["task"]["backend"] = resolved_task_backend
    api.ACTIVE_CONFIG.setdefault("doc", {})
    if isinstance(api.ACTIVE_CONFIG.get("doc"), dict):
        api.ACTIVE_CONFIG["doc"]["backend"] = resolved_doc_backend

    task_inspection = api.inspect_tasklist(resolved_tasklist_name, configured_guid=configured_tasklist_guid)
    config_path = api.resolve_config_path(args.config)
    config_payload = {key: value for key, value in api.ACTIVE_CONFIG.items() if not str(key).startswith("_")}
    config_payload["repo_root"] = str(root)
    config_payload.setdefault("repo", {})
    if isinstance(config_payload["repo"], dict):
        config_payload["repo"]["root"] = str(root)
    config_payload.setdefault("task", {})
    if isinstance(config_payload["task"], dict):
        config_payload["task"]["backend"] = resolved_task_backend
        config_payload["task"]["tasklist_name"] = resolved_tasklist_name
        config_payload["task"].setdefault("prefix", api.task_prefix())
        config_payload["task"].setdefault("kind", api.task_kind())
        if configured_tasklist_guid:
            config_payload["task"]["tasklist_guid"] = configured_tasklist_guid
        config_payload.setdefault("tasklist_name", config_payload["task"]["tasklist_name"])
        config_payload.setdefault("task_prefix", config_payload["task"]["prefix"])
        config_payload.setdefault("kind", config_payload["task"]["kind"])
    config_payload.setdefault("doc", api.default_config()["doc"])
    if isinstance(config_payload["doc"], dict):
        config_payload["doc"]["backend"] = resolved_doc_backend
        config_payload["doc"]["folder_name"] = resolved_doc_folder_name
        if configured_doc_folder_token:
            config_payload["doc"]["folder_token"] = configured_doc_folder_token
        config_payload["doc"].setdefault("project_title", "PROJECT")
        config_payload["doc"].setdefault("requirements_title", "REQUIREMENTS")
        config_payload["doc"].setdefault("roadmap_title", "ROADMAP")
        config_payload["doc"].setdefault("state_title", "STATE")
    config_payload.setdefault("coder", api.default_config()["coder"])
    if isinstance(config_payload["coder"], dict):
        config_payload["coder"].setdefault("backend", "codex")
        config_payload["coder"].setdefault("agent_id", "codex")
        config_payload["coder"].setdefault("timeout", 900)
        config_payload["coder"].setdefault("thinking", "high")
        config_payload["coder"].setdefault("session_key", "main")
    config_payload.setdefault("project", {})
    if isinstance(config_payload["project"], dict):
        current_name = str(config_payload["project"].get("name") or "").strip()
        if not current_name or current_name == "未命名项目":
            config_payload["project"]["name"] = identity["project_name"]
    return config_path, config_payload, task_inspection


def _skipped_project_review_registration(reason: str = "repo_local_init_only") -> dict[str, Any]:
    return {"status": "skipped", "reason": reason}


def _init_warnings(args: argparse.Namespace) -> list[str]:
    warnings: list[str] = []
    if str(args.tasklist_name or "").strip():
        warnings.append("`--tasklist-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
    if str(args.doc_folder_name or "").strip():
        warnings.append("`--doc-folder-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
    return warnings


def _sync_repo_contract(
    api: Any,
    *,
    root: Path,
    config_path: Path,
    tasklist_name: str,
    doc_folder_name: str,
    default_worker: str,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {
            "status": "dry_run",
            "path": str(root / "AGENTS.md"),
        }
    sync = getattr(api, "sync_repo_agents_contract", None)
    if not callable(sync):
        return {"status": "skipped", "reason": "helper_unavailable"}
    path = sync(
        repo_root=root,
        pm_config_path=str(config_path),
        tasklist_name=tasklist_name,
        doc_folder_name=doc_folder_name,
        default_worker=default_worker,
        preferred_ui_worker="gemini",
    )
    return {"status": "updated", "path": str(path)}


def cmd_init(api: Any, args: argparse.Namespace) -> int:
    root = api.project_root_path(args.repo_root)
    repo_config_path = root / "pm.json"
    args.config = str(repo_config_path)

    identity = _resolve_project_identity(api, args, root)
    names = _resolve_init_names(api, args, root, identity)
    _prime_active_config(
        api,
        root=root,
        resolved_tasklist_name=names["resolved_tasklist_name"],
        configured_tasklist_guid=names["configured_tasklist_guid"],
        resolved_doc_folder_name=names["resolved_doc_folder_name"],
        configured_doc_folder_token=names["configured_doc_folder_token"],
    )
    backend_state = _resolve_backends_and_auth(api, args)
    config_path, config_payload, task_inspection = _build_init_config_payload(
        api,
        args,
        root=root,
        identity=identity,
        resolved_tasklist_name=names["resolved_tasklist_name"],
        resolved_doc_folder_name=names["resolved_doc_folder_name"],
        configured_tasklist_guid=names["configured_tasklist_guid"],
        configured_doc_folder_token=names["configured_doc_folder_token"],
        resolved_task_backend=backend_state["resolved_task_backend"],
        resolved_doc_backend=backend_state["resolved_doc_backend"],
    )
    main_review_registration = _skipped_project_review_registration()
    main_digest_registration = main_review_registration
    nightly_review_registration = _skipped_project_review_registration("repo_local_init_only")
    warnings = _init_warnings(args)
    repo_contract = _sync_repo_contract(
        api,
        root=root,
        config_path=config_path,
        tasklist_name=names["resolved_tasklist_name"],
        doc_folder_name=names["resolved_doc_folder_name"],
        default_worker=str(args.default_worker or "codex").strip() or "codex",
        dry_run=bool(args.dry_run),
    )

    if args.dry_run:
        api.ACTIVE_CONFIG.update(config_payload)
        docs_preview = api.ensure_project_docs(root, dry_run=True)
        return _emit(
            {
                "status": "dry_run",
                "warnings": warnings,
                "config_path": str(config_path),
                "repo_root": str(root),
                "project_name": identity["project_name"],
                "naming_mode": "project_name_default"
                if not (str(args.tasklist_name or "").strip() or str(args.doc_folder_name or "").strip())
                else "explicit_override",
                "resolved_tasklist_name": names["resolved_tasklist_name"],
                "resolved_doc_folder_name": names["resolved_doc_folder_name"],
                "tasklist_inspection": task_inspection,
                "docs_preview": docs_preview,
                "repo_contract": repo_contract,
                "auth_bundle": backend_state["auth_bundle"],
                "main_review_registration": main_review_registration,
                "main_digest_registration": main_digest_registration,
                "nightly_review_registration": nightly_review_registration,
                "config_preview": config_payload,
            }
        )

    tasklist = api.ensure_tasklist(names["resolved_tasklist_name"])
    tasklist_guid = str(tasklist.get("guid") or "").strip()
    tasklist_url = str(tasklist.get("url") or "").strip()
    tasklist_owner = tasklist.get("owner") if isinstance(tasklist.get("owner"), dict) else {}
    tasklist_owner_id = str(tasklist_owner.get("id") or "").strip()
    if isinstance(config_payload.get("task"), dict):
        if tasklist_guid:
            config_payload["task"]["tasklist_guid"] = tasklist_guid
        if tasklist_url:
            config_payload["task"]["tasklist_url"] = tasklist_url
        if tasklist_owner_id:
            config_payload["task"].setdefault("default_assignee", tasklist_owner_id)
    api.ACTIVE_CONFIG.update(config_payload)
    docs = api.ensure_project_docs(root)
    if isinstance(config_payload.get("doc"), dict):
        config_payload["doc"].update(docs)
    api.ACTIVE_CONFIG.update(config_payload)
    api.ensure_pm_dir(str(root))
    if args.write_config or not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    bootstrap_task = api.ensure_bootstrap_task(root)
    selected_task_id = str(((bootstrap_task or {}).get("task") or {}).get("task_id") or "").strip()
    selected_task_guid = str(((bootstrap_task or {}).get("task") or {}).get("guid") or "").strip()
    payload = api.refresh_context_cache(task_id=selected_task_id, task_guid=selected_task_guid)
    return _emit(
        {
            "status": "initialized",
            "warnings": warnings,
            "config_path": str(config_path),
            "repo_root": str(root),
            "pm_dir": str(api.pm_dir_path(str(root))),
            "project_name": identity["project_name"],
            "naming_mode": "project_name_default"
            if not (str(args.tasklist_name or "").strip() or str(args.doc_folder_name or "").strip())
            else "explicit_override",
            "tasklist": tasklist,
            "tasklist_inspection": task_inspection,
            "bootstrap_task": bootstrap_task,
            "context_path": str(api.pm_file("current-context.json", str(root))),
            "project_scan_path": str(api.pm_file("project-scan.json", str(root))),
            "repo_scan": payload.get("repo_scan") or {},
            "doc_index": payload.get("doc_index") or {},
            "repo_contract": repo_contract,
            "auth_bundle": backend_state["auth_bundle"],
            "main_review_registration": main_review_registration,
            "main_digest_registration": main_digest_registration,
            "nightly_review_registration": nightly_review_registration,
        }
    )
