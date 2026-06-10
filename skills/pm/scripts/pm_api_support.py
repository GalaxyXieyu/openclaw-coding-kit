from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from pm_auth import ensure_attachment_token as ensure_pm_attachment_token
from pm_auth import feishu_credentials as load_feishu_credentials
from pm_auth import request_json as auth_request_json
from pm_config import ACTIVE_CONFIG
from pm_config import OPENCLAW_CONFIG_PATHS
from pm_config import default_config
from pm_io import STATE_DIR
from pm_project_review import register_main_digest_source as register_pm_main_digest_source
from pm_project_review import register_nightly_review_job as register_pm_nightly_review_job
from pm_project_review import unregister_main_digest_source as unregister_pm_main_digest_source
from pm_project_review import unregister_nightly_review_job as unregister_pm_nightly_review_job
from pm_workspace import default_doc_folder_name as build_pm_default_doc_folder_name
from pm_workspace import default_tasklist_name as build_pm_default_tasklist_name
from pm_workspace import english_project_name as resolve_pm_english_project_name
from pm_workspace import project_display_name as resolve_pm_project_display_name
from pm_workspace import project_slug as build_pm_project_slug
from pm_workspace import sync_repo_agents_contract as sync_pm_repo_agents_contract

SKILL_ROOT = Path(__file__).resolve().parent.parent
TOKEN_PATH = STATE_DIR / "attachment-oauth-token.json"
PENDING_AUTH_PATH = STATE_DIR / "attachment-oauth-pending.json"
DEFAULT_ATTACHMENT_SCOPES = (
    "task:task:read",
    "task:attachment:read",
    "task:attachment:write",
    "offline_access",
)
def lark_auth_hint(*, scopes: list[str] | tuple[str, ...] = (), token_type: str = "user") -> dict[str, Any]:
    return {
        "status": "managed_by_lark_cli",
        "provider": "lark-cli",
        "token_type": token_type,
        "scopes": list(scopes or []),
        "commands": {
            "status": ["pm", "lark", "status"],
            "doctor": ["pm", "lark", "doctor"],
            "login": ["pm", "lark", "login", "--exec"],
        },
        "message": "Official lark-cli owns Feishu auth; PM no longer generates OpenClaw auth links or reads Gateway tokens.",
    }


def build_auth_link(*, scopes: list[str], token_type: str = "user") -> dict[str, Any]:
    return lark_auth_hint(scopes=scopes, token_type=token_type)


def request_user_oauth_link(*, scopes: list[str]) -> dict[str, Any]:
    return lark_auth_hint(scopes=scopes, token_type="user")


def feishu_credentials() -> dict[str, str]:
    return load_feishu_credentials(OPENCLAW_CONFIG_PATHS)


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


def feishu_provider_name() -> str:
    task_cfg = ACTIVE_CONFIG.get("task") if isinstance(ACTIVE_CONFIG.get("task"), dict) else {}
    doc_cfg = ACTIVE_CONFIG.get("doc") if isinstance(ACTIVE_CONFIG.get("doc"), dict) else {}
    if task_backend_name() != "feishu" and doc_backend_name() != "feishu":
        return "local"
    feishu_cfg = ACTIVE_CONFIG.get("feishu") if isinstance(ACTIVE_CONFIG.get("feishu"), dict) else {}
    provider = str(os.environ.get("PM_FEISHU_PROVIDER") or feishu_cfg.get("provider") or task_cfg.get("provider") or doc_cfg.get("provider") or "").strip()
    return provider or "lark-cli"


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
    provider = feishu_provider_name()
    if provider == "lark-cli":
        from pm_lark_cli import run_bridge_compatible

        return run_bridge_compatible(tool, action, args)
    if provider in {"openclaw", "gateway", "openclaw-gateway"}:
        raise SystemExit("OpenClaw/Gateway Feishu provider is disabled for PM; set provider to 'lark-cli' or use local backend")
    raise SystemExit(f"unsupported PM Feishu provider: {provider}; expected lark-cli or local backend")


def details_of(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("details"), dict):
        return payload["details"]
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("details"), dict):
        return result["details"]
    return {}


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


def sync_repo_agents_contract(
    *,
    repo_root: Path,
    pm_config_path: str,
    tasklist_name: str,
    doc_folder_name: str,
    default_worker: str,
    preferred_ui_worker: str = "gemini",
) -> Path:
    return sync_pm_repo_agents_contract(
        repo_root=repo_root,
        pm_config_path=pm_config_path,
        tasklist_name=tasklist_name,
        doc_folder_name=doc_folder_name,
        default_worker=default_worker,
        preferred_ui_worker=preferred_ui_worker,
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
    stagger_minutes: int = 0,
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
        stagger_minutes=stagger_minutes,
        timezone_name=timezone_name,
        since=since,
        until=until,
        reviewer_model=reviewer_model,
        auto_fix_mode=auto_fix_mode,
        send_if_possible=send_if_possible,
        include_dirty=include_dirty,
    )


def unregister_main_digest_source(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    source_key: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    return unregister_pm_main_digest_source(
        openclaw_config_path=openclaw_config_path,
        repo_root=repo_root,
        source_key=source_key,
        dry_run=dry_run,
    )


def unregister_nightly_review_job(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    project_name: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    return unregister_pm_nightly_review_job(
        openclaw_config_path=openclaw_config_path,
        repo_root=repo_root,
        project_name=project_name,
        dry_run=dry_run,
    )
