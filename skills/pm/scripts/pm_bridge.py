from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


def bridge_script_path(candidates: Sequence[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path(candidates[0])


def run_bridge(
    bridge_script_candidates: Sequence[Path],
    tool: str,
    action: str,
    args: dict[str, Any] | None = None,
    *,
    session_key: str = "",
    message_channel: str = "",
    account_id: str = "",
    message_to: str = "",
    thread_id: str = "",
) -> dict[str, Any]:
    payload = json.dumps(args or {}, ensure_ascii=False)
    bridge_script = bridge_script_path(bridge_script_candidates)
    cmd = [
        sys.executable,
        str(bridge_script),
        "--tool",
        tool,
        "--args",
        payload,
    ]
    if action:
        cmd.extend(["--action", action])
    if session_key:
        cmd.extend(["--session-key", session_key])
    if message_channel:
        cmd.extend(["--message-channel", message_channel])
    if account_id:
        cmd.extend(["--account-id", account_id])
    if message_to:
        cmd.extend(["--message-to", message_to])
    if thread_id:
        cmd.extend(["--thread-id", thread_id])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or proc.stdout.strip() or f"bridge call failed: {tool}.{action}")
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"bridge returned non-JSON output for {tool}.{action}: {exc}") from exc


def details_of(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("details"), dict):
        return payload["details"]
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("details"), dict):
        return result["details"]
    return {}
