from __future__ import annotations

from dataclasses import dataclass
import json
import os
import subprocess
from typing import Any, Iterable

from pm_config import ACTIVE_CONFIG, default_config

UPDATE_TASK_FIELDS = {"summary", "description", "start", "due", "completed_at", "members"}

OPENCLAW_ENV_PREFIXES = ("OPENCLAW_", "CLAWDBOT_")
OPENCLAW_ENV_NAMES = {
    "CLAUDE_CODE_OPENCLAW_CONTEXT",
    "PM_ALLOW_WORKSPACE_OPENCLAW_CONFIG",
}
SUPPORTED_HEALTH_ACTIONS = {
    ("lark_cli", "status"),
    ("lark_cli", "doctor"),
    ("feishu_lark_cli", "status"),
    ("feishu_lark_cli", "doctor"),
}
LARK_HEALTH_ACTIONS = {"status", "doctor"}


@dataclass(frozen=True)
class LarkCliConfig:
    cli_bin: str = "lark-cli"
    cli_profile: str = ""
    as_identity: str = "bot"


def _feishu_config() -> dict[str, Any]:
    raw = ACTIVE_CONFIG.get("feishu")
    if isinstance(raw, dict):
        return raw
    default_feishu = default_config().get("feishu", {})
    return default_feishu if isinstance(default_feishu, dict) else {}


def resolve_config() -> LarkCliConfig:
    cfg = _feishu_config()
    cli_bin = str(os.environ.get("LARK_CLI_BIN") or cfg.get("cli_bin") or "lark-cli").strip() or "lark-cli"
    cli_profile = str(os.environ.get("PM_LARK_PROFILE") or cfg.get("cli_profile") or "").strip()
    as_identity = str(os.environ.get("PM_LARK_AS") or cfg.get("as") or "bot").strip() or "bot"
    if as_identity not in {"bot", "user"}:
        raise SystemExit("invalid lark-cli identity: expected PM_LARK_AS or feishu.as to be 'bot' or 'user'")
    return LarkCliConfig(cli_bin=cli_bin, cli_profile=cli_profile, as_identity=as_identity)


def build_base_command(config: LarkCliConfig) -> list[str]:
    cmd = [config.cli_bin]
    if config.cli_profile:
        cmd.extend(["--profile", config.cli_profile])
    return cmd


def sanitized_env(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment for official lark-cli without OpenClaw routing context."""
    env = dict(os.environ if base is None else base)
    for name in list(env):
        if name in OPENCLAW_ENV_NAMES or any(name.startswith(prefix) for prefix in OPENCLAW_ENV_PREFIXES):
            env.pop(name, None)
    return env


def parse_json_output(stdout: str) -> Any:
    raw = str(stdout or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        values: list[Any] = []
        for line in raw.splitlines():
            text = line.strip()
            if not text:
                continue
            try:
                values.append(json.loads(text))
            except json.JSONDecodeError:
                continue
        if values:
            return values[-1] if len(values) == 1 else values
        raise SystemExit("lark-cli returned non-JSON output for a JSON-mode command")


def run_lark_cli(
    argv: Iterable[str],
    *,
    input_json: dict[str, Any] | None = None,
    dry_run: bool = False,
    json_output: bool = True,
    include_identity: bool = True,
) -> Any:
    config = resolve_config()
    cmd = build_base_command(config) + list(argv)
    if include_identity:
        cmd.extend(["--as", config.as_identity])
    if dry_run:
        cmd.append("--dry-run")
    if json_output and "--format" not in cmd:
        cmd.extend(["--format", "json"])

    input_text = json.dumps(input_json, ensure_ascii=False) if input_json is not None else None
    try:
        proc = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            check=False,
            env=sanitized_env(),
        )
    except FileNotFoundError as exc:
        raise SystemExit("lark-cli not found; install it and run: lark-cli auth login --recommend") from exc

    if proc.returncode != 0:
        message = (proc.stderr or proc.stdout or "").strip()
        lowered = message.lower()
        if any(token in lowered for token in ("unauthorized", "not authenticated", "not logged in", "401", "403")):
            raise SystemExit(f"lark-cli authentication required; run: lark-cli auth login --recommend\n{message}")
        raise SystemExit(message or f"lark-cli failed with exit code {proc.returncode}")

    if json_output:
        return parse_json_output(proc.stdout)
    return {"output": str(proc.stdout or "").strip(), "stderr": str(proc.stderr or "").strip()}


def _items_from_raw(raw: Any, *keys: str) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        values = raw
    elif isinstance(raw, dict):
        values = []
        for key in keys:
            candidate = raw.get(key)
            if isinstance(candidate, list):
                values = candidate
                break
        if not values and isinstance(raw.get("items"), list):
            values = raw["items"]
    else:
        values = []
    return [item for item in values if isinstance(item, dict)]


def _page_state(raw: Any) -> tuple[bool, str]:
    if not isinstance(raw, dict):
        return False, ""
    page_token = str(raw.get("page_token") or raw.get("next_page_token") or "").strip()
    return bool(raw.get("has_more") and page_token), page_token


def _run_paged(argv: list[str], list_key: str, *, extra_keys: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    page_token = ""
    while True:
        page_argv = list(argv)
        if page_token:
            page_argv.extend(["--page-token", page_token])
        raw = run_lark_cli(page_argv)
        for item in _items_from_raw(raw, list_key, *extra_keys):
            guid = str(item.get("guid") or item.get("task_guid") or item.get("id") or "").strip()
            dedup_key = guid or json.dumps(item, sort_keys=True, ensure_ascii=False)
            if dedup_key not in seen:
                rows.append(item)
                seen.add(dedup_key)
        has_more, page_token = _page_state(raw)
        if not has_more:
            break
    return rows


def search_tasklists(*, page_size: int = 100) -> list[dict[str, Any]]:
    return _run_paged(["task", "tasklists", "list", "--page-size", str(page_size)], "tasklists")


def list_tasklist_tasks(tasklist_guid: str, *, completed: bool, page_size: int = 100) -> list[dict[str, Any]]:
    guid = str(tasklist_guid or "").strip()
    if not guid:
        return []
    return _run_paged(
        ["task", "tasks", "list", "--tasklist-guid", guid, "--completed", "true" if completed else "false", "--page-size", str(page_size)],
        "tasks",
    )


def search_tasks(query: str, *, completed: bool | None = None, page_size: int = 100) -> list[dict[str, Any]]:
    argv = ["task", "tasks", "search", "--query", str(query or ""), "--page-size", str(page_size)]
    if completed is not None:
        argv.extend(["--completed", "true" if completed else "false"])
    return _run_paged(argv, "tasks")


def get_task(task_guid: str) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    if not guid:
        return {}
    raw = run_lark_cli(["task", "tasks", "get", "--task-guid", guid])
    if isinstance(raw, dict):
        task = raw.get("task")
        return task if isinstance(task, dict) else raw
    return {}


def _tasklist_guids(tasklists: list[dict[str, Any]] | None) -> list[str]:
    guids: list[str] = []
    for item in tasklists or []:
        if not isinstance(item, dict):
            continue
        guid = str(item.get("tasklist_guid") or item.get("guid") or item.get("id") or "").strip()
        if guid:
            guids.append(guid)
    return guids


def build_create_task_argv(summary: str, description: str, tasklists: list[dict[str, Any]] | None = None) -> list[str]:
    argv = ["task", "tasks", "create", "--summary", str(summary or ""), "--description", str(description or "")]
    for guid in _tasklist_guids(tasklists):
        argv.extend(["--tasklist-guid", guid])
    return argv


def build_update_task_argv(task_guid: str) -> list[str]:
    return ["task", "tasks", "update", "--task-guid", str(task_guid or "").strip()]


def _is_empty_update_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return not value
    return False


def build_update_task_data(changes: dict[str, Any] | None) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in (changes or {}).items():
        field = str(key or "").strip()
        if field not in UPDATE_TASK_FIELDS or _is_empty_update_value(value):
            continue
        data[field] = value
    return data


def update_task(task_guid: str, changes: dict[str, Any] | None) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    data = build_update_task_data(changes)
    if not guid or not data:
        return {}
    raw = run_lark_cli(build_update_task_argv(guid), input_json=data)
    if isinstance(raw, dict):
        task = raw.get("task")
        return task if isinstance(task, dict) else raw
    return {}


def create_task(
    *,
    summary: str,
    description: str,
    tasklists: list[dict[str, Any]] | None = None,
    current_user_id: str = "",
    members: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    input_json: dict[str, Any] = {}
    if current_user_id:
        input_json["current_user_id"] = current_user_id
    if members:
        input_json["members"] = members
    raw = run_lark_cli(build_create_task_argv(summary, description, tasklists), input_json=input_json or None)
    if isinstance(raw, dict):
        task = raw.get("task")
        return task if isinstance(task, dict) else raw
    return {}


def build_create_task_comment_argv(task_guid: str, content: str) -> list[str]:
    return ["task", "comments", "create", "--task-guid", str(task_guid or "").strip(), "--content", str(content or "")]


def create_task_comment(task_guid: str, content: str) -> dict[str, Any]:
    guid = str(task_guid or "").strip()
    if not guid or not str(content or "").strip():
        return {}
    raw = run_lark_cli(build_create_task_comment_argv(guid, content))
    if isinstance(raw, dict):
        comment = raw.get("comment")
        return comment if isinstance(comment, dict) else raw
    return {}


def lark_health(action: str) -> dict[str, Any]:
    key = str(action or "").strip()
    if key not in LARK_HEALTH_ACTIONS:
        raise SystemExit(f"unsupported lark action: {key}; expected status or doctor")
    if key == "status":
        raw = run_lark_cli(["auth", "status"], json_output=False, include_identity=False)
    else:
        raw = run_lark_cli(["doctor"], json_output=False, include_identity=False)
    return normalize_payload(raw if isinstance(raw, dict) else {"result": raw}, raw, "lark", key)


def lark_login_command() -> list[str]:
    return build_base_command(resolve_config()) + ["auth", "login", "--recommend"]


def lark_login(*, execute: bool = False) -> dict[str, Any]:
    cmd = lark_login_command()
    if not execute:
        return {
            "adapter": "lark-cli",
            "action": "login",
            "command": cmd,
            "message": "Run this command interactively to initialize official lark-cli auth.",
        }
    try:
        proc = subprocess.run(cmd, capture_output=False, text=True, check=False, env=sanitized_env())
    except FileNotFoundError as exc:
        raise SystemExit("lark-cli not found; install it and run: lark-cli auth login --recommend") from exc
    if proc.returncode != 0:
        raise SystemExit(f"lark-cli auth login failed with exit code {proc.returncode}")
    return {"adapter": "lark-cli", "action": "login", "status": "completed", "command": cmd}


def normalize_payload(details: dict[str, Any], raw: Any, tool: str, action: str) -> dict[str, Any]:
    return {
        "details": details if isinstance(details, dict) else {},
        "raw": raw,
        "adapter": "lark-cli",
        "tool": tool,
        "action": action,
    }


def unsupported_message(tool: str, action: str) -> str:
    return (
        f"{tool}.{action} is unsupported by the lark-cli adapter in Phase 1. "
        "Phase 2/3 will add task/comment/drive/doc business mappings. "
        "OpenClaw/Gateway is no longer a supported PM Feishu delivery path; use local backend if you need offline work."
    )


def run_bridge_compatible(tool: str, action: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
    _ = args or {}
    key = (str(tool or "").strip(), str(action or "").strip())
    if key not in SUPPORTED_HEALTH_ACTIONS:
        raise SystemExit(unsupported_message(key[0], key[1]))

    if key[1] == "status":
        raw = run_lark_cli(["auth", "status"], json_output=False, include_identity=False)
    else:
        raw = run_lark_cli(["doctor"], json_output=False, include_identity=False)
    return normalize_payload(raw if isinstance(raw, dict) else {"result": raw}, raw, key[0], key[1])
