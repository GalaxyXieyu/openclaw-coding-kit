from __future__ import annotations

from typing import Any

from pm_command_support import CommandHandler, task_summary_text
from pm_flow_commands import build_flow_command_handlers
from pm_gsd_commands import build_gsd_command_handlers
from pm_init_commands import build_init_command_handlers
from pm_task_commands import build_task_command_handlers


def build_command_handlers(api: Any) -> dict[str, CommandHandler]:
    handlers: dict[str, CommandHandler] = {}
    for factory in (
        build_init_command_handlers,
        build_gsd_command_handlers,
        build_flow_command_handlers,
        build_task_command_handlers,
    ):
        handlers.update(factory(api))
    return handlers


__all__ = ["build_command_handlers", "task_summary_text"]
