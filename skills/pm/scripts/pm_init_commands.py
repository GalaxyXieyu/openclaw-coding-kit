from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pm_command_support import (
    CommandHandler,
    current_doc_backend,
    current_doc_cfg,
    current_project_cfg,
    current_task_backend,
    current_task_cfg,
    emit_json,
    resolve_doc_folder_name,
    resolve_tasklist_name,
)


@dataclass(frozen=True)
class InitNames:
    root: Path
    project_name: str
    group_id: str
    english_name: str
    agent_id: str
    deprecated_command: str
    explicit_tasklist_name: str
    explicit_doc_folder_name: str
    resolved_tasklist_name: str
    resolved_doc_folder_name: str
    configured_tasklist_guid: str
    configured_doc_folder_token: str


@dataclass(frozen=True)
class InitRuntime:
    resolved_task_backend: str
    resolved_doc_backend: str
    auth_bundle: dict[str, Any] | None
    resolved_openclaw_config_path: Path | None
    workspace_bootstrap: dict[str, Any] | None


@dataclass(frozen=True)
class InitRegistrations:
    main_review_registration: dict[str, Any]
    main_digest_registration: dict[str, Any]
    nightly_review_registration: dict[str, Any]


def _emit(payload: dict[str, Any]) -> int:
    return emit_json(payload)


def _cmd_auth_link(api: Any, args: argparse.Namespace) -> int:
    raw = [item.strip() for item in re.split(r"[\s,]+", args.scopes or "") if item.strip()]
    if not raw:
        raise SystemExit("provide --scopes, e.g. --scopes drive:drive offline_access")
    if args.mode == "user-oauth":
        payload = api.request_user_oauth_link(scopes=raw)
    else:
        payload = api.build_auth_link(scopes=raw, token_type=args.token_type)
    return _emit(payload)


def _cmd_permission_bundle(api: Any, args: argparse.Namespace) -> int:
    if args.list_presets:
        return _emit({"presets": api.list_app_scope_presets()})
    payload = api.build_permission_bundle(
        preset_names=list(args.preset or []),
        scopes=list(args.scope or []),
        token_type=args.token_type,
    )
    return _emit(payload)


def _cmd_auth(api: Any, args: argparse.Namespace) -> int:
    payload = api.build_auth_bundle(
        include_group_open_reply=not bool(args.no_group_open_reply),
        include_attachment_oauth=not bool(args.no_attachment_oauth),
    )
    return _emit(payload)


def _resolve_init_names(api: Any, args: argparse.Namespace) -> InitNames:
    root = api.project_root_path(args.repo_root)
    args.config = str(root / "pm.json")
    deprecated_command = str(getattr(args, "_deprecated_command", "") or "").strip()
    explicit_tasklist_name = str(args.tasklist_name or "").strip()
    explicit_doc_folder_name = str(args.doc_folder_name or "").strip()

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

    resolved_tasklist_name = resolve_tasklist_name(
        api,
        root,
        project_name,
        explicit_name=explicit_tasklist_name,
        english_name=english_name,
        agent_id=agent_id,
    )
    resolved_doc_folder_name = resolve_doc_folder_name(
        api,
        root,
        project_name,
        explicit_name=explicit_doc_folder_name,
        english_name=english_name,
        agent_id=agent_id,
    )
    configured_tasklist_guid = str(
        args.tasklist_guid or current_task_cfg(api).get("tasklist_guid") or ""
    ).strip()
    configured_doc_folder_token = str(
        args.doc_folder_token or current_doc_cfg(api).get("folder_token") or ""
    ).strip()
    return InitNames(
        root=root,
        project_name=project_name,
        group_id=group_id,
        english_name=english_name,
        agent_id=agent_id,
        deprecated_command=deprecated_command,
        explicit_tasklist_name=explicit_tasklist_name,
        explicit_doc_folder_name=explicit_doc_folder_name,
        resolved_tasklist_name=resolved_tasklist_name,
        resolved_doc_folder_name=resolved_doc_folder_name,
        configured_tasklist_guid=configured_tasklist_guid,
        configured_doc_folder_token=configured_doc_folder_token,
    )


def _prime_active_config(api: Any, names: InitNames) -> None:
    api.ACTIVE_CONFIG["repo_root"] = str(names.root)
    api.ACTIVE_CONFIG.setdefault("task", {})
    if isinstance(api.ACTIVE_CONFIG.get("task"), dict):
        api.ACTIVE_CONFIG["task"]["tasklist_name"] = names.resolved_tasklist_name
        if names.configured_tasklist_guid:
            api.ACTIVE_CONFIG["task"]["tasklist_guid"] = names.configured_tasklist_guid
    api.ACTIVE_CONFIG["tasklist_name"] = names.resolved_tasklist_name
    api.ACTIVE_CONFIG.setdefault("doc", {})
    if isinstance(api.ACTIVE_CONFIG.get("doc"), dict):
        api.ACTIVE_CONFIG["doc"]["folder_name"] = names.resolved_doc_folder_name
        if names.configured_doc_folder_token:
            api.ACTIVE_CONFIG["doc"]["folder_token"] = names.configured_doc_folder_token


def _build_workspace_bootstrap(api: Any, args: argparse.Namespace, names: InitNames, runtime: InitRuntime | None = None) -> dict[str, Any]:
    openclaw_config_path = (
        runtime.resolved_openclaw_config_path if runtime is not None else api.resolve_openclaw_config_path(args.openclaw_config)
    )
    if openclaw_config_path is None:
        raise SystemExit("openclaw.json not found; provide --openclaw-config")
    workspace_root = api.resolve_workspace_root(
        openclaw_config_path=openclaw_config_path,
        agent_id=names.agent_id,
        explicit=args.workspace_root,
    )
    resolved_task_backend = runtime.resolved_task_backend if runtime is not None else "feishu"
    resolved_doc_backend = runtime.resolved_doc_backend if runtime is not None else "feishu"
    profile = api.build_workspace_profile(
        project_name=names.project_name,
        english_name=names.english_name,
        agent_id=names.agent_id,
        channel=str(args.channel or "feishu").strip() or "feishu",
        group_id=names.group_id,
        repo_root=names.root,
        workspace_root=workspace_root,
        tasklist_name=names.resolved_tasklist_name,
        doc_folder_name=names.resolved_doc_folder_name,
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
        config_path=openclaw_config_path,
        agent_id=names.agent_id,
        workspace_root=workspace_root,
        group_id=names.group_id,
        channel=str(args.channel or "feishu").strip() or "feishu",
        skills=list(args.skill or []),
        allow_agents=list(args.allow_agent or []),
        model_primary=str(args.model_primary or "").strip(),
        replace_binding=bool(args.replace_binding),
        dry_run=bool(args.dry_run),
    )
    return {
        "project_name": names.project_name,
        "english_name": names.english_name,
        "agent_id": names.agent_id,
        "workspace_root": str(workspace_root),
        "group_id": names.group_id,
        "profile": profile,
        "scaffold": scaffold_result,
        "registration": register_result,
    }


def _resolve_init_runtime(api: Any, args: argparse.Namespace, names: InitNames) -> InitRuntime:
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
        if names.group_id:
            raise

    runtime = InitRuntime(
        resolved_task_backend=resolved_task_backend,
        resolved_doc_backend=resolved_doc_backend,
        auth_bundle=auth_bundle,
        resolved_openclaw_config_path=resolved_openclaw_config_path,
        workspace_bootstrap=None,
    )
    workspace_bootstrap = None
    if names.group_id:
        workspace_bootstrap = _build_workspace_bootstrap(api, args, names, runtime)

    api.ACTIVE_CONFIG.setdefault("task", {})
    if isinstance(api.ACTIVE_CONFIG.get("task"), dict):
        api.ACTIVE_CONFIG["task"]["backend"] = resolved_task_backend
    api.ACTIVE_CONFIG.setdefault("doc", {})
    if isinstance(api.ACTIVE_CONFIG.get("doc"), dict):
        api.ACTIVE_CONFIG["doc"]["backend"] = resolved_doc_backend
    return InitRuntime(
        resolved_task_backend=resolved_task_backend,
        resolved_doc_backend=resolved_doc_backend,
        auth_bundle=auth_bundle,
        resolved_openclaw_config_path=resolved_openclaw_config_path,
        workspace_bootstrap=workspace_bootstrap,
    )


def _populate_task_config(api: Any, config_payload: dict[str, Any], names: InitNames, runtime: InitRuntime) -> None:
    config_payload.setdefault("task", {})
    if not isinstance(config_payload["task"], dict):
        config_payload["task"] = {}
    task_payload = config_payload["task"]
    task_payload["backend"] = runtime.resolved_task_backend
    task_payload["tasklist_name"] = names.resolved_tasklist_name
    task_payload.setdefault("prefix", api.task_prefix())
    task_payload.setdefault("kind", api.task_kind())
    if names.configured_tasklist_guid:
        task_payload["tasklist_guid"] = names.configured_tasklist_guid
    config_payload.setdefault("tasklist_name", task_payload["tasklist_name"])
    config_payload.setdefault("task_prefix", task_payload["prefix"])
    config_payload.setdefault("kind", task_payload["kind"])


def _populate_doc_config(api: Any, config_payload: dict[str, Any], names: InitNames, runtime: InitRuntime) -> None:
    config_payload.setdefault("doc", api.default_config()["doc"])
    if not isinstance(config_payload["doc"], dict):
        config_payload["doc"] = {}
    doc_payload = config_payload["doc"]
    doc_payload["backend"] = runtime.resolved_doc_backend
    doc_payload["folder_name"] = names.resolved_doc_folder_name
    if names.configured_doc_folder_token:
        doc_payload["folder_token"] = names.configured_doc_folder_token
    doc_payload.setdefault("project_title", "PROJECT")
    doc_payload.setdefault("requirements_title", "REQUIREMENTS")
    doc_payload.setdefault("roadmap_title", "ROADMAP")
    doc_payload.setdefault("state_title", "STATE")


def _populate_coder_config(api: Any, args: argparse.Namespace, config_payload: dict[str, Any]) -> None:
    config_payload.setdefault("coder", api.default_config()["coder"])
    if not isinstance(config_payload["coder"], dict):
        config_payload["coder"] = {}
    coder_payload = config_payload["coder"]
    coder_payload.setdefault("backend", "acp")
    coder_payload.setdefault("agent_id", args.agent or "codex")
    coder_payload.setdefault("timeout", int(args.timeout or 900))
    coder_payload.setdefault("thinking", args.thinking or "high")
    coder_payload.setdefault("session_key", args.session_key or "main")


def _populate_project_config(config_payload: dict[str, Any], names: InitNames, runtime: InitRuntime) -> None:
    config_payload.setdefault("project", {})
    if not isinstance(config_payload["project"], dict):
        config_payload["project"] = {}
    project_payload = config_payload["project"]
    current_name = str(project_payload.get("name") or "").strip()
    if not current_name or current_name == "未命名项目":
        project_payload["name"] = names.project_name
    if names.group_id:
        project_payload["group_id"] = names.group_id
    workspace_bootstrap = runtime.workspace_bootstrap or {}
    if str(workspace_bootstrap.get("agent_id") or "").strip():
        project_payload["agent"] = str(workspace_bootstrap.get("agent_id") or "").strip()


def _build_init_config_payload(api: Any, args: argparse.Namespace, names: InitNames, runtime: InitRuntime) -> tuple[Path, dict[str, Any]]:
    config_path = api.resolve_config_path(args.config)
    config_payload = {
        key: value for key, value in api.ACTIVE_CONFIG.items() if not str(key).startswith("_")
    }
    config_payload["repo_root"] = str(names.root)
    config_payload.setdefault("repo", {})
    if not isinstance(config_payload["repo"], dict):
        config_payload["repo"] = {}
    config_payload["repo"]["root"] = str(names.root)
    _populate_task_config(api, config_payload, names, runtime)
    _populate_doc_config(api, config_payload, names, runtime)
    _populate_coder_config(api, args, config_payload)
    _populate_project_config(config_payload, names, runtime)
    return config_path, config_payload


def _main_digest_source_key(api: Any, names: InitNames) -> str:
    try:
        return str(api.project_slug(names.project_name, names.english_name, names.agent_id)).strip() or names.root.name
    except Exception:
        return names.root.name


def _register_main_review_source(
    api: Any,
    *,
    args: argparse.Namespace,
    names: InitNames,
    runtime: InitRuntime,
) -> dict[str, Any]:
    no_main_review_source = bool(
        getattr(args, "no_main_review_source", False) or args.no_main_digest_source
    )
    if no_main_review_source:
        return {"status": "skipped", "reason": "disabled_by_flag"}
    if runtime.resolved_openclaw_config_path is None:
        return {"status": "skipped", "reason": "openclaw_config_not_found"}
    return api.register_main_digest_source(
        openclaw_config_path=runtime.resolved_openclaw_config_path,
        repo_root=names.root,
        project_name=names.project_name,
        source_key=_main_digest_source_key(api, names),
        dry_run=bool(args.dry_run),
    )


def _register_nightly_review_job(
    api: Any,
    *,
    args: argparse.Namespace,
    names: InitNames,
    runtime: InitRuntime,
    config_path: Path,
    config_payload: dict[str, Any],
) -> dict[str, Any]:
    project_review_cfg = (
        config_payload.get("project_review")
        if isinstance(config_payload.get("project_review"), dict)
        else {}
    )
    nightly_cfg = (
        project_review_cfg.get("nightly")
        if isinstance(project_review_cfg.get("nightly"), dict)
        else {}
    )
    if not bool(nightly_cfg.get("enabled")):
        return {"status": "skipped", "reason": "not_enabled"}
    register_nightly_review_job = getattr(api, "register_nightly_review_job", None)
    if not callable(register_nightly_review_job):
        return {"status": "skipped", "reason": "helper_unavailable"}
    if runtime.resolved_openclaw_config_path is None:
        return {"status": "skipped", "reason": "openclaw_config_not_found"}
    project_cfg = config_payload.get("project") if isinstance(config_payload.get("project"), dict) else {}
    return register_nightly_review_job(
        openclaw_config_path=runtime.resolved_openclaw_config_path,
        repo_root=names.root,
        pm_config_path=config_path,
        project_name=names.project_name,
        agent_id=str(project_cfg.get("agent") or names.agent_id or "").strip(),
        group_id=str(project_cfg.get("group_id") or names.group_id or "").strip(),
        dry_run=bool(args.dry_run),
        enabled=bool(nightly_cfg.get("enabled")),
        cron_expr=str(nightly_cfg.get("cron") or nightly_cfg.get("schedule") or "30 0 * * *").strip() or "30 0 * * *",
        timezone_name=str(nightly_cfg.get("timezone") or "Asia/Shanghai").strip() or "Asia/Shanghai",
        since=str(nightly_cfg.get("since") or "24 hours ago").strip() or "24 hours ago",
        reviewer_model=str(nightly_cfg.get("reviewer_model") or "").strip(),
        auto_fix_mode=str(nightly_cfg.get("auto_fix_mode") or "long-file-and-docs").strip() or "long-file-and-docs",
        send_if_possible=bool(nightly_cfg.get("send", True)),
        include_dirty=bool(nightly_cfg.get("include_dirty", True)),
    )


def _build_init_registrations(
    api: Any,
    *,
    args: argparse.Namespace,
    names: InitNames,
    runtime: InitRuntime,
    config_path: Path,
    config_payload: dict[str, Any],
) -> InitRegistrations:
    main_review_registration = _register_main_review_source(
        api,
        args=args,
        names=names,
        runtime=runtime,
    )
    nightly_review_registration = _register_nightly_review_job(
        api,
        args=args,
        names=names,
        runtime=runtime,
        config_path=config_path,
        config_payload=config_payload,
    )
    return InitRegistrations(
        main_review_registration=main_review_registration,
        main_digest_registration=main_review_registration,
        nightly_review_registration=nightly_review_registration,
    )


def _build_init_warnings(names: InitNames) -> list[str]:
    warnings: list[str] = []
    if names.deprecated_command:
        warnings.append(f"`{names.deprecated_command}` 已弃用，请改用 `init`。")
    if names.explicit_tasklist_name:
        warnings.append("`--tasklist-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
    if names.explicit_doc_folder_name:
        warnings.append("`--doc-folder-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
    return warnings


def _emit_init_dry_run(
    api: Any,
    *,
    names: InitNames,
    runtime: InitRuntime,
    config_path: Path,
    config_payload: dict[str, Any],
    task_inspection: dict[str, Any],
    registrations: InitRegistrations,
    warnings: list[str],
) -> int:
    api.ACTIVE_CONFIG.update(config_payload)
    docs_preview = api.ensure_project_docs(names.root, dry_run=True)
    return _emit(
        {
            "status": "dry_run",
            "warnings": warnings,
            "config_path": str(config_path),
            "repo_root": str(names.root),
            "project_name": names.project_name,
            "naming_mode": "project_name_default"
            if not (names.explicit_tasklist_name or names.explicit_doc_folder_name)
            else "explicit_override",
            "resolved_tasklist_name": names.resolved_tasklist_name,
            "resolved_doc_folder_name": names.resolved_doc_folder_name,
            "tasklist_inspection": task_inspection,
            "docs_preview": docs_preview,
            "workspace_bootstrap": runtime.workspace_bootstrap,
            "auth_bundle": runtime.auth_bundle,
            "main_review_registration": registrations.main_review_registration,
            "main_digest_registration": registrations.main_digest_registration,
            "nightly_review_registration": registrations.nightly_review_registration,
            "config_preview": config_payload,
        }
    )


def _build_auto_run_payload(
    api: Any,
    *,
    args: argparse.Namespace,
    config_payload: dict[str, Any],
    root: Path,
    bootstrap_task: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    if args.skip_auto_run:
        return None, "disabled_by_flag"
    if not (isinstance(bootstrap_task, dict) and bootstrap_task.get("created")):
        return None, "bootstrap_task_not_created"

    selected_task_id = str(((bootstrap_task or {}).get("task") or {}).get("task_id") or "").strip()
    selected_task_guid = str(((bootstrap_task or {}).get("task") or {}).get("guid") or "").strip()
    run_args = argparse.Namespace(
        task_id=selected_task_id,
        task_guid=selected_task_guid,
        backend=str((config_payload.get("coder") or {}).get("backend") or "acp"),
        agent=args.agent or str((config_payload.get("coder") or {}).get("agent_id") or "codex"),
        timeout=int(args.timeout or (config_payload.get("coder") or {}).get("timeout") or 900),
        thinking=args.thinking or str((config_payload.get("coder") or {}).get("thinking") or "high"),
        session_key=args.session_key or str((config_payload.get("coder") or {}).get("session_key") or "main"),
    )
    bundle, coder_context_path = api.build_coder_context(
        task_id=selected_task_id,
        task_guid=selected_task_guid,
    )
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
    run_side_effects = api.persist_dispatch_side_effects(
        bundle,
        run_result,
        agent_id=str(run_args.agent or "codex"),
        runtime="acp",
    )
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
    return run_payload, "bootstrap_task_created"


def _execute_init(
    api: Any,
    *,
    args: argparse.Namespace,
    names: InitNames,
    runtime: InitRuntime,
    config_path: Path,
    config_payload: dict[str, Any],
    task_inspection: dict[str, Any],
    registrations: InitRegistrations,
    warnings: list[str],
) -> int:
    tasklist = api.ensure_tasklist(names.resolved_tasklist_name)
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
    docs = api.ensure_project_docs(names.root)
    if isinstance(config_payload.get("doc"), dict):
        config_payload["doc"].update(docs)
    api.ACTIVE_CONFIG.update(config_payload)
    api.ensure_pm_dir(str(names.root))
    if args.write_config or not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    bootstrap_task = None if args.skip_bootstrap_task else api.ensure_bootstrap_task(names.root)
    selected_task_id = str(((bootstrap_task or {}).get("task") or {}).get("task_id") or "").strip()
    selected_task_guid = str(((bootstrap_task or {}).get("task") or {}).get("guid") or "").strip()
    payload = api.refresh_context_cache(task_id=selected_task_id, task_guid=selected_task_guid)
    run_payload, auto_run_reason = _build_auto_run_payload(
        api,
        args=args,
        config_payload=config_payload,
        root=names.root,
        bootstrap_task=bootstrap_task,
    )
    return _emit(
        {
            "status": "initialized",
            "warnings": warnings,
            "config_path": str(config_path),
            "repo_root": str(names.root),
            "pm_dir": str(api.pm_dir_path(str(names.root))),
            "project_name": names.project_name,
            "naming_mode": "project_name_default"
            if not (names.explicit_tasklist_name or names.explicit_doc_folder_name)
            else "explicit_override",
            "tasklist": tasklist,
            "tasklist_inspection": task_inspection,
            "bootstrap_task": bootstrap_task,
            "auto_run_reason": auto_run_reason,
            "run": run_payload,
            "context_path": str(api.pm_file("current-context.json", str(names.root))),
            "project_scan_path": str(api.pm_file("project-scan.json", str(names.root))),
            "repo_scan": payload.get("repo_scan") or {},
            "doc_index": payload.get("doc_index") or {},
            "gsd": payload.get("gsd") or {},
            "workspace_bootstrap": runtime.workspace_bootstrap,
            "auth_bundle": runtime.auth_bundle,
            "main_review_registration": registrations.main_review_registration,
            "main_digest_registration": registrations.main_digest_registration,
            "nightly_review_registration": registrations.nightly_review_registration,
        }
    )


def _cmd_init(api: Any, args: argparse.Namespace) -> int:
    names = _resolve_init_names(api, args)
    _prime_active_config(api, names)
    runtime = _resolve_init_runtime(api, args, names)
    task_inspection = api.inspect_tasklist(
        names.resolved_tasklist_name,
        configured_guid=names.configured_tasklist_guid,
    )
    config_path, config_payload = _build_init_config_payload(api, args, names, runtime)
    registrations = _build_init_registrations(
        api,
        args=args,
        names=names,
        runtime=runtime,
        config_path=config_path,
        config_payload=config_payload,
    )
    warnings = _build_init_warnings(names)
    if args.dry_run:
        return _emit_init_dry_run(
            api,
            names=names,
            runtime=runtime,
            config_path=config_path,
            config_payload=config_payload,
            task_inspection=task_inspection,
            registrations=registrations,
            warnings=warnings,
        )
    return _execute_init(
        api,
        args=args,
        names=names,
        runtime=runtime,
        config_path=config_path,
        config_payload=config_payload,
        task_inspection=task_inspection,
        registrations=registrations,
        warnings=warnings,
    )


def build_init_command_handlers(api: Any) -> dict[str, CommandHandler]:
    return {
        "auth": lambda args: _cmd_auth(api, args),
        "auth_link": lambda args: _cmd_auth_link(api, args),
        "permission_bundle": lambda args: _cmd_permission_bundle(api, args),
        "init": lambda args: _cmd_init(api, args),
    }
