from __future__ import annotations

import argparse
from typing import Any

from pm_command_support import CommandHandler, emit_json


def build_board_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def cmd_board(args: argparse.Namespace) -> int:
        if args.refresh:
            api.refresh_context_cache()
        payload = api.build_project_board(
            include_completed=bool(args.include_completed),
            tasklist_guid=str(args.tasklist_guid or ""),
            limit=int(args.limit),
            comment_limit=int(args.comment_limit),
            recent_events_limit=int(args.recent_events_limit),
            include_all_visible_tasklists=bool(args.all_visible_tasklists),
        )
        return emit_json(payload)

    def cmd_board_task(args: argparse.Namespace) -> int:
        if args.refresh:
            api.refresh_context_cache(task_id=args.task_id, task_guid=args.task_guid)
        payload = api.build_task_board_detail(
            task_id=str(args.task_id or ""),
            task_guid=str(args.task_guid or ""),
            include_completed=bool(args.include_completed),
            comment_limit=int(args.comment_limit),
        )
        return emit_json(payload)

    return {
        "board": cmd_board,
        "board_task": cmd_board_task,
    }
