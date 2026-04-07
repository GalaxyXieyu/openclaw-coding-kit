from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
STATE_DIR_ENV_VARS = ("PM_STATE_DIR", "OPENCLAW_PM_STATE_DIR")


def _first_env_path(env_vars: tuple[str, ...]) -> Path | None:
    for env_name in env_vars:
        raw = str(os.environ.get(env_name) or "").strip()
        if raw:
            return Path(raw).expanduser()
    return None


def default_state_dir() -> Path:
    explicit = _first_env_path(STATE_DIR_ENV_VARS)
    if explicit is not None:
        return explicit
    local_appdata = str(os.environ.get("LOCALAPPDATA") or "").strip()
    if local_appdata:
        return Path(local_appdata) / "OpenClawPMCoder" / "state"
    appdata = str(os.environ.get("APPDATA") or "").strip()
    if appdata:
        return Path(appdata) / "OpenClawPMCoder" / "state"
    xdg_state_home = str(os.environ.get("XDG_STATE_HOME") or "").strip()
    if xdg_state_home:
        return Path(xdg_state_home) / "openclaw-pm-coder-kit" / "state"
    return Path.home() / ".local" / "state" / "openclaw-pm-coder-kit" / "pm"


STATE_DIR = default_state_dir()


def now_text() -> str:
    return datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S %Z")


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def unix_ts() -> int:
    return int(datetime.now(TZ).timestamp())


def ensure_state_dir(path: Path = STATE_DIR) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def save_json_file(path: Path, payload: dict[str, Any], *, state_dir: Path = STATE_DIR) -> None:
    ensure_state_dir(state_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def write_repo_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
