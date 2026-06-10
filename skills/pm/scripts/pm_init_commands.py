from __future__ import annotations

from functools import partial
from typing import Any

from pm_command_support import CommandHandler
from pm_init_command_support import cmd_init


def build_init_command_handlers(api: Any) -> dict[str, CommandHandler]:
    return {
        "init": partial(cmd_init, api),
    }
