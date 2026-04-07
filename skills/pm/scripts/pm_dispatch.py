from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

BridgeFn = Callable[..., dict[str, Any]]


def build_run_label(root: Path, agent_id: str, task_id: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", root.name.lower()).strip("-") or "repo"
    task_slug = re.sub(r"[^a-z0-9]+", "-", task_id.lower()).strip("-") or "bootstrap"
    return f"pm-{slug}-{agent_id}-{task_slug}"


def spawn_acp_session(
    run_bridge: BridgeFn,
    *,
    agent_id: str,
    message: str,
    cwd: str,
    timeout_seconds: int = 900,
    thinking: str = "high",
    label: str = "",
    session_key: str = "main",
) -> dict[str, Any]:
    args: dict[str, Any] = {
        "task": message,
        "runtime": "acp",
        "agentId": agent_id,
        "cwd": cwd,
        "runTimeoutSeconds": timeout_seconds,
        "thinking": thinking,
        "mode": "run",
        "cleanup": "keep",
    }
    if label:
        args["label"] = label
    return run_bridge("sessions_spawn", "", args, session_key=session_key)


def extract_dispatch_ids(dispatch_result: dict[str, Any]) -> tuple[str, str]:
    result = dispatch_result.get("result") if isinstance(dispatch_result.get("result"), dict) else dispatch_result
    if not isinstance(result, dict):
        return "", ""
    details = result.get("details") if isinstance(result.get("details"), dict) else {}
    session_key = str(details.get("childSessionKey") or result.get("childSessionKey") or "").strip()
    run_id = str(details.get("runId") or result.get("runId") or "").strip()
    return session_key, run_id
