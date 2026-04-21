from __future__ import annotations

from functools import partial
from typing import Any

from pm_command_support import CommandHandler
from pm_init_command_support import (
    cmd_auth,
    cmd_auth_link,
    cmd_init,
    cmd_permission_bundle,
    cmd_workspace_delete,
)


def build_init_command_handlers(api: Any) -> dict[str, CommandHandler]:
    return {
        "auth": partial(cmd_auth, api),
        "auth_link": partial(cmd_auth_link, api),
        "permission_bundle": partial(cmd_permission_bundle, api),
        "init": partial(cmd_init, api),
        "workspace_delete": partial(cmd_workspace_delete, api),
    }
