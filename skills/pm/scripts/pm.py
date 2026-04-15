#!/usr/bin/env python3
"""Feishu-first taskflow utilities for project workspaces."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from pm_api import *  # noqa: F401,F403
from pm_cli import build_parser as build_pm_parser
from pm_commands import build_command_handlers
from pm_config import ACTIVE_CONFIG
from pm_config import load_config
from pm_config import repo_root
from pm_config import task_kind
from pm_config import tasklist_name


def build_parser():
    handlers = build_command_handlers(build_cli_api())
    return build_pm_parser(handlers=handlers)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    command_name = str(getattr(args, "command", "") or "")
    ACTIVE_CONFIG.clear()
    ACTIVE_CONFIG.update(load_config(args.config))
    if hasattr(args, "repo_root") and not getattr(args, "repo_root", ""):
        args.repo_root = repo_root()
    if hasattr(args, "kind") and not getattr(args, "kind", ""):
        args.kind = task_kind()
    if command_name not in {"init", "workspace-init"} and hasattr(args, "tasklist_name") and not getattr(args, "tasklist_name", ""):
        args.tasklist_name = tasklist_name()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
