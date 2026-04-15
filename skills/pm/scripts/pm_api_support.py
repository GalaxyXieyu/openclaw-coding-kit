from __future__ import annotations

import json
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
    cron_expr: str = "30 0 * * *",
    timezone_name: str = "Asia/Shanghai",
    since: str = "24 hours ago",
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
        reviewer_model=reviewer_model,
        auto_fix_mode=auto_fix_mode,
        send_if_possible=send_if_possible,
        include_dirty=include_dirty,
    )
