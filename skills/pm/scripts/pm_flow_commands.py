from __future__ import annotations

import argparse
from typing import Any

from pm_command_support import CommandHandler, emit_json


def build_flow_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def emit(payload: dict[str, Any]) -> int:
        return emit_json(payload)

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

    return {
        "context": cmd_context,
        "next": cmd_next,
        "plan": cmd_plan,
        "refine": cmd_refine,
        "coder_context": cmd_coder_context,
        "run": cmd_run,
    }
