from __future__ import annotations

import argparse
import json
import re
import shutil
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


def build_init_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def emit(payload: dict[str, Any]) -> int:
        return emit_json(payload)

    def cmd_auth_link(args: argparse.Namespace) -> int:
        raw = [item.strip() for item in re.split(r"[\s,]+", args.scopes or "") if item.strip()]
        if not raw:
            raise SystemExit("provide --scopes, e.g. --scopes drive:drive offline_access")
        if args.mode == "user-oauth":
            payload = api.request_user_oauth_link(scopes=raw)
        else:
            payload = api.build_auth_link(scopes=raw, token_type=args.token_type)
        return emit(payload)

    def cmd_permission_bundle(args: argparse.Namespace) -> int:
        if args.list_presets:
            return emit({"presets": api.list_app_scope_presets()})
        payload = api.build_permission_bundle(
            preset_names=list(args.preset or []),
            scopes=list(args.scope or []),
            token_type=args.token_type,
        )
        return emit(payload)

    def cmd_auth(args: argparse.Namespace) -> int:
        payload = api.build_auth_bundle(
            include_group_open_reply=not bool(args.no_group_open_reply),
            include_attachment_oauth=not bool(args.no_attachment_oauth),
        )
        return emit(payload)

    def cmd_init(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        repo_config_path = root / "pm.json"
        args.config = str(repo_config_path)
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
            explicit_name=str(args.tasklist_name or "").strip(),
            english_name=english_name,
            agent_id=agent_id,
        )
        resolved_doc_folder_name = resolve_doc_folder_name(
            api,
            root,
            project_name,
            explicit_name=str(args.doc_folder_name or "").strip(),
            english_name=english_name,
            agent_id=agent_id,
        )
        configured_tasklist_guid = str(args.tasklist_guid or current_task_cfg(api).get("tasklist_guid") or "").strip()
        configured_doc_folder_token = str(args.doc_folder_token or current_doc_cfg(api).get("folder_token") or "").strip()

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

        resolved_task_backend = str(args.task_backend or current_task_backend(api)).strip() or "feishu"
        resolved_doc_backend = str(args.doc_backend or current_doc_backend(api)).strip() or "feishu"
        auth_bundle = None if args.no_auth_bundle else api.build_auth_bundle(
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

        workspace_bootstrap = None
        if group_id:
            openclaw_config_path = resolved_openclaw_config_path
            if openclaw_config_path is None:
                raise SystemExit("openclaw.json not found; provide --openclaw-config")
            workspace_root = api.resolve_workspace_root(
                openclaw_config_path=openclaw_config_path,
                agent_id=agent_id,
                explicit=args.workspace_root,
            )
            profile = api.build_workspace_profile(
                project_name=project_name,
                english_name=english_name,
                agent_id=agent_id,
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
                config_path=openclaw_config_path,
                agent_id=agent_id,
                workspace_root=workspace_root,
                group_id=group_id,
                channel=str(args.channel or "feishu").strip() or "feishu",
                skills=list(args.skill or []),
                allow_agents=list(args.allow_agent or []),
                model_primary=str(args.model_primary or "").strip(),
                replace_binding=bool(args.replace_binding),
                dry_run=bool(args.dry_run),
            )
            workspace_bootstrap = {
                "project_name": project_name,
                "english_name": english_name,
                "agent_id": agent_id,
                "workspace_root": str(workspace_root),
                "group_id": group_id,
                "profile": profile,
                "scaffold": scaffold_result,
                "registration": register_result,
            }

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
                config_payload["project"]["name"] = project_name
            if group_id:
                config_payload["project"]["group_id"] = group_id
            if isinstance(workspace_bootstrap, dict) and str(workspace_bootstrap.get("agent_id") or "").strip():
                config_payload["project"]["agent"] = str(workspace_bootstrap.get("agent_id") or "").strip()

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
        main_digest_registration = main_review_registration
        project_review_cfg = config_payload.get("project_review") if isinstance(config_payload.get("project_review"), dict) else {}
        nightly_cfg = project_review_cfg.get("nightly") if isinstance(project_review_cfg.get("nightly"), dict) else {}
        nightly_enabled = bool(nightly_cfg.get("enabled"))
        nightly_review_registration: dict[str, Any] = {
            "status": "skipped",
            "reason": "not_enabled",
        }
        register_nightly_review_job = getattr(api, "register_nightly_review_job", None)
        if nightly_enabled:
            if not callable(register_nightly_review_job):
                nightly_review_registration = {
                    "status": "skipped",
                    "reason": "helper_unavailable",
                }
            elif resolved_openclaw_config_path is None:
                nightly_review_registration = {
                    "status": "skipped",
                    "reason": "openclaw_config_not_found",
                }
            else:
                project_cfg = config_payload.get("project") if isinstance(config_payload.get("project"), dict) else {}
                nightly_review_registration = register_nightly_review_job(
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

        warnings = []
        if deprecated_command:
            warnings.append(f"`{deprecated_command}` 已弃用，请改用 `init`。")
        if explicit_tasklist_name:
            warnings.append("`--tasklist-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
        if explicit_doc_folder_name:
            warnings.append("`--doc-folder-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")

        if args.dry_run:
            api.ACTIVE_CONFIG.update(config_payload)
            docs_preview = api.ensure_project_docs(root, dry_run=True)
            return emit(
                {
                    "status": "dry_run",
                    "warnings": warnings,
                    "config_path": str(config_path),
                    "repo_root": str(root),
                    "project_name": project_name,
                    "naming_mode": "project_name_default" if not (explicit_tasklist_name or explicit_doc_folder_name) else "explicit_override",
                    "resolved_tasklist_name": resolved_tasklist_name,
                    "resolved_doc_folder_name": resolved_doc_folder_name,
                    "tasklist_inspection": task_inspection,
                    "docs_preview": docs_preview,
                    "workspace_bootstrap": workspace_bootstrap,
                    "auth_bundle": auth_bundle,
                    "main_review_registration": main_review_registration,
                    "main_digest_registration": main_digest_registration,
                    "nightly_review_registration": nightly_review_registration,
                    "config_preview": config_payload,
                }
            )

        tasklist = api.ensure_tasklist(resolved_tasklist_name)
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
        run_payload = None
        auto_run_reason = "disabled_by_flag" if args.skip_auto_run else "not_requested"
        if not args.skip_auto_run:
            if isinstance(bootstrap_task, dict) and bootstrap_task.get("created"):
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
                auto_run_reason = "bootstrap_task_created"
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
            else:
                auto_run_reason = "bootstrap_task_not_created"

        return emit(
            {
                "status": "initialized",
                "warnings": warnings,
                "config_path": str(config_path),
                "repo_root": str(root),
                "pm_dir": str(api.pm_dir_path(str(root))),
                "project_name": project_name,
                "naming_mode": "project_name_default" if not (explicit_tasklist_name or explicit_doc_folder_name) else "explicit_override",
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
                "auth_bundle": auth_bundle,
                "main_review_registration": main_review_registration,
                "main_digest_registration": main_digest_registration,
                "nightly_review_registration": nightly_review_registration,
            }
        )

    def cmd_workspace_delete(args: argparse.Namespace) -> int:
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
        resolved_agent_id = str(registration.get("resolved_agent_id") or agent_id).strip()
        resolved_group_id = str(registration.get("resolved_group_id") or group_id).strip()
        resolved_channel = str(registration.get("resolved_channel") or channel).strip() or channel

        tasklist_name = str(task_cfg.get("tasklist_name") or "").strip()
        tasklist_guid = str(task_cfg.get("tasklist_guid") or "").strip()
        tasklist_cleanup: dict[str, Any]
        if str(task_cfg.get("backend") or "feishu").strip() != "feishu":
            tasklist_cleanup = {"status": "skipped", "reason": "backend_not_feishu"}
        else:
            inspection = api.inspect_tasklist(tasklist_name, configured_guid=tasklist_guid) if (tasklist_name or tasklist_guid) else {}
            tasklist = inspection.get("tasklist") if isinstance(inspection.get("tasklist"), dict) else {}
            resolved_tasklist_guid = str(tasklist.get("guid") or tasklist_guid).strip()
            if not resolved_tasklist_guid:
                tasklist_cleanup = {"status": "missing", "inspection": inspection}
            elif args.dry_run:
                tasklist_cleanup = {
                    "status": "dry_run",
                    "tasklist_guid": resolved_tasklist_guid,
                    "tasklist_name": str(tasklist.get("name") or tasklist_name).strip(),
                    "inspection": inspection,
                }
            else:
                api.run_bridge("feishu_task_tasklist", "delete", {"tasklist_guid": resolved_tasklist_guid})
                tasklist_cleanup = {
                    "status": "deleted",
                    "tasklist_guid": resolved_tasklist_guid,
                    "tasklist_name": str(tasklist.get("name") or tasklist_name).strip(),
                    "inspection": inspection,
                }

        folder_name = str(doc_cfg.get("folder_name") or "").strip()
        folder_token = str(doc_cfg.get("folder_token") or "").strip()
        docs_cleanup: dict[str, Any]
        if str(doc_cfg.get("backend") or "feishu").strip() != "feishu":
            docs_cleanup = {"status": "skipped", "reason": "backend_not_feishu"}
        else:
            folder_node = api.find_root_folder_by_name(folder_name) if (not folder_token and folder_name) else None
            resolved_folder_token = folder_token or str((folder_node or {}).get("token") or (folder_node or {}).get("file_token") or "").strip()
            if not resolved_folder_token:
                docs_cleanup = {"status": "missing", "folder_name": folder_name}
            elif args.dry_run:
                docs_cleanup = {
                    "status": "dry_run",
                    "folder_token": resolved_folder_token,
                    "folder_name": folder_name or str((folder_node or {}).get("name") or "").strip(),
                }
            else:
                api.run_bridge("feishu_drive_file", "delete", {"file_token": resolved_folder_token, "type": "folder"})
                docs_cleanup = {
                    "status": "deleted",
                    "folder_token": resolved_folder_token,
                    "folder_name": folder_name or str((folder_node or {}).get("name") or "").strip(),
                }

        source_key = ""
        try:
            source_key = str(api.project_slug(project_name, "", resolved_agent_id or agent_id)).strip()
        except Exception:
            source_key = ""
        main_digest_cleanup = api.unregister_main_digest_source(
            openclaw_config_path=openclaw_config_path,
            repo_root=root or Path.cwd(),
            source_key=source_key,
            dry_run=bool(args.dry_run),
        )
        nightly_review_cleanup = api.unregister_nightly_review_job(
            openclaw_config_path=openclaw_config_path,
            repo_root=root or Path.cwd(),
            project_name=project_name,
            dry_run=bool(args.dry_run),
        )
        registration_cleanup = api.unregister_workspace(
            config_path=openclaw_config_path,
            agent_id=resolved_agent_id,
            workspace_root=workspace_root,
            group_id=resolved_group_id,
            channel=resolved_channel,
            dry_run=bool(args.dry_run),
        )

        if args.dry_run or not repo_config_path.exists():
            repo_config_cleanup = {
                "status": "dry_run" if args.dry_run and repo_config_path.exists() else "missing",
                "config_path": str(repo_config_path),
                "cleared_fields": _cleanup_repo_config_for_workspace_delete(json.loads(json.dumps(config_payload, ensure_ascii=False))) if repo_config_path.exists() else [],
            }
        else:
            cleared_fields = _cleanup_repo_config_for_workspace_delete(config_payload)
            repo_config_path.write_text(json.dumps(config_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            repo_config_cleanup = {
                "status": "updated",
                "config_path": str(repo_config_path),
                "cleared_fields": cleared_fields,
            }

        workspace_cleanup: dict[str, Any]
        if workspace_root is None:
            workspace_cleanup = {"status": "missing", "path": ""}
        elif args.dry_run:
            workspace_cleanup = {
                "status": "dry_run",
                "path": str(workspace_root),
                "exists": workspace_root.exists(),
            }
        else:
            existed = workspace_root.exists()
            if existed:
                shutil.rmtree(workspace_root)
            workspace_cleanup = {
                "status": "deleted" if existed else "missing",
                "path": str(workspace_root),
                "exists": existed,
            }

        return emit(
            {
                "status": "dry_run" if args.dry_run else "deleted",
                "repo_root": str(root) if isinstance(root, Path) else "",
                "config_path": str(repo_config_path),
                "openclaw_config_path": str(openclaw_config_path),
                "project_name": project_name,
                "agent_id": resolved_agent_id,
                "group_id": resolved_group_id,
                "channel": resolved_channel,
                "workspace_root": str(workspace_root) if isinstance(workspace_root, Path) else "",
                "tasklist_cleanup": tasklist_cleanup,
                "docs_cleanup": docs_cleanup,
                "main_digest_cleanup": main_digest_cleanup,
                "nightly_review_cleanup": nightly_review_cleanup,
                "registration_cleanup": registration_cleanup,
                "repo_config_cleanup": repo_config_cleanup,
                "workspace_cleanup": workspace_cleanup,
            }
        )

    return {
        "auth": cmd_auth,
        "auth_link": cmd_auth_link,
        "permission_bundle": cmd_permission_bundle,
        "init": cmd_init,
        "workspace_delete": cmd_workspace_delete,
    }
