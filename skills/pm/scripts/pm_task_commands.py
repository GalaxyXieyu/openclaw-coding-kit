from __future__ import annotations

from functools import partial
from typing import Any

from pm_command_support import CommandHandler
from pm_task_command_support import (
    cmd_attachments,
    cmd_backfill_assignees,
    cmd_comment,
    cmd_complete,
    cmd_create,
    cmd_get,
    cmd_list,
    cmd_normalize_titles,
    cmd_search,
    cmd_update_description,
    cmd_upload_attachments,
)


def build_task_command_handlers(api: Any) -> dict[str, CommandHandler]:
    return {
        "create": partial(cmd_create, api),
        "get": partial(cmd_get, api),
        "comment": partial(cmd_comment, api),
        "complete": partial(cmd_complete, api),
        "update_description": partial(cmd_update_description, api),
        "list": partial(cmd_list, api),
        "normalize_titles": partial(cmd_normalize_titles, api),
        "search": partial(cmd_search, api),
        "backfill_assignees": partial(cmd_backfill_assignees, api),
        "attachments": partial(cmd_attachments, api),
        "upload_attachments": partial(cmd_upload_attachments, api),
    }
