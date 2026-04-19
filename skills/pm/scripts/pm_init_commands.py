from __future__ import annotations

import argparse
import json
import re
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
                    cron_expr=str(nightly_cfg.get("cron") or nightly_cfg.get("schedule") or "30 0 * * *").strip() or "30 0 * * *",
                    timezone_name=str(nightly_cfg.get("timezone") or "Asia/Shanghai").strip() or "Asia/Shanghai",
                    since=str(nightly_cfg.get("since") or "24 hours ago").strip() or "24 hours ago",
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
                run_args = argparse.Namespace(
                    task_id=selected_task_id,
                    task_guid=selected_task_guid,
                    backend=str((config_payload.get("coder") or {}).get("backend") or "acp"),
                    agent=args.agent or str((config_payload.get("coder") or {}).get("agent_id") or "codex"),
                    timeout=int(args.timeout or (config_payload.get("coder") or {}).get("timeout") or 900),
                    thinking=args.thinking or str((config_payload.get("coder") or {}).get("thinking") or "high"),
                    session_key=args.session_key or str((config_payload.get("coder") or {}).get("session_key") or "main"),
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

    return {
        "auth": cmd_auth,
        "auth_link": cmd_auth_link,
        "permission_bundle": cmd_permission_bundle,
        "init": cmd_init,
    }
