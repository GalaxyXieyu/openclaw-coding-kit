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

    return {
        "context": cmd_context,
        "next": cmd_next,
        "plan": cmd_plan,
        "refine": cmd_refine,
        "coder_context": cmd_coder_context,
    }
