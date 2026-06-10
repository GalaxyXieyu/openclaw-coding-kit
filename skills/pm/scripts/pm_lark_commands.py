from __future__ import annotations

import argparse
from typing import Any

from pm_command_support import CommandHandler, emit_json


def build_lark_command_handlers(api: Any) -> dict[str, CommandHandler]:
    def cmd_lark(args: argparse.Namespace) -> int:
        action = str(args.action or "status").strip()
        if action in {"status", "doctor"}:
            return emit_json(api.lark_health(action))
        if action == "login":
            return emit_json(api.lark_login(execute=bool(args.exec)))
        raise SystemExit(f"unsupported lark action: {action}")

    return {"lark": cmd_lark}
