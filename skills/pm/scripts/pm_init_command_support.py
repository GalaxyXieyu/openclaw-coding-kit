from __future__ import annotations

import argparse
import json
import re
import shutil
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


def _clear_nested_keys(payload: dict[str, Any], path: str, cleared: list[str]) -> None:
    parts = path.split(".")
    cursor: Any = payload
    for key in parts[:-1]:
        if not isinstance(cursor, dict):
            return
        cursor = cursor.get(key)
    if isinstance(cursor, dict) and parts[-1] in cursor:
        cursor.pop(parts[-1], None)
        cleared.append(path)


def _cleanup_repo_config_for_workspace_delete(config_payload: dict[str, Any]) -> list[str]:
    cleared: list[str] = []
    for path in (
        "project.agent",
        "task.tasklist_guid",
        "task.tasklist_url",
        "task.default_assignee",
        "doc.folder_token",
        "doc.folder_url",
        "doc.project_doc_token",
        "doc.project_doc_url",
        "doc.requirements_doc_token",
        "doc.requirements_doc_url",
        "doc.roadmap_doc_token",
        "doc.roadmap_doc_url",
        "doc.state_doc_token",
        "doc.state_doc_url",
    ):
        _clear_nested_keys(config_payload, path, cleared)
    return cleared


def cmd_auth_link(api: Any, args: argparse.Namespace) -> int:
    raw = [item.strip() for item in re.split(r"[\s,]+", args.scopes or "") if item.strip()]
    if not raw:
        raise SystemExit("provide --scopes, e.g. --scopes drive:drive offline_access")
    if args.mode == "user-oauth":
        payload = api.request_user_oauth_link(scopes=raw)
    else:
        payload = api.build_auth_link(scopes=raw, token_type=args.token_type)
    return _emit(payload)


def cmd_permission_bundle(api: Any, args: argparse.Namespace) -> int:
    if args.list_presets:
        return _emit({"presets": api.list_app_scope_presets()})
    payload = api.build_permission_bundle(
        preset_names=list(args.preset or []),
        scopes=list(args.scope or []),
        token_type=args.token_type,
    )
    return _emit(payload)


def cmd_auth(api: Any, args: argparse.Namespace) -> int:
    payload = api.build_auth_bundle(
        include_group_open_reply=not bool(args.no_group_open_reply),
        include_attachment_oauth=not bool(args.no_attachment_oauth),
    )
    return _emit(payload)


def _resolve_project_identity(api: Any, args: argparse.Namespace, root: Path) -> dict[str, str]:
    configured_project_name = str(current_project_cfg(api).get("name") or "").strip()
    if configured_project_name in {"", "未命名项目"}:
        configured_project_name = ""
    project_name = str(args.project_name or configured_project_name or root.name).strip() or root.name
    group_id = str(args.group_id or "").strip()
    english_name = ""
    agent_id = ""
    if group_id or str(args.english_name or "").strip() or str(args.agent_id or "").strip():
        english_name = api.english_project_name(project_name, args.english_name, args.agent_id)
        agent_id = api.project_slug(project_name, english_name, args.agent_id)
    return {
        "project_name": project_name,
        "group_id": group_id,
        "english_name": english_name,
        "agent_id": agent_id,
    }


def _resolve_init_names(api: Any, args: argparse.Namespace, root: Path, identity: dict[str, str]) -> dict[str, str]:
    resolved_tasklist_name = resolve_tasklist_name(
        api,
        root,
        identity["project_name"],
        explicit_name=str(args.tasklist_name or "").strip(),
        english_name=identity["english_name"],
        agent_id=identity["agent_id"],
    )
    resolved_doc_folder_name = resolve_doc_folder_name(
        api,
        root,
        identity["project_name"],
        explicit_name=str(args.doc_folder_name or "").strip(),
        english_name=identity["english_name"],
        agent_id=identity["agent_id"],
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


def _resolve_backends_and_auth(api: Any, args: argparse.Namespace, *, group_id: str) -> dict[str, Any]:
    resolved_task_backend = str(args.task_backend or current_task_backend(api)).strip() or "feishu"
    resolved_doc_backend = str(args.doc_backend or current_doc_backend(api)).strip() or "feishu"
    auth_bundle = None
    if not args.no_auth_bundle:
        auth_bundle = api.build_auth_bundle(
            include_group_open_reply=True,
            include_attachment_oauth=True,
            explicit_openclaw_config=str(args.openclaw_config or "").strip(),
        )
    resolved_openclaw_config_path = None
    try:
        resolved_openclaw_config_path = api.resolve_openclaw_config_path(args.openclaw_config)
    except SystemExit:
        if group_id:
            raise
    return {
        "resolved_task_backend": resolved_task_backend,
        "resolved_doc_backend": resolved_doc_backend,
        "auth_bundle": auth_bundle,
        "resolved_openclaw_config_path": resolved_openclaw_config_path,
    }


def _workspace_bootstrap_payload(
    api: Any,
    args: argparse.Namespace,
    *,
    root: Path,
    identity: dict[str, str],
    resolved_tasklist_name: str,
    resolved_doc_folder_name: str,
    resolved_task_backend: str,
    resolved_openclaw_config_path: Path | None,
) -> dict[str, Any] | None:
    group_id = identity["group_id"]
    if not group_id:
        return None
    if resolved_openclaw_config_path is None:
        raise SystemExit("openclaw.json not found; provide --openclaw-config")
    workspace_root = api.resolve_workspace_root(
        openclaw_config_path=resolved_openclaw_config_path,
        agent_id=identity["agent_id"],
        explicit=args.workspace_root,
    )
    profile = api.build_workspace_profile(
        project_name=identity["project_name"],
        english_name=identity["english_name"],
        agent_id=identity["agent_id"],
        channel=str(args.channel or "feishu").strip() or "feishu",
        group_id=group_id,
        repo_root=root,
        workspace_root=workspace_root,
        tasklist_name=resolved_tasklist_name,
        doc_folder_name=resolved_doc_folder_name,
        task_prefix=str(args.task_prefix or "T").strip() or "T",
        default_worker=str(args.default_worker or "codex").strip() or "codex",
        reviewer_worker=str(args.reviewer_worker or "reviewer").strip() or "reviewer",
        task_backend_type="local-task" if resolved_task_backend == "local" else "feishu-task",
    )
    scaffold_result = api.scaffold_workspace(
        output=workspace_root,
        profile=profile,
        force=bool(args.force),
        dry_run=bool(args.dry_run),
    )
    register_result = api.register_workspace(
        config_path=resolved_openclaw_config_path,
        agent_id=identity["agent_id"],
        workspace_root=workspace_root,
        group_id=group_id,
        channel=str(args.channel or "feishu").strip() or "feishu",
        skills=list(args.skill or []),
        allow_agents=list(args.allow_agent or []),
        model_primary=str(args.model_primary or "").strip(),
        replace_binding=bool(args.replace_binding),
        dry_run=bool(args.dry_run),
    )
    return {
        "project_name": identity["project_name"],
        "english_name": identity["english_name"],
        "agent_id": identity["agent_id"],
        "workspace_root": str(workspace_root),
        "group_id": group_id,
        "profile": profile,
        "scaffold": scaffold_result,
        "registration": register_result,
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
    workspace_bootstrap: dict[str, Any] | None,
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
        config_payload["coder"].setdefault("backend", "acp")
        config_payload["coder"].setdefault("agent_id", args.agent or "codex")
        config_payload["coder"].setdefault("timeout", int(args.timeout or 900))
        config_payload["coder"].setdefault("thinking", args.thinking or "high")
        config_payload["coder"].setdefault("session_key", args.session_key or "main")
    config_payload.setdefault("project", {})
    if isinstance(config_payload["project"], dict):
        current_name = str(config_payload["project"].get("name") or "").strip()
        if not current_name or current_name == "未命名项目":
            config_payload["project"]["name"] = identity["project_name"]
        if identity["group_id"]:
            config_payload["project"]["group_id"] = identity["group_id"]
        if isinstance(workspace_bootstrap, dict) and str(workspace_bootstrap.get("agent_id") or "").strip():
            config_payload["project"]["agent"] = str(workspace_bootstrap.get("agent_id") or "").strip()
    return config_path, config_payload, task_inspection


def _register_main_review_source(
    api: Any,
    *,
    root: Path,
    project_name: str,
    english_name: str,
    agent_id: str,
    args: argparse.Namespace,
    resolved_openclaw_config_path: Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        main_digest_source_key = str(api.project_slug(project_name, english_name, agent_id)).strip() or root.name
    except Exception:
        main_digest_source_key = root.name
    no_main_review_source = bool(getattr(args, "no_main_review_source", False) or args.no_main_digest_source)
    if no_main_review_source:
        main_review_registration = {
            "status": "skipped",
            "reason": "disabled_by_flag",
        }
    elif resolved_openclaw_config_path is None:
        main_review_registration = {
            "status": "skipped",
            "reason": "openclaw_config_not_found",
        }
    else:
        main_review_registration = api.register_main_digest_source(
            openclaw_config_path=resolved_openclaw_config_path,
            repo_root=root,
            project_name=project_name,
            source_key=main_digest_source_key,
            dry_run=bool(args.dry_run),
        )
    return main_review_registration, main_review_registration


def _register_nightly_review_job(
    api: Any,
    *,
    root: Path,
    config_path: Path,
    config_payload: dict[str, Any],
    project_name: str,
    agent_id: str,
    group_id: str,
    args: argparse.Namespace,
    resolved_openclaw_config_path: Path | None,
) -> dict[str, Any]:
    project_review_cfg = config_payload.get("project_review") if isinstance(config_payload.get("project_review"), dict) else {}
    nightly_cfg = project_review_cfg.get("nightly") if isinstance(project_review_cfg.get("nightly"), dict) else {}
    if not bool(nightly_cfg.get("enabled")):
        return {
            "status": "skipped",
            "reason": "not_enabled",
        }
    register_nightly_review_job = getattr(api, "register_nightly_review_job", None)
    if not callable(register_nightly_review_job):
        return {
            "status": "skipped",
            "reason": "helper_unavailable",
        }
    if resolved_openclaw_config_path is None:
        return {
            "status": "skipped",
            "reason": "openclaw_config_not_found",
        }
    project_cfg = config_payload.get("project") if isinstance(config_payload.get("project"), dict) else {}
    return register_nightly_review_job(
        openclaw_config_path=resolved_openclaw_config_path,
        repo_root=root,
        pm_config_path=config_path,
        project_name=project_name,
        agent_id=str(project_cfg.get("agent") or agent_id or "").strip(),
        group_id=str(project_cfg.get("group_id") or group_id or "").strip(),
        dry_run=bool(args.dry_run),
        enabled=bool(nightly_cfg.get("enabled")),
        cron_expr=str(nightly_cfg.get("cron") or nightly_cfg.get("schedule") or "0 6 * * *").strip() or "0 6 * * *",
        stagger_minutes=int(nightly_cfg.get("stagger_minutes") or 0),
        timezone_name=str(nightly_cfg.get("timezone") or "Asia/Shanghai").strip() or "Asia/Shanghai",
        since=str(nightly_cfg.get("since") or "yesterday 00:00").strip() or "yesterday 00:00",
        until=str(nightly_cfg.get("until") or "today 00:00").strip() or "today 00:00",
        reviewer_model=str(nightly_cfg.get("reviewer_model") or "").strip(),
        auto_fix_mode=str(nightly_cfg.get("auto_fix_mode") or "long-file-and-docs").strip() or "long-file-and-docs",
        send_if_possible=bool(nightly_cfg.get("send", True)),
        include_dirty=bool(nightly_cfg.get("include_dirty", True)),
    )


def _init_warnings(args: argparse.Namespace, deprecated_command: str) -> list[str]:
    warnings: list[str] = []
    if deprecated_command:
        warnings.append(f"`{deprecated_command}` 已弃用，请改用 `init`。")
    if str(args.tasklist_name or "").strip():
        warnings.append("`--tasklist-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
    if str(args.doc_folder_name or "").strip():
        warnings.append("`--doc-folder-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
    return warnings


def _maybe_auto_run_init_task(
    api: Any,
    args: argparse.Namespace,
    *,
    root: Path,
    config_payload: dict[str, Any],
    bootstrap_task: dict[str, Any] | None,
    selected_task_id: str,
    selected_task_guid: str,
) -> tuple[str, dict[str, Any] | None]:
    if args.skip_auto_run:
        return "disabled_by_flag", None
    if not isinstance(bootstrap_task, dict) or not bootstrap_task.get("created"):
        return "bootstrap_task_not_created", None

    fallback_session_key = str((config_payload.get("coder") or {}).get("session_key") or "main").strip() or "main"
    resolve_dispatch_session_key = getattr(api, "resolve_dispatch_session_key", None)
    if callable(resolve_dispatch_session_key):
        resolved_session_key = resolve_dispatch_session_key(args.session_key, fallback=fallback_session_key)
    else:
        resolved_session_key = str(args.session_key or fallback_session_key or "main").strip() or "main"
    run_args = argparse.Namespace(
        task_id=selected_task_id,
        task_guid=selected_task_guid,
        backend=str((config_payload.get("coder") or {}).get("backend") or "acp"),
        agent=args.agent or str((config_payload.get("coder") or {}).get("agent_id") or "codex"),
        timeout=int(args.timeout or (config_payload.get("coder") or {}).get("timeout") or 900),
        thinking=args.thinking or str((config_payload.get("coder") or {}).get("thinking") or "high"),
        session_key=resolved_session_key,
    )
    bundle, coder_context_path = api.build_coder_context(task_id=selected_task_id, task_guid=selected_task_guid)
    message = api.build_run_message(bundle)
    run_result = api.spawn_acp_session(
        agent_id=str(run_args.agent or "codex"),
        message=message,
        cwd=str(root),
        timeout_seconds=int(run_args.timeout or 900),
        thinking=str(run_args.thinking or "high"),
        label=api.build_run_label(root, str(run_args.agent or "codex"), selected_task_id),
        session_key=str(run_args.session_key or "main"),
    )
    run_side_effects = api.persist_dispatch_side_effects(bundle, run_result, agent_id=str(run_args.agent or "codex"), runtime="acp")
    run_payload = {
        "coder_context_path": str(coder_context_path),
        "backend": "acp",
        "agent_id": str(run_args.agent or "codex"),
        "session_key": str(run_args.session_key or "main"),
        "timeout": int(run_args.timeout or 900),
        "thinking": str(run_args.thinking or "high"),
        "message_preview": message[:1200],
        "result": run_result,
        "side_effects": run_side_effects,
    }
    api.write_pm_bundle("last-run.json", run_payload)
    return "bootstrap_task_created", run_payload


def cmd_init(api: Any, args: argparse.Namespace) -> int:
    root = api.project_root_path(args.repo_root)
    repo_config_path = root / "pm.json"
    args.config = str(repo_config_path)
    deprecated_command = str(getattr(args, "_deprecated_command", "") or "").strip()

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
    backend_state = _resolve_backends_and_auth(api, args, group_id=identity["group_id"])
    workspace_bootstrap = _workspace_bootstrap_payload(
        api,
        args,
        root=root,
        identity=identity,
        resolved_tasklist_name=names["resolved_tasklist_name"],
        resolved_doc_folder_name=names["resolved_doc_folder_name"],
        resolved_task_backend=backend_state["resolved_task_backend"],
        resolved_openclaw_config_path=backend_state["resolved_openclaw_config_path"],
    )
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
        workspace_bootstrap=workspace_bootstrap,
    )
    main_review_registration, main_digest_registration = _register_main_review_source(
        api,
        root=root,
        project_name=identity["project_name"],
        english_name=identity["english_name"],
        agent_id=identity["agent_id"],
        args=args,
        resolved_openclaw_config_path=backend_state["resolved_openclaw_config_path"],
    )
    nightly_review_registration = _register_nightly_review_job(
        api,
        root=root,
        config_path=config_path,
        config_payload=config_payload,
        project_name=identity["project_name"],
        agent_id=identity["agent_id"],
        group_id=identity["group_id"],
        args=args,
        resolved_openclaw_config_path=backend_state["resolved_openclaw_config_path"],
    )
    warnings = _init_warnings(args, deprecated_command)

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
                "workspace_bootstrap": workspace_bootstrap,
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
    bootstrap_task = None if args.skip_bootstrap_task else api.ensure_bootstrap_task(root)
    selected_task_id = str(((bootstrap_task or {}).get("task") or {}).get("task_id") or "").strip()
    selected_task_guid = str(((bootstrap_task or {}).get("task") or {}).get("guid") or "").strip()
    payload = api.refresh_context_cache(task_id=selected_task_id, task_guid=selected_task_guid)
    auto_run_reason, run_payload = _maybe_auto_run_init_task(
        api,
        args,
        root=root,
        config_payload=config_payload,
        bootstrap_task=bootstrap_task,
        selected_task_id=selected_task_id,
        selected_task_guid=selected_task_guid,
    )
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
            "auto_run_reason": auto_run_reason,
            "run": run_payload,
            "context_path": str(api.pm_file("current-context.json", str(root))),
            "project_scan_path": str(api.pm_file("project-scan.json", str(root))),
            "repo_scan": payload.get("repo_scan") or {},
            "doc_index": payload.get("doc_index") or {},
            "gsd": payload.get("gsd") or {},
            "workspace_bootstrap": workspace_bootstrap,
            "auth_bundle": backend_state["auth_bundle"],
            "main_review_registration": main_review_registration,
            "main_digest_registration": main_digest_registration,
            "nightly_review_registration": nightly_review_registration,
        }
    )


def _resolve_workspace_delete_context(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    repo_root_raw = str(args.repo_root or "").strip()
    workspace_root_raw = str(args.workspace_root or "").strip()
    if not repo_root_raw and not workspace_root_raw:
        raise SystemExit("provide --repo-root or --workspace-root")

    root = api.project_root_path(repo_root_raw) if repo_root_raw else None
    workspace_root = Path(workspace_root_raw).expanduser().resolve() if workspace_root_raw else None
    if root is None and isinstance(workspace_root, Path):
        profile_path = workspace_root / "config" / "project-profile.json"
        if profile_path.exists():
            try:
                profile_payload = json.loads(profile_path.read_text(encoding="utf-8"))
            except Exception:
                profile_payload = {}
            repo_root_from_profile = str(profile_payload.get("repoRoot") or "").strip() if isinstance(profile_payload, dict) else ""
            if repo_root_from_profile:
                root = Path(repo_root_from_profile).expanduser().resolve()

    repo_config_path = (root / "pm.json") if isinstance(root, Path) else Path(str(args.config or "")).expanduser().resolve()
    config_payload = api.load_config(str(repo_config_path)) if repo_config_path.exists() else {}
    project_cfg = config_payload.get("project") if isinstance(config_payload.get("project"), dict) else {}
    task_cfg = config_payload.get("task") if isinstance(config_payload.get("task"), dict) else {}
    doc_cfg = config_payload.get("doc") if isinstance(config_payload.get("doc"), dict) else {}

    openclaw_config_path = api.resolve_openclaw_config_path(args.openclaw_config)
    project_name = str(project_cfg.get("name") or (root.name if isinstance(root, Path) else "")).strip()
    agent_id = str(args.agent_id or project_cfg.get("agent") or "").strip()
    group_id = str(args.group_id or project_cfg.get("group_id") or "").strip()
    channel = str(args.channel or "feishu").strip() or "feishu"
    registration = api.inspect_workspace_registration(
        config_path=openclaw_config_path,
        agent_id=agent_id,
        workspace_root=workspace_root,
        group_id=group_id,
        channel=channel,
    )
    resolved_workspace_raw = str(registration.get("resolved_workspace_root") or "").strip()
    if workspace_root is None and resolved_workspace_raw:
        workspace_root = Path(resolved_workspace_raw).expanduser().resolve()

    return {
        "root": root,
        "workspace_root": workspace_root,
        "repo_config_path": repo_config_path,
        "config_payload": config_payload,
        "task_cfg": task_cfg,
        "doc_cfg": doc_cfg,
        "openclaw_config_path": openclaw_config_path,
        "project_name": project_name,
        "resolved_agent_id": str(registration.get("resolved_agent_id") or agent_id).strip(),
        "resolved_group_id": str(registration.get("resolved_group_id") or group_id).strip(),
        "resolved_channel": str(registration.get("resolved_channel") or channel).strip() or channel,
    }


def _workspace_delete_tasklist_cleanup(api: Any, args: argparse.Namespace, task_cfg: dict[str, Any]) -> dict[str, Any]:
    tasklist_name = str(task_cfg.get("tasklist_name") or "").strip()
    tasklist_guid = str(task_cfg.get("tasklist_guid") or "").strip()
    if str(task_cfg.get("backend") or "feishu").strip() != "feishu":
        return {"status": "skipped", "reason": "backend_not_feishu"}

    inspection = api.inspect_tasklist(tasklist_name, configured_guid=tasklist_guid) if (tasklist_name or tasklist_guid) else {}
    tasklist = inspection.get("tasklist") if isinstance(inspection.get("tasklist"), dict) else {}
    resolved_tasklist_guid = str(tasklist.get("guid") or tasklist_guid).strip()
    if not resolved_tasklist_guid:
        return {"status": "missing", "inspection": inspection}
    if args.dry_run:
        return {
            "status": "dry_run",
            "tasklist_guid": resolved_tasklist_guid,
            "tasklist_name": str(tasklist.get("name") or tasklist_name).strip(),
            "inspection": inspection,
        }
    api.run_bridge("feishu_task_tasklist", "delete", {"tasklist_guid": resolved_tasklist_guid})
    return {
        "status": "deleted",
        "tasklist_guid": resolved_tasklist_guid,
        "tasklist_name": str(tasklist.get("name") or tasklist_name).strip(),
        "inspection": inspection,
    }


def _workspace_delete_docs_cleanup(api: Any, args: argparse.Namespace, doc_cfg: dict[str, Any]) -> dict[str, Any]:
    folder_name = str(doc_cfg.get("folder_name") or "").strip()
    folder_token = str(doc_cfg.get("folder_token") or "").strip()
    if str(doc_cfg.get("backend") or "feishu").strip() != "feishu":
        return {"status": "skipped", "reason": "backend_not_feishu"}
    folder_node = api.find_root_folder_by_name(folder_name) if (not folder_token and folder_name) else None
    resolved_folder_token = folder_token or str((folder_node or {}).get("token") or (folder_node or {}).get("file_token") or "").strip()
    if not resolved_folder_token:
        return {"status": "missing", "folder_name": folder_name}
    if args.dry_run:
        return {
            "status": "dry_run",
            "folder_token": resolved_folder_token,
            "folder_name": folder_name or str((folder_node or {}).get("name") or "").strip(),
        }
    api.run_bridge("feishu_drive_file", "delete", {"file_token": resolved_folder_token, "type": "folder"})
    return {
        "status": "deleted",
        "folder_token": resolved_folder_token,
        "folder_name": folder_name or str((folder_node or {}).get("name") or "").strip(),
    }


def _workspace_delete_repo_config_cleanup(args: argparse.Namespace, repo_config_path: Path, config_payload: dict[str, Any]) -> dict[str, Any]:
    if args.dry_run or not repo_config_path.exists():
        return {
            "status": "dry_run" if args.dry_run and repo_config_path.exists() else "missing",
            "config_path": str(repo_config_path),
            "cleared_fields": _cleanup_repo_config_for_workspace_delete(json.loads(json.dumps(config_payload, ensure_ascii=False)))
            if repo_config_path.exists()
            else [],
        }
    cleared_fields = _cleanup_repo_config_for_workspace_delete(config_payload)
    repo_config_path.write_text(json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "status": "updated",
        "config_path": str(repo_config_path),
        "cleared_fields": cleared_fields,
    }


def _workspace_delete_workspace_cleanup(args: argparse.Namespace, workspace_root: Path | None) -> dict[str, Any]:
    if workspace_root is None:
        return {"status": "missing", "path": ""}
    if args.dry_run:
        return {
            "status": "dry_run",
            "path": str(workspace_root),
            "exists": workspace_root.exists(),
        }
    existed = workspace_root.exists()
    if existed:
        shutil.rmtree(workspace_root)
    return {
        "status": "deleted" if existed else "missing",
        "path": str(workspace_root),
        "exists": existed,
    }


def cmd_workspace_delete(api: Any, args: argparse.Namespace) -> int:
    context = _resolve_workspace_delete_context(api, args)
    root = context["root"]
    repo_config_path = context["repo_config_path"]
    config_payload = context["config_payload"]
    project_name = context["project_name"]

    tasklist_cleanup = _workspace_delete_tasklist_cleanup(api, args, context["task_cfg"])
    docs_cleanup = _workspace_delete_docs_cleanup(api, args, context["doc_cfg"])

    source_key = ""
    try:
        source_key = str(api.project_slug(project_name, "", context["resolved_agent_id"])).strip()
    except Exception:
        source_key = ""
    main_digest_cleanup = api.unregister_main_digest_source(
        openclaw_config_path=context["openclaw_config_path"],
        repo_root=root or Path.cwd(),
        source_key=source_key,
        dry_run=bool(args.dry_run),
    )
    nightly_review_cleanup = api.unregister_nightly_review_job(
        openclaw_config_path=context["openclaw_config_path"],
        repo_root=root or Path.cwd(),
        project_name=project_name,
        dry_run=bool(args.dry_run),
    )
    registration_cleanup = api.unregister_workspace(
        config_path=context["openclaw_config_path"],
        agent_id=context["resolved_agent_id"],
        workspace_root=context["workspace_root"],
        group_id=context["resolved_group_id"],
        channel=context["resolved_channel"],
        dry_run=bool(args.dry_run),
    )
    repo_config_cleanup = _workspace_delete_repo_config_cleanup(args, repo_config_path, config_payload)
    workspace_cleanup = _workspace_delete_workspace_cleanup(args, context["workspace_root"])

    return _emit(
        {
            "status": "dry_run" if args.dry_run else "deleted",
            "repo_root": str(root) if isinstance(root, Path) else "",
            "config_path": str(repo_config_path),
            "openclaw_config_path": str(context["openclaw_config_path"]),
            "project_name": project_name,
            "agent_id": context["resolved_agent_id"],
            "group_id": context["resolved_group_id"],
            "channel": context["resolved_channel"],
            "workspace_root": str(context["workspace_root"]) if isinstance(context["workspace_root"], Path) else "",
            "tasklist_cleanup": tasklist_cleanup,
            "docs_cleanup": docs_cleanup,
            "main_digest_cleanup": main_digest_cleanup,
            "nightly_review_cleanup": nightly_review_cleanup,
            "registration_cleanup": registration_cleanup,
            "repo_config_cleanup": repo_config_cleanup,
            "workspace_cleanup": workspace_cleanup,
        }
    )
