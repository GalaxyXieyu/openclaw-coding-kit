from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATHS = (
    Path.cwd() / "pm.json",
    Path(__file__).with_name("pm.json"),
)
PM_DIR_NAME = ".pm"
ACTIVE_CONFIG: dict[str, Any] = {}


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for item in paths:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _openclaw_config_candidates() -> tuple[Path, ...]:
    home = Path.home()
    candidates: list[Path] = [Path.cwd() / "openclaw.json"]
    openclaw_home = str(os.environ.get("OPENCLAW_HOME") or "").strip()
    if openclaw_home:
        candidates.append(Path(openclaw_home).expanduser() / "openclaw.json")
    xdg_config_home = str(os.environ.get("XDG_CONFIG_HOME") or "").strip()
    if xdg_config_home:
        candidates.extend(
            [
                Path(xdg_config_home) / "openclaw" / "openclaw.json",
                Path(xdg_config_home) / "OpenClaw" / "openclaw.json",
            ]
        )
    for env_name in ("APPDATA", "LOCALAPPDATA"):
        base = str(os.environ.get(env_name) or "").strip()
        if not base:
            continue
        candidates.extend(
            [
                Path(base) / "openclaw" / "openclaw.json",
                Path(base) / "OpenClaw" / "openclaw.json",
            ]
        )
    candidates.extend(
        [
            home / ".config" / "openclaw" / "openclaw.json",
            home / ".config" / "OpenClaw" / "openclaw.json",
            home / ".openclaw" / "openclaw.json",
        ]
    )
    return tuple(_dedupe_paths(candidates))


OPENCLAW_CONFIG_PATHS = _openclaw_config_candidates()


def _workspace_profile_candidates(start: Path) -> list[Path]:
    candidates: list[Path] = []
    for parent in [start, *start.parents]:
        candidates.append(parent / "config" / "project-profile.json")
    return _dedupe_paths(candidates)


def _repo_config_from_workspace_profile(profile_path: Path) -> Path | None:
    if not profile_path.exists():
        return None
    try:
        payload = json.loads(profile_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    repo_root = str(payload.get("repoRoot") or "").strip()
    if not repo_root:
        return None
    return Path(repo_root).expanduser().resolve() / "pm.json"


def default_config() -> dict[str, Any]:
    return {
        "project": {
            "name": "未命名项目",
        },
        "repo_root": str(Path.cwd()),
        "task": {
            "backend": "feishu",
            "tasklist_name": "选育溯源档案",
            "prefix": "T",
            "kind": "task",
        },
        "doc": {
            "backend": "feishu",
            "folder_name": "项目文档",
            "project_title": "PROJECT",
            "requirements_title": "REQUIREMENTS",
            "roadmap_title": "ROADMAP",
            "state_title": "STATE",
        },
        "coder": {
            "backend": "acp",
            "agent_id": "codex",
            "timeout": 900,
            "thinking": "high",
            "session_key": "main",
        },
        "tasklist_name": "选育溯源档案",
        "task_prefix": "T",
        "kind": "task",
        "description_requirements": [
            "以 task/doc 为主，不再依赖本地 task/context/state 文件。",
            "进度默认写评论，验收证据优先回填附件或评论。",
        ],
    }


def resolve_config_path(path_value: str) -> Path:
    if path_value:
        return Path(path_value).expanduser()
    env_path = os.environ.get("FEISHU_TASKFLOW_CONFIG") or os.environ.get("OPENCLAW_TASKFLOW_CONFIG") or ""
    if env_path:
        return Path(env_path).expanduser()

    cwd = Path.cwd().expanduser().resolve()
    discovered_candidates: list[Path] = []
    for profile_path in _workspace_profile_candidates(cwd):
        repo_config = _repo_config_from_workspace_profile(profile_path)
        if repo_config is not None:
            discovered_candidates.append(repo_config)
    for parent in [cwd, *cwd.parents]:
        discovered_candidates.append(parent / "pm.json")

    all_candidates = _dedupe_paths(discovered_candidates + [candidate.expanduser() for candidate in DEFAULT_CONFIG_PATHS])
    for candidate in all_candidates:
        expanded = candidate.expanduser()
        if expanded.exists():
            return expanded
    return all_candidates[0] if all_candidates else DEFAULT_CONFIG_PATHS[0].expanduser()


def load_config(path_value: str) -> dict[str, Any]:
    path = resolve_config_path(path_value)
    config = default_config()
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise SystemExit(f"invalid config payload: {path}")
        config.update(payload)
    config["_config_path"] = str(path)
    return config


def project_name() -> str:
    project = ACTIVE_CONFIG.get("project")
    if isinstance(project, dict):
        name = str(project.get("name") or "").strip()
        if name:
            return name
    return str(ACTIVE_CONFIG.get("project_name") or "").strip() or "未命名项目"


def project_root_path(explicit: str = "") -> Path:
    raw = str(explicit or ACTIVE_CONFIG.get("repo_root") or default_config()["repo_root"]).strip()
    return Path(raw).expanduser().resolve()


def pm_dir_path(explicit_repo_root: str = "") -> Path:
    return project_root_path(explicit_repo_root) / PM_DIR_NAME


def ensure_pm_dir(explicit_repo_root: str = "") -> Path:
    path = pm_dir_path(explicit_repo_root)
    path.mkdir(parents=True, exist_ok=True)
    return path


def pm_file(name: str, explicit_repo_root: str = "") -> Path:
    return ensure_pm_dir(explicit_repo_root) / name


def find_openclaw_config_path() -> Path | None:
    candidates: list[Path] = []
    root = project_root_path() if "repo_root" in ACTIVE_CONFIG else Path.cwd()
    for parent in [root, *root.parents]:
        candidates.append(parent / "openclaw.json")
        candidates.append(parent / ".openclaw" / "openclaw.json")
    candidates.extend(OPENCLAW_CONFIG_PATHS)
    seen: set[str] = set()
    for candidate in candidates:
        expanded = candidate.expanduser()
        key = str(expanded)
        if key in seen:
            continue
        seen.add(key)
        if expanded.exists():
            return expanded
    return None


def task_prefix() -> str:
    task = ACTIVE_CONFIG.get("task")
    if isinstance(task, dict):
        raw = str(task.get("prefix") or "").strip().upper()
        if raw:
            return raw
    return str(ACTIVE_CONFIG.get("task_prefix") or default_config()["task_prefix"]).strip().upper()


def tasklist_name() -> str:
    task = ACTIVE_CONFIG.get("task")
    if isinstance(task, dict):
        raw = str(task.get("tasklist_name") or "").strip()
        if raw:
            return raw
    return str(ACTIVE_CONFIG.get("tasklist_name") or "").strip() or default_config()["tasklist_name"]


def task_kind() -> str:
    task = ACTIVE_CONFIG.get("task")
    if isinstance(task, dict):
        raw = str(task.get("kind") or "").strip()
        if raw:
            return raw
    return str(ACTIVE_CONFIG.get("kind") or "").strip() or str(default_config()["kind"]).strip()


def repo_root() -> str:
    return str(ACTIVE_CONFIG.get("repo_root") or "").strip() or default_config()["repo_root"]


def doc_config() -> dict[str, Any]:
    raw = ACTIVE_CONFIG.get("doc")
    return raw if isinstance(raw, dict) else {}


def doc_folder_name() -> str:
    return str(doc_config().get("folder_name") or default_config()["doc"]["folder_name"]).strip()


def doc_titles() -> dict[str, str]:
    cfg = doc_config()
    defaults = default_config()["doc"]
    return {
        "project": str(cfg.get("project_title") or defaults["project_title"]).strip() or "PROJECT",
        "requirements": str(cfg.get("requirements_title") or defaults["requirements_title"]).strip() or "REQUIREMENTS",
        "roadmap": str(cfg.get("roadmap_title") or defaults["roadmap_title"]).strip() or "ROADMAP",
        "state": str(cfg.get("state_title") or defaults["state_title"]).strip() or "STATE",
    }


def coder_config() -> dict[str, Any]:
    raw = ACTIVE_CONFIG.get("coder")
    if isinstance(raw, dict):
        return raw
    return default_config()["coder"]
