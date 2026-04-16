from __future__ import annotations

import argparse
from typing import Any

from pm_command_support import CommandHandler, emit_json


def emit_flow_payload(payload: dict[str, Any]) -> int:
    return emit_json(payload)


def context_command_payload(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    use_cache = not args.refresh and not args.task_id and not args.task_guid
    if not use_cache:
        return api.refresh_context_cache(task_id=args.task_id, task_guid=args.task_guid)
    context_path = api.pm_file("current-context.json")
    cached = api.load_json_file(context_path)
    return cached if isinstance(cached, dict) else api.refresh_context_cache()


def bundle_command_payload(api: Any, bundle_kind: str, args: argparse.Namespace) -> dict[str, Any]:
    payload, path = api.build_planning_bundle(bundle_kind, task_id=args.task_id, task_guid=args.task_guid, focus=args.focus)
    return {"bundle_path": str(path), "bundle": payload}


def coder_context_command_payload(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    payload, path = api.build_coder_context(task_id=args.task_id, task_guid=args.task_guid)
    return {"bundle_path": str(path), "bundle": payload}


def resolve_run_settings(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    coder = api.coder_config()
    return {
        "backend": str(args.backend or coder.get("backend") or "acp").strip() or "acp",
        "agent_id": str(args.agent or coder.get("agent_id") or "codex").strip() or "codex",
        "timeout_seconds": int(args.timeout or coder.get("timeout") or 900),
        "thinking": str(args.thinking or coder.get("thinking") or "high").strip(),
        "session_key": str(args.session_key or coder.get("session_key") or "main").strip() or "main",
    }


def dispatch_run_backend(
    api: Any,
    *,
    bundle: dict[str, Any],
    settings: dict[str, Any],
    message: str,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    repo_root = str(api.project_root_path())
    backend = str(settings["backend"])
    agent_id = str(settings["agent_id"])
    timeout_seconds = int(settings["timeout_seconds"])
    thinking = str(settings["thinking"])
    if backend == "acp":
        result = api.spawn_acp_session(
            agent_id=agent_id,
            message=message,
            cwd=repo_root,
            timeout_seconds=timeout_seconds,
            thinking=thinking,
            label=label,
            session_key=str(settings["session_key"]),
        )
        side_effects = api.persist_dispatch_side_effects(bundle, result, agent_id=agent_id, runtime="acp")
        return result, side_effects
    if backend == "codex-cli":
        result = api.run_codex_cli(
            agent_id=agent_id,
            message=message,
            cwd=repo_root,
            timeout_seconds=timeout_seconds,
            thinking=thinking,
        )
    else:
        result = api.run_openclaw_agent(
            agent_id=agent_id,
            message=message,
            cwd=repo_root,
            timeout_seconds=timeout_seconds,
            thinking=thinking,
        )
    return result, api.persist_run_side_effects(bundle, result)


def run_command_payload(api: Any, args: argparse.Namespace) -> dict[str, Any]:
    bundle, path = api.build_coder_context(task_id=args.task_id, task_guid=args.task_guid)
    settings = resolve_run_settings(api, args)
    message = api.build_run_message(bundle)
    task = api.resolve_effective_task(bundle)
    task_id = str(task.get("task_id") or "").strip()
    label = api.build_run_label(api.project_root_path(), str(settings["agent_id"]), task_id)
    result, side_effects = dispatch_run_backend(api, bundle=bundle, settings=settings, message=message, label=label)
    payload = {
        "coder_context_path": str(path),
        "backend": settings["backend"],
        "agent_id": settings["agent_id"],
        "session_key": settings["session_key"],
        "timeout": settings["timeout_seconds"],
        "thinking": settings["thinking"],
        "message_preview": message[:1200],
        "result": result,
        "side_effects": side_effects,
    }
    api.write_pm_bundle("last-run.json", payload)
    return payload


def build_flow_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def cmd_context(args: argparse.Namespace) -> int:
        return emit_flow_payload(context_command_payload(api, args))

    def cmd_next(args: argparse.Namespace) -> int:
        payload = api.refresh_context_cache() if args.refresh else api.build_context_payload()
        return emit_flow_payload({"next_task": payload.get("next_task"), "current_task": payload.get("current_task")})

    def cmd_plan(args: argparse.Namespace) -> int:
        return emit_flow_payload(bundle_command_payload(api, "plan", args))

    def cmd_refine(args: argparse.Namespace) -> int:
        return emit_flow_payload(bundle_command_payload(api, "refine", args))

    def cmd_coder_context(args: argparse.Namespace) -> int:
        return emit_flow_payload(coder_context_command_payload(api, args))

    def cmd_run(args: argparse.Namespace) -> int:
        return emit_flow_payload(run_command_payload(api, args))

    return {
        "context": cmd_context,
        "next": cmd_next,
        "plan": cmd_plan,
        "refine": cmd_refine,
        "coder_context": cmd_coder_context,
        "run": cmd_run,
    }
