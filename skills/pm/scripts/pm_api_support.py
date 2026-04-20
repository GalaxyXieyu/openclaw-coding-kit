from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from pm_auth import DEFAULT_BOT_AUTH_COMMANDS
from pm_auth import build_auth_bundle as build_pm_auth_bundle
from pm_auth import build_auth_link as build_pm_auth_link
from pm_auth import build_permission_bundle as build_pm_permission_bundle
from pm_auth import ensure_attachment_token as ensure_pm_attachment_token
from pm_auth import feishu_credentials as load_feishu_credentials
from pm_auth import get_channel_app_info as get_pm_channel_app_info
from pm_auth import list_app_scope_presets as list_pm_app_scope_presets
from pm_auth import openclaw_config as load_openclaw_config
from pm_auth import request_json as auth_request_json
from pm_auth import request_user_oauth_link as request_pm_user_oauth_link
from pm_bridge import bridge_script_path as resolve_bridge_script_path
from pm_bridge import details_of as bridge_details_of
from pm_bridge import run_bridge as invoke_bridge
from pm_config import ACTIVE_CONFIG
from pm_config import OPENCLAW_CONFIG_PATHS
from pm_config import default_config
from pm_config import find_openclaw_config_path
from pm_io import STATE_DIR
from pm_io import load_json_file
from pm_io import unix_ts
from pm_project_review import register_main_digest_source as register_pm_main_digest_source
from pm_project_review import register_nightly_review_job as register_pm_nightly_review_job
from pm_runtime import resolve_runtime_path
from pm_workspace import build_workspace_profile as build_pm_workspace_profile
from pm_workspace import default_doc_folder_name as build_pm_default_doc_folder_name
from pm_workspace import default_tasklist_name as build_pm_default_tasklist_name
from pm_workspace import default_workspace_root as resolve_pm_default_workspace_root
from pm_workspace import english_project_name as resolve_pm_english_project_name
from pm_workspace import project_display_name as resolve_pm_project_display_name
from pm_workspace import project_slug as build_pm_project_slug
from pm_workspace import register_workspace as register_pm_workspace
from pm_workspace import scaffold_workspace as scaffold_pm_workspace

SKILL_ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT_CANDIDATES = (
    SKILL_ROOT.parent / "openclaw-lark-bridge" / "scripts" / "invoke_openclaw_tool.py",
    Path.home() / ".codex/skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py",
)
BRIDGE_SCRIPT_ENV_VARS = ("OPENCLAW_LARK_BRIDGE_SCRIPT", "OPENCLAW_BRIDGE_SCRIPT")
TOKEN_PATH = STATE_DIR / "attachment-oauth-token.json"
PENDING_AUTH_PATH = STATE_DIR / "attachment-oauth-pending.json"
DEFAULT_ATTACHMENT_SCOPES = (
    "task:task:read",
    "task:attachment:read",
    "task:attachment:write",
    "offline_access",
)
OPENCLAW_AGENT_SESSION_RE = re.compile(r"^agent:([^:]+):")
ACP_LABEL_STALE_GRACE_SECONDS_ENV_VARS = (
    "PM_ACP_LABEL_STALE_GRACE_SECONDS",
    "OPENCLAW_PM_ACP_LABEL_STALE_GRACE_SECONDS",
)
ACP_LABEL_STALE_GRACE_SECONDS_DEFAULT = 120


def _trim_env(name: str) -> str:
    return str(os.environ.get(name) or "").strip()


def _agent_id_from_session_key(session_key: str) -> str:
    match = OPENCLAW_AGENT_SESSION_RE.match(str(session_key or "").strip())
    return str(match.group(1) or "").strip() if match else ""


def resolve_current_openclaw_context() -> dict[str, str]:
    session_key = _trim_env("OPENCLAW_SESSION_KEY")
    if not session_key:
        return {}

    agent_id = _trim_env("OPENCLAW_AGENT_ID") or _agent_id_from_session_key(session_key)
    context = {
        "session_key": session_key,
        "agent_id": agent_id,
        "message_channel": _trim_env("OPENCLAW_MESSAGE_CHANNEL"),
        "account_id": _trim_env("OPENCLAW_ACCOUNT_ID"),
        "message_to": _trim_env("OPENCLAW_MESSAGE_TO"),
        "thread_id": _trim_env("OPENCLAW_THREAD_ID"),
    }

    route_fields = ("message_channel", "account_id", "message_to", "thread_id")
    needs_lookup = any(not str(context.get(field) or "").strip() for field in route_fields)
    if needs_lookup and agent_id:
        state_dir_raw = _trim_env("OPENCLAW_STATE_DIR")
        state_dir = Path(state_dir_raw).expanduser().resolve() if state_dir_raw else STATE_DIR
        sessions_path = state_dir / "agents" / agent_id / "sessions" / "sessions.json"
        payload = load_json_file(sessions_path)
        session_entry = payload.get(session_key) if isinstance(payload, dict) else None
        if isinstance(session_entry, dict):
            delivery_context = session_entry.get("deliveryContext") if isinstance(session_entry.get("deliveryContext"), dict) else {}
            origin = session_entry.get("origin") if isinstance(session_entry.get("origin"), dict) else {}
            context["message_channel"] = str(
                context["message_channel"]
                or delivery_context.get("channel")
                or session_entry.get("channel")
                or origin.get("provider")
                or ""
            ).strip()
            context["account_id"] = str(
                context["account_id"]
                or delivery_context.get("accountId")
                or session_entry.get("lastAccountId")
                or origin.get("accountId")
                or ""
            ).strip()
            context["message_to"] = str(
                context["message_to"]
                or delivery_context.get("to")
                or session_entry.get("lastTo")
                or origin.get("to")
                or ""
            ).strip()
            context["thread_id"] = str(
                context["thread_id"]
                or delivery_context.get("threadId")
                or session_entry.get("threadId")
                or origin.get("threadId")
                or ""
            ).strip()

    return {key: value for key, value in context.items() if str(value or "").strip()}


def resolve_dispatch_session_key(explicit_session_key: str = "", *, fallback: str = "") -> str:
    explicit = str(explicit_session_key or "").strip()
    if explicit:
        return explicit
    current = resolve_current_openclaw_context()
    current_session_key = str(current.get("session_key") or "").strip()
    if current_session_key:
        return current_session_key
    resolved_fallback = str(fallback or "").strip()
    return resolved_fallback or "main"


def _bridge_script_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []
    explicit = resolve_runtime_path(env_vars=BRIDGE_SCRIPT_ENV_VARS)
    if explicit is not None:
        candidates.append(explicit)
    for candidate in BRIDGE_SCRIPT_CANDIDATES:
        expanded = candidate.expanduser()
        if expanded not in candidates:
            candidates.append(expanded)
    return tuple(candidates)


def bridge_script_path() -> Path:
    return resolve_bridge_script_path(_bridge_script_candidates())


def get_channel_app_info() -> dict[str, str]:
    return get_pm_channel_app_info(find_openclaw_config_path)


def build_auth_link(*, scopes: list[str], token_type: str = "user") -> dict[str, Any]:
    return build_pm_auth_link(find_openclaw_config_path, scopes=scopes, token_type=token_type)


def list_app_scope_presets() -> dict[str, dict[str, Any]]:
    return list_pm_app_scope_presets()


def build_permission_bundle(*, preset_names: list[str], scopes: list[str], token_type: str = "tenant") -> dict[str, Any]:
    return build_pm_permission_bundle(
        find_openclaw_config_path,
        preset_names=preset_names,
        scopes=scopes,
        token_type=token_type,
    )


def build_auth_bundle(
    *,
    include_group_open_reply: bool = True,
    include_attachment_oauth: bool = True,
    explicit_openclaw_config: str = "",
) -> dict[str, Any]:
    oauth_scopes = DEFAULT_ATTACHMENT_SCOPES if include_attachment_oauth else ()
    if explicit_openclaw_config:
        config_path = Path(explicit_openclaw_config).expanduser().resolve()

        def find_config() -> Path | None:
            return config_path
    else:
        find_config = find_openclaw_config_path
    return build_pm_auth_bundle(
        find_config,
        include_group_open_reply=include_group_open_reply,
        user_oauth_scopes=oauth_scopes,
        bot_auth_commands=DEFAULT_BOT_AUTH_COMMANDS,
    )


def request_user_oauth_link(*, scopes: list[str]) -> dict[str, Any]:
    return request_pm_user_oauth_link(find_openclaw_config_path, scopes=scopes)


def openclaw_config() -> dict[str, Any]:
    return load_openclaw_config(OPENCLAW_CONFIG_PATHS)


def feishu_credentials() -> dict[str, str]:
    return load_feishu_credentials(OPENCLAW_CONFIG_PATHS)


def load_openclaw_gateway_user_token(user_open_id: str) -> dict[str, Any]:
    resolved_open_id = str(user_open_id or "").strip()
    if not resolved_open_id:
        return {}

    app_id = str(feishu_credentials().get("app_id") or "").strip()
    if not app_id:
        return {}

    try:
        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                "openclaw-feishu-uat",
                "-a",
                f"{app_id}:{resolved_open_id}",
                "-w",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}

    raw = str(result.stdout or "").strip()
    if not raw:
        return {}

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}

    access_token = str(payload.get("accessToken") or "").strip()
    expires_at = int(payload.get("expiresAt") or 0)
    granted_scopes = {item for item in str(payload.get("scope") or "").split() if item}
    required_scopes = {"task:task:read", "task:task:write"}
    if not access_token or not required_scopes.issubset(granted_scopes):
        return {}
    if expires_at and expires_at <= ((unix_ts() * 1000) + 300000):
        return {}

    return {
        "status": "authorized",
        "token": access_token,
        "token_payload": payload,
        "open_id": resolved_open_id,
        "source": "openclaw_gateway_keychain",
    }


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any], str]:
    return auth_request_json(url, method=method, headers=headers, form=form, body=body, timeout=timeout)


def ensure_attachment_token(required_scopes: tuple[str, ...] = DEFAULT_ATTACHMENT_SCOPES) -> dict[str, Any]:
    return ensure_pm_attachment_token(
        state_dir=STATE_DIR,
        token_path=TOKEN_PATH,
        pending_auth_path=PENDING_AUTH_PATH,
        required_scopes=required_scopes,
        config_paths=OPENCLAW_CONFIG_PATHS,
    )


def task_backend_name() -> str:
    task_cfg = ACTIVE_CONFIG.get("task") if isinstance(ACTIVE_CONFIG.get("task"), dict) else {}
    return str(task_cfg.get("backend") or default_config()["task"]["backend"]).strip() or "feishu"


def doc_backend_name() -> str:
    doc_cfg = ACTIVE_CONFIG.get("doc") if isinstance(ACTIVE_CONFIG.get("doc"), dict) else {}
    return str(doc_cfg.get("backend") or default_config()["doc"]["backend"]).strip() or "feishu"


def gsd_bindings_path() -> Path:
    from pm_config import pm_file

    return pm_file("gsd-task-bindings.json")


def run_bridge(
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
    return invoke_bridge(
        _bridge_script_candidates(),
        tool,
        action,
        args,
        session_key=session_key,
        message_channel=message_channel,
        account_id=account_id,
        message_to=message_to,
        thread_id=thread_id,
    )


def details_of(payload: dict[str, Any]) -> dict[str, Any]:
    return bridge_details_of(payload)


def sanitize_feishu_markdown(text: str) -> str:
    raw = str(text or "")
    if not raw.strip():
        return ""

    def replace_link(match: re.Match[str]) -> str:
        label = str(match.group(1) or "").strip()
        target = str(match.group(2) or "").strip()
        lowered = target.lower()
        if lowered.startswith(("http://", "https://", "applink://", "#")):
            return match.group(0)
        if label:
            return f"`{label}`"
        return target

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, raw)


def build_run_label(root: Path, agent_id: str, task_id: str) -> str:
    from pm_dispatch import build_run_label as format_run_label

    return format_run_label(root, agent_id, task_id)


def _openclaw_state_dir() -> Path:
    state_dir_raw = _trim_env("OPENCLAW_STATE_DIR")
    return Path(state_dir_raw).expanduser().resolve() if state_dir_raw else STATE_DIR


def _stale_grace_ms() -> int:
    for env_name in ACP_LABEL_STALE_GRACE_SECONDS_ENV_VARS:
        raw = _trim_env(env_name)
        if not raw:
            continue
        try:
            seconds = max(0, int(raw))
        except ValueError:
            continue
        return seconds * 1000
    return ACP_LABEL_STALE_GRACE_SECONDS_DEFAULT * 1000


def _entry_session_file_exists(entry: dict[str, Any]) -> bool:
    session_file_raw = str(entry.get("sessionFile") or "").strip()
    if not session_file_raw:
        return False
    return Path(session_file_raw).expanduser().exists()


def _bridge_activity_anchor_ms(bridge_run: dict[str, Any], entry: dict[str, Any]) -> int:
    candidates = (
        bridge_run.get("lastEventAt"),
        bridge_run.get("discoveredAt"),
        entry.get("updatedAt"),
    )
    values: list[int] = []
    for candidate in candidates:
        try:
            value = int(candidate or 0)
        except (TypeError, ValueError):
            value = 0
        if value > 0:
            values.append(value)
    return max(values) if values else 0


def best_effort_release_stale_acp_label(agent_id: str, label: str) -> dict[str, Any]:
    resolved_agent_id = str(agent_id or "").strip()
    resolved_label = str(label or "").strip()
    if not resolved_agent_id or not resolved_label:
        return {"status": "invalid", "agent_id": resolved_agent_id, "label": resolved_label}

    state_dir = _openclaw_state_dir()
    sessions_path = state_dir / "agents" / resolved_agent_id / "sessions" / "sessions.json"
    sessions_payload = load_json_file(sessions_path)
    if not isinstance(sessions_payload, dict):
        return {
            "status": "missing_session_store",
            "agent_id": resolved_agent_id,
            "label": resolved_label,
            "sessions_path": str(sessions_path),
        }

    matches: list[tuple[str, dict[str, Any]]] = []
    for session_key, entry in sessions_payload.items():
        if not isinstance(entry, dict):
            continue
        entry_label = str(entry.get("label") or "").strip()
        if entry_label == resolved_label:
            matches.append((str(session_key).strip(), entry))
    if not matches:
        return {"status": "not_found", "agent_id": resolved_agent_id, "label": resolved_label}

    child_session_key, entry = sorted(matches, key=lambda item: int((item[1].get("updatedAt") or 0)), reverse=True)[0]
    acp_payload = entry.get("acp") if isinstance(entry.get("acp"), dict) else {}
    acp_state = str(acp_payload.get("state") or "").strip().lower()
    bridge_state_path = state_dir / "plugins" / "acp-progress-bridge" / "state.json"
    bridge_payload = load_json_file(bridge_state_path)
    bridge_runs = bridge_payload.get("runs") if isinstance(bridge_payload, dict) else {}
    bridge_run = bridge_runs.get(child_session_key) if isinstance(bridge_runs, dict) else {}
    if not isinstance(bridge_run, dict):
        bridge_run = {}

    bridge_done_at = int(bridge_run.get("doneAt") or 0)
    terminal_kind = str(bridge_run.get("terminalKind") or "").strip().lower()
    completion_handled = bool(bridge_run.get("completionHandled"))
    status_hint = str(bridge_run.get("statusHint") or "").strip()
    bridge_acp_state = str(bridge_run.get("acpState") or "").strip().lower()
    stream_exists = bool(bridge_run.get("streamExists"))
    session_file_exists = bool(bridge_run.get("sessionFileExists")) if bridge_run else _entry_session_file_exists(entry)
    activity_anchor_ms = _bridge_activity_anchor_ms(bridge_run, entry)
    stale_grace_ms = _stale_grace_ms()
    stale_for_ms = max(0, unix_ts() * 1000 - activity_anchor_ms) if activity_anchor_ms else 0
    missing_observability = (not stream_exists) or (not session_file_exists)

    stale_reason = ""
    replacement_state = ""
    if acp_state in {"idle", "error"}:
        stale_reason = f"session store already marked terminal: {acp_state}"
        replacement_state = acp_state
    elif bridge_acp_state in {"idle", "error"}:
        stale_reason = f"ACP bridge observed terminal session state: {bridge_acp_state}"
        replacement_state = bridge_acp_state
    elif bridge_done_at and completion_handled:
        stale_reason = "ACP bridge already marked the run complete"
        replacement_state = "error" if terminal_kind == "error" else "idle"
    elif bridge_done_at and "completion already detected" in status_hint:
        stale_reason = "ACP bridge observed terminal completion"
        replacement_state = "error" if terminal_kind == "error" else "idle"
    elif (
        acp_state in {"", "pending", "running"}
        and missing_observability
        and stale_for_ms >= stale_grace_ms
    ):
        stale_reason = (
            "ACP bridge lost transcript/stream observability "
            f"for {stale_for_ms // 1000}s: {status_hint or 'missing session transcript or stream'}"
        )
        replacement_state = "error"

    if not stale_reason:
        return {
            "status": "in_use",
            "agent_id": resolved_agent_id,
            "label": resolved_label,
            "child_session_key": child_session_key,
            "acp_state": acp_state,
            "bridge_done_at": bridge_done_at,
            "completion_handled": completion_handled,
            "status_hint": status_hint,
            "bridge_acp_state": bridge_acp_state,
            "stream_exists": stream_exists,
            "session_file_exists": session_file_exists,
            "stale_for_ms": stale_for_ms,
            "stale_grace_ms": stale_grace_ms,
        }

    next_entry = dict(entry)
    next_entry.pop("label", None)
    next_acp_payload = dict(acp_payload)
    if replacement_state:
        next_acp_payload["state"] = replacement_state
    if next_acp_payload:
        next_entry["acp"] = next_acp_payload
    next_entry["updatedAt"] = unix_ts() * 1000
    sessions_payload[child_session_key] = next_entry
    sessions_path.write_text(json.dumps(sessions_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "status": "released",
        "agent_id": resolved_agent_id,
        "label": resolved_label,
        "child_session_key": child_session_key,
        "previous_acp_state": acp_state,
        "replacement_state": replacement_state,
        "reason": stale_reason,
        "sessions_path": str(sessions_path),
    }


def spawn_acp_session(
    *,
    agent_id: str,
    message: str,
    cwd: str,
    timeout_seconds: int = 900,
    thinking: str = "high",
    label: str = "",
    session_key: str = "main",
) -> dict[str, Any]:
    from pm_dispatch import spawn_acp_session as dispatch_acp_session

    return dispatch_acp_session(
        run_bridge,
        agent_id=agent_id,
        message=message,
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        thinking=thinking,
        label=label,
        session_key=session_key,
    )


def english_project_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return resolve_pm_english_project_name(project_name, english_name, agent_id)


def project_slug(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return build_pm_project_slug(project_name, english_name, agent_id)


def project_display_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return resolve_pm_project_display_name(project_name, english_name, agent_id)


def default_tasklist_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return build_pm_default_tasklist_name(project_name, english_name, agent_id)


def default_doc_folder_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    return build_pm_default_doc_folder_name(project_name, english_name, agent_id)


def resolve_openclaw_config_path(explicit: str = "") -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    found = find_openclaw_config_path()
    if not found:
        raise SystemExit("openclaw.json not found; provide --openclaw-config")
    return found.resolve()


def resolve_workspace_root(*, openclaw_config_path: Path, agent_id: str, explicit: str = "") -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    config = load_json_file(openclaw_config_path)
    return resolve_pm_default_workspace_root(config, agent_id, openclaw_config_path)


def build_workspace_profile(
    *,
    project_name: str,
    english_name: str,
    agent_id: str,
    channel: str,
    group_id: str,
    repo_root: Path,
    workspace_root: Path,
    tasklist_name: str,
    doc_folder_name: str,
    task_prefix: str,
    default_worker: str,
    reviewer_worker: str,
    task_backend_type: str = "feishu-task",
) -> dict[str, Any]:
    return build_pm_workspace_profile(
        project_name=project_name,
        english_name=english_name,
        agent_id=agent_id,
        channel=channel,
        group_id=group_id,
        repo_root=repo_root,
        workspace_root=workspace_root,
        tasklist_name=tasklist_name,
        doc_folder_name=doc_folder_name,
        task_prefix=task_prefix,
        default_worker=default_worker,
        reviewer_worker=reviewer_worker,
        task_backend_type=task_backend_type,
    )


def scaffold_workspace(*, output: Path, profile: dict[str, Any], force: bool = False, dry_run: bool = False) -> dict[str, Any]:
    return scaffold_pm_workspace(output=output, profile=profile, force=force, dry_run=dry_run)


def register_workspace(
    *,
    config_path: Path,
    agent_id: str,
    workspace_root: Path,
    group_id: str,
    channel: str,
    skills: list[str],
    allow_agents: list[str],
    model_primary: str = "",
    replace_binding: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    return register_pm_workspace(
        config_path=config_path,
        agent_id=agent_id,
        workspace_root=workspace_root,
        group_id=group_id,
        channel=channel,
        skills=skills,
        allow_agents=allow_agents,
        model_primary=model_primary,
        replace_binding=replace_binding,
        dry_run=dry_run,
    )


def register_main_digest_source(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    project_name: str,
    source_key: str,
    enabled: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    template_path = Path(__file__).resolve().parents[2] / "project-review" / "config" / "main_review_sources.json"
    return register_pm_main_digest_source(
        openclaw_config_path=openclaw_config_path,
        repo_root=repo_root,
        project_name=project_name,
        source_key=source_key,
        enabled=enabled,
        dry_run=dry_run,
        template_path=template_path,
    )


def register_nightly_review_job(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    pm_config_path: Path,
    project_name: str,
    agent_id: str = "",
    group_id: str = "",
    enabled: bool = True,
    dry_run: bool = False,
    cron_expr: str = "0 6 * * *",
    timezone_name: str = "Asia/Shanghai",
    since: str = "yesterday 00:00",
    until: str = "today 00:00",
    reviewer_model: str = "",
    auto_fix_mode: str = "long-file-and-docs",
    send_if_possible: bool = True,
    include_dirty: bool = True,
) -> dict[str, Any]:
    return register_pm_nightly_review_job(
        openclaw_config_path=openclaw_config_path,
        repo_root=repo_root,
        pm_config_path=pm_config_path,
        project_name=project_name,
        agent_id=agent_id,
        group_id=group_id,
        enabled=enabled,
        dry_run=dry_run,
        cron_expr=cron_expr,
        timezone_name=timezone_name,
        since=since,
        until=until,
        reviewer_model=reviewer_model,
        auto_fix_mode=auto_fix_mode,
        send_if_possible=send_if_possible,
        include_dirty=include_dirty,
    )
