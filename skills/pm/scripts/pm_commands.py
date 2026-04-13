from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

CommandHandler = Callable[[argparse.Namespace], int]


def task_summary_text(item: dict[str, Any]) -> str:
    return str(item.get("normalized_summary") or item.get("summary") or "").strip()


def build_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def emit(payload: dict[str, Any]) -> int:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

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

    def current_task_cfg() -> dict[str, Any]:
        value = api.ACTIVE_CONFIG.get("task")
        return value if isinstance(value, dict) else {}

    def current_doc_cfg() -> dict[str, Any]:
        value = api.ACTIVE_CONFIG.get("doc")
        return value if isinstance(value, dict) else {}

    def current_project_cfg() -> dict[str, Any]:
        value = api.ACTIVE_CONFIG.get("project")
        return value if isinstance(value, dict) else {}

    def current_task_backend() -> str:
        return str(current_task_cfg().get("backend") or api.default_config()["task"]["backend"]).strip() or "feishu"

    def current_doc_backend() -> str:
        return str(current_doc_cfg().get("backend") or api.default_config()["doc"]["backend"]).strip() or "feishu"

    def safe_project_label(project_name: str, english_name: str = "", agent_id: str = "") -> str:
        try:
            return str(api.project_display_name(project_name, english_name, agent_id)).strip()
        except Exception:
            return str(project_name or "").strip()

    def resolve_tasklist_name(root: Any, project_name: str, *, explicit_name: str = "", english_name: str = "", agent_id: str = "") -> str:
        explicit = str(explicit_name or "").strip()
        if explicit:
            return explicit
        task_cfg = current_task_cfg()
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
            return safe_project_label(project_name, english_name, agent_id) or str(root.name)

    def resolve_doc_folder_name(root: Any, project_name: str, *, explicit_name: str = "", english_name: str = "", agent_id: str = "") -> str:
        explicit = str(explicit_name or "").strip()
        if explicit:
            return explicit
        doc_cfg = current_doc_cfg()
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
            return safe_project_label(project_name, english_name, agent_id) or str(root.name)

    def cmd_init(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        repo_config_path = root / "pm.json"
        args.config = str(repo_config_path)
        deprecated_command = str(getattr(args, "_deprecated_command", "") or "").strip()
        explicit_tasklist_name = str(args.tasklist_name or "").strip()
        explicit_doc_folder_name = str(args.doc_folder_name or "").strip()

        configured_project_name = str(current_project_cfg().get("name") or "").strip()
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
            root,
            project_name,
            explicit_name=str(args.tasklist_name or "").strip(),
            english_name=english_name,
            agent_id=agent_id,
        )
        resolved_doc_folder_name = resolve_doc_folder_name(
            root,
            project_name,
            explicit_name=str(args.doc_folder_name or "").strip(),
            english_name=english_name,
            agent_id=agent_id,
        )
        configured_tasklist_guid = str(args.tasklist_guid or current_task_cfg().get("tasklist_guid") or "").strip()
        configured_doc_folder_token = str(args.doc_folder_token or current_doc_cfg().get("folder_token") or "").strip()

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

        resolved_task_backend = str(args.task_backend or current_task_backend()).strip() or "feishu"
        resolved_doc_backend = str(args.doc_backend or current_doc_backend()).strip() or "feishu"
        auth_bundle = None if args.no_auth_bundle else api.build_auth_bundle(
            include_group_open_reply=True,
            include_attachment_oauth=True,
            explicit_openclaw_config=str(args.openclaw_config or "").strip(),
        )

        workspace_bootstrap = None
        if group_id:
            openclaw_config_path = api.resolve_openclaw_config_path(args.openclaw_config)
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

        if args.dry_run:
            api.ACTIVE_CONFIG.update(config_payload)
            docs_preview = api.ensure_project_docs(root, dry_run=True)
            warnings = []
            if deprecated_command:
                warnings.append(f"`{deprecated_command}` 已弃用，请改用 `init`。")
            if explicit_tasklist_name:
                warnings.append("`--tasklist-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
            if explicit_doc_folder_name:
                warnings.append("`--doc-folder-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
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
        warnings = []
        if deprecated_command:
            warnings.append(f"`{deprecated_command}` 已弃用，请改用 `init`。")
        if explicit_tasklist_name:
            warnings.append("`--tasklist-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
        if explicit_doc_folder_name:
            warnings.append("`--doc-folder-name` 仅保留为兼容覆盖参数；默认应只传 `--project-name`。")
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
            }
        )

    def cmd_sync_gsd_docs(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.sync_gsd_docs(root=root, include=list(args.include or []))
        refreshed = api.refresh_context_cache()
        payload["context_path"] = str(api.pm_file("current-context.json", str(root)))
        payload["doc_index"] = refreshed.get("doc_index") or {}
        payload["gsd"] = refreshed.get("gsd") or {}
        return emit(payload)

    def cmd_sync_gsd_progress(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        task_guid = str(args.task_guid or "").strip()
        if not task_guid and str(args.task_id or "").strip():
            task = api.get_task_record(args.task_id, include_completed=args.include_completed)
            task_guid = str(task.get("guid") or "").strip()
        payload = api.sync_gsd_progress(
            root=root,
            phase=str(args.phase or "").strip(),
            task_guid=task_guid,
            append_to_state=not args.no_state_append,
        )
        payload["context_path"] = str(api.pm_file("current-context.json", str(root)))
        return emit(payload)

    def cmd_materialize_gsd_tasks(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.materialize_gsd_tasks(root=root, phase=str(args.phase or "").strip())
        refreshed = api.refresh_context_cache()
        payload["context_path"] = str(api.pm_file("current-context.json", str(root)))
        payload["doc_index"] = refreshed.get("doc_index") or {}
        payload["gsd"] = refreshed.get("gsd") or {}
        return emit(payload)

    def cmd_route_gsd(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.route_gsd_work(root, phase=str(args.phase or "").strip(), prefer_pm_tasks=True)
        refreshed = api.refresh_context_cache()
        return emit(
            {
                "repo_root": str(root),
                "route": payload,
                "context_path": str(api.pm_file("current-context.json", str(root))),
                "doc_index": refreshed.get("doc_index") or {},
                "gsd": refreshed.get("gsd") or {},
            }
        )

    def cmd_plan_phase(args: argparse.Namespace) -> int:
        root = api.project_root_path(args.repo_root)
        api.ACTIVE_CONFIG["repo_root"] = str(root)
        payload = api.plan_gsd_phase_workflow(
            root=root,
            phase=str(args.phase or "").strip(),
            task_id=str(args.task_id or "").strip(),
            task_guid=str(args.task_guid or "").strip(),
            include_completed=bool(args.include_completed),
            agent_id=str(args.agent or "").strip(),
            timeout_seconds=int(args.timeout or 0),
            thinking=str(args.thinking or "").strip(),
            research=bool(args.research),
            skip_research=bool(args.skip_research),
            gaps=bool(args.gaps),
            skip_verify=bool(args.skip_verify),
            prd=str(args.prd or "").strip(),
            reviews=bool(args.reviews),
            sync_docs=not args.no_doc_sync,
            sync_progress=not args.no_progress_sync,
            append_state=not args.no_state_append,
        )
        return emit(payload)

    def cmd_context(args: argparse.Namespace) -> int:
        use_cache = not args.refresh and not args.task_id and not args.task_guid
        if not use_cache:
            payload = api.refresh_context_cache(task_id=args.task_id, task_guid=args.task_guid)
        else:
            context_path = api.pm_file("current-context.json")
            cached = api.load_json_file(context_path)
            payload = cached if isinstance(cached, dict) else api.refresh_context_cache()
        return emit(payload)

    def cmd_next(args: argparse.Namespace) -> int:
        payload = api.refresh_context_cache() if args.refresh else api.build_context_payload()
        return emit({"next_task": payload.get("next_task"), "current_task": payload.get("current_task")})

    def cmd_plan(args: argparse.Namespace) -> int:
        payload, path = api.build_planning_bundle("plan", task_id=args.task_id, task_guid=args.task_guid, focus=args.focus)
        return emit({"bundle_path": str(path), "bundle": payload})

    def cmd_refine(args: argparse.Namespace) -> int:
        payload, path = api.build_planning_bundle("refine", task_id=args.task_id, task_guid=args.task_guid, focus=args.focus)
        return emit({"bundle_path": str(path), "bundle": payload})

    def cmd_coder_context(args: argparse.Namespace) -> int:
        payload, path = api.build_coder_context(task_id=args.task_id, task_guid=args.task_guid)
        return emit({"bundle_path": str(path), "bundle": payload})

    def cmd_run(args: argparse.Namespace) -> int:
        bundle, path = api.build_coder_context(task_id=args.task_id, task_guid=args.task_guid)
        coder = api.coder_config()
        backend = str(args.backend or coder.get("backend") or "acp").strip() or "acp"
        agent_id = str(args.agent or coder.get("agent_id") or "codex").strip() or "codex"
        timeout_seconds = int(args.timeout or coder.get("timeout") or 900)
        thinking = str(args.thinking or coder.get("thinking") or "high").strip()
        session_key = str(args.session_key or coder.get("session_key") or "main").strip() or "main"
        message = api.build_run_message(bundle)
        task = api.resolve_effective_task(bundle)
        task_id = str(task.get("task_id") or "").strip()
        label = api.build_run_label(api.project_root_path(), agent_id, task_id)
        if backend == "acp":
            result = api.spawn_acp_session(
                agent_id=agent_id,
                message=message,
                cwd=str(api.project_root_path()),
                timeout_seconds=timeout_seconds,
                thinking=thinking,
                label=label,
                session_key=session_key,
            )
            side_effects = api.persist_dispatch_side_effects(bundle, result, agent_id=agent_id, runtime="acp")
        elif backend == "codex-cli":
            result = api.run_codex_cli(
                agent_id=agent_id,
                message=message,
                cwd=str(api.project_root_path()),
                timeout_seconds=timeout_seconds,
                thinking=thinking,
            )
            side_effects = api.persist_run_side_effects(bundle, result)
        else:
            result = api.run_openclaw_agent(
                agent_id=agent_id,
                message=message,
                cwd=str(api.project_root_path()),
                timeout_seconds=timeout_seconds,
                thinking=thinking,
            )
            side_effects = api.persist_run_side_effects(bundle, result)
        payload = {
            "coder_context_path": str(path),
            "backend": backend,
            "agent_id": agent_id,
            "session_key": session_key,
            "timeout": timeout_seconds,
            "thinking": thinking,
            "message_preview": message[:1200],
            "result": result,
            "side_effects": side_effects,
        }
        api.write_pm_bundle("last-run.json", payload)
        return emit(payload)

    def cmd_create(args: argparse.Namespace) -> int:
        if args.tasklist_name:
            api.ACTIVE_CONFIG.setdefault("task", {})
            if isinstance(api.ACTIVE_CONFIG.get("task"), dict):
                api.ACTIVE_CONFIG["task"]["tasklist_name"] = str(args.tasklist_name).strip()
            api.ACTIVE_CONFIG["tasklist_name"] = str(args.tasklist_name).strip()
        tasklist = api.ensure_tasklist(args.tasklist_name)
        summary = args.summary.strip()
        if not args.force_new:
            existing = api.find_existing_task_by_summary(summary, include_completed=True)
            if isinstance(existing, dict) and str(existing.get("guid") or "").strip():
                context = api.refresh_context_cache(task_guid=str(existing.get("guid") or ""))
                parsed = api.parse_task_summary(task_summary_text(existing)) or {}
                return emit(
                    {
                        "task_id": str((parsed or {}).get("task_id") or existing.get("normalized_task_id") or ""),
                        "task": existing,
                        "tasklist": tasklist,
                        "deduplicated": True,
                        "context_path": str(api.pm_file("current-context.json")),
                        "next_task": context.get("next_task"),
                    }
                )
        task_id = api.next_task_id()
        title = f"[{task_id}] {summary}"
        description = api.build_description(task_id, summary, args.request or "", args.repo_root, args.kind)
        create_args: dict[str, Any] = {
            "summary": title,
            "description": description,
            "tasklists": [{"tasklist_guid": str(tasklist.get("guid") or "").strip()}],
        }
        owner = tasklist.get("owner") if isinstance(tasklist.get("owner"), dict) else {}
        current_user_id = str(owner.get("id") or "").strip()
        if current_user_id:
            create_args["current_user_id"] = current_user_id
        task = api.create_task(
            summary=title,
            description=description,
            tasklists=[{"tasklist_guid": str(tasklist.get("guid") or "").strip()}],
            current_user_id=current_user_id,
        )
        context = api.refresh_context_cache(task_guid=str(task.get("guid") or ""))
        return emit(
            {
                "task_id": task_id,
                "task": task,
                "tasklist": tasklist,
                "deduplicated": False,
                "context_path": str(api.pm_file("current-context.json")),
                "next_task": context.get("next_task"),
            }
        )

    def cmd_get(args: argparse.Namespace) -> int:
        task = api.get_task_record_by_guid(args.task_guid) if args.task_guid else api.get_task_record(args.task_id, include_completed=args.include_completed)
        guid = str(task.get("guid") or "").strip()
        comments = api.list_task_comments(guid, 20)
        parsed = api.parse_task_summary(task_summary_text(task))
        result = {
            "task_id": api.normalize_task_key(args.task_id) if args.task_id else str((parsed or {}).get("task_id") or ""),
            "summary": task.get("summary") or "",
            "normalized_summary": str((parsed or {}).get("normalized_summary") or task_summary_text(task)),
            "status": task.get("status") or "",
            "description": task.get("description") or "",
            "url": task.get("url") or "",
            "guid": task.get("guid") or "",
            "created_at": task.get("created_at") or "",
            "updated_at": task.get("updated_at") or "",
            "completed_at": task.get("completed_at") or "",
            "start": task.get("start") or {},
            "due": task.get("due") or {},
            "members": task.get("members") or [],
            "tasklists": task.get("tasklists") or [],
            "attachments": task.get("attachments") or [],
            "comments": comments,
        }
        return emit(result)

    def cmd_comment(args: argparse.Namespace) -> int:
        task = api.get_task_record_by_guid(args.task_guid) if args.task_guid else api.get_task_record(args.task_id, include_completed=args.include_completed)
        guid = str(task.get("guid") or "").strip()
        if not guid:
            raise SystemExit(f"task missing guid: {args.task_id or args.task_guid}")
        auto_started = api.ensure_task_started(task)
        content = args.content.strip()
        payload = api.create_task_comment(guid, content)
        context = api.refresh_context_cache(task_guid=guid)
        return emit(
            {
                "task_id": api.task_id_for_output(args.task_id),
                "task_guid": guid,
                "auto_started": bool(auto_started),
                "start_result": auto_started,
                "result": payload,
                "context_path": str(api.pm_file("current-context.json")),
                "next_task": context.get("next_task"),
            }
        )

    def cmd_complete(args: argparse.Namespace) -> int:
        task = api.get_task_record_by_guid(args.task_guid) if args.task_guid else api.get_task_record(args.task_id, include_completed=args.include_completed)
        guid = str(task.get("guid") or "").strip()
        if not guid:
            raise SystemExit(f"task missing guid: {args.task_id or args.task_guid}")
        content = api.resolve_optional_text_input(args.content, args.content_file)
        upload_result = api.upload_task_attachments(task, args.task_id, args.file)
        if upload_result.get("status") == "authorization_required":
            upload_result["pending_action"] = "complete"
            upload_result["content"] = content
            upload_result["commit_url"] = args.commit_url.strip() or ("" if args.skip_head_commit_url else api.current_head_commit_url(args.repo_root))
            return emit(upload_result)
        auto_started = upload_result.get("start_result")
        if upload_result.get("status") == "skipped":
            auto_started = api.ensure_task_started(task)
        commit_url = args.commit_url.strip() or ("" if args.skip_head_commit_url else api.current_head_commit_url(args.repo_root))
        completion_comment = api.build_completion_comment(content, commit_url, int(upload_result.get("uploaded_count") or 0))
        comment_payload: dict[str, Any] | None = None
        if completion_comment:
            comment_payload = api.create_task_comment(guid, completion_comment)
        completed_at = api.now_iso()
        payload = api.patch_task(guid, api.build_completion_changes(task, completed_at=completed_at))
        context = api.refresh_context_cache()
        return emit(
            {
                "task_id": api.task_id_for_output(args.task_id),
                "task_guid": guid,
                "auto_started": bool(auto_started),
                "start_result": auto_started,
                "completion_comment": completion_comment,
                "comment_result": comment_payload,
                "commit_url": commit_url,
                "upload_result": upload_result,
                "result": payload,
                "context_path": str(api.pm_file("current-context.json")),
                "next_task": context.get("next_task"),
            }
        )

    def cmd_update_description(args: argparse.Namespace) -> int:
        task = api.get_task_record_by_guid(args.task_guid) if args.task_guid else api.get_task_record(args.task_id, include_completed=args.include_completed)
        guid = str(task.get("guid") or "").strip()
        if not guid:
            raise SystemExit(f"task missing guid: {args.task_id or args.task_guid}")
        content = api.resolve_text_input(args.content, args.content_file)
        current = str(task.get("description") or "").strip()
        if args.mode == "replace":
            description = content
        else:
            separator = args.separator
            description = f"{current}{separator}{content}".strip() if current else content
        payload = api.patch_task(guid, {"description": description})
        context = api.refresh_context_cache(task_guid=guid)
        return emit(
            {
                "task_id": api.normalize_task_key(args.task_id) if args.task_id else "",
                "task_guid": guid,
                "mode": args.mode,
                "description": description,
                "result": payload,
                "context_path": str(api.pm_file("current-context.json")),
                "next_task": context.get("next_task"),
            }
        )

    def cmd_list(args: argparse.Namespace) -> int:
        rows = [item for item in api.task_pool(include_completed=args.include_completed) if api.extract_task_number(task_summary_text(item)) > 0]
        rows.sort(key=lambda item: api.extract_task_number(task_summary_text(item)), reverse=not args.asc)
        if args.limit:
            rows = rows[: args.limit]
        result = [
            {
                "task_id": str((api.parse_task_summary(task_summary_text(item)) or {}).get("task_id") or ""),
                "summary": item.get("summary") or "",
                "normalized_summary": str(item.get("normalized_summary") or item.get("summary") or ""),
                "status": item.get("status") or "",
                "guid": item.get("guid") or "",
                "url": item.get("url") or "",
                "created_at": item.get("created_at") or "",
                "updated_at": item.get("updated_at") or "",
            }
            for item in rows
        ]
        return emit({"tasks": result})

    def cmd_normalize_titles(args: argparse.Namespace) -> int:
        result = api.normalize_task_titles(include_completed=args.include_completed)
        api.refresh_context_cache()
        return emit(result)

    def cmd_search(args: argparse.Namespace) -> int:
        query = args.query.strip().lower()
        if not query:
            raise SystemExit("search query is required")
        matches: list[dict[str, Any]] = []
        for item in api.task_pool(include_completed=args.include_completed):
            summary = task_summary_text(item)
            parsed = api.parse_task_summary(summary)
            if not summary:
                continue
            if query in summary.lower():
                matches.append(
                    {
                        "task_id": str((parsed or {}).get("task_id") or ""),
                        "summary": item.get("summary") or "",
                        "normalized_summary": str((parsed or {}).get("normalized_summary") or summary),
                        "guid": item.get("guid") or "",
                        "completed_at": item.get("completed_at") or "0",
                    }
                )
                continue
            guid = str(item.get("guid") or "").strip()
            if not guid:
                continue
            task = api.get_task_record_by_guid(guid)
            description = str(task.get("description") or "")
            if query in description.lower():
                matches.append(
                    {
                        "task_id": str((parsed or {}).get("task_id") or ""),
                        "summary": item.get("summary") or "",
                        "normalized_summary": str((parsed or {}).get("normalized_summary") or summary),
                        "guid": guid,
                        "completed_at": item.get("completed_at") or "0",
                        "description_excerpt": description[:240],
                    }
                )
        matches.sort(key=lambda item: api.extract_task_number(str(item.get("normalized_summary") or item.get("summary") or "")), reverse=True)
        if args.limit:
            matches = matches[: args.limit]
        return emit({"tasks": matches})

    def cmd_attachments(args: argparse.Namespace) -> int:
        task = api.get_task_record_by_guid(args.task_guid) if args.task_guid else api.get_task_record(args.task_id, include_completed=args.include_completed)
        result = api.list_task_attachments(
            task,
            args.task_id,
            args.download_dir,
            task_id_for_output_fn=api.task_id_for_output,
            attachment_auth_result_fn=api.attachment_auth_result,
            feishu_credentials=api.feishu_credentials,
            request_json=api.request_json,
        )
        return emit(result)

    def cmd_upload_attachments(args: argparse.Namespace) -> int:
        task = api.get_task_record_by_guid(args.task_guid) if args.task_guid else api.get_task_record(args.task_id, include_completed=args.include_completed)
        result = api.upload_task_attachments(task, args.task_id, args.file)
        if str(result.get("status") or "") != "authorization_required":
            api.refresh_context_cache(task_guid=str(task.get("guid") or ""))
        return emit(result)

    return {
        "auth": cmd_auth,
        "auth_link": cmd_auth_link,
        "permission_bundle": cmd_permission_bundle,
        "init": cmd_init,
        "sync_gsd_docs": cmd_sync_gsd_docs,
        "sync_gsd_progress": cmd_sync_gsd_progress,
        "materialize_gsd_tasks": cmd_materialize_gsd_tasks,
        "route_gsd": cmd_route_gsd,
        "plan_phase": cmd_plan_phase,
        "context": cmd_context,
        "next": cmd_next,
        "plan": cmd_plan,
        "refine": cmd_refine,
        "coder_context": cmd_coder_context,
        "run": cmd_run,
        "create": cmd_create,
        "get": cmd_get,
        "comment": cmd_comment,
        "complete": cmd_complete,
        "update_description": cmd_update_description,
        "list": cmd_list,
        "normalize_titles": cmd_normalize_titles,
        "search": cmd_search,
        "attachments": cmd_attachments,
        "upload_attachments": cmd_upload_attachments,
    }
