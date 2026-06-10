from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
REPO_TEMPLATE_ROOT = WORKSPACE_ROOT / "skills" / "pm" / "templates" / "repo"
REPO_AGENTS_TEMPLATE_NAME = "AGENTS.managed.md.tpl"
TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
SLUG_RE = re.compile(r"[^a-z0-9]+")
REPO_AGENTS_MANAGED_START = "<!-- PM_SHARED_CONTRACT:START -->"
REPO_AGENTS_MANAGED_END = "<!-- PM_SHARED_CONTRACT:END -->"


def repo_template_root() -> Path:
    return REPO_TEMPLATE_ROOT


def _is_ascii(text: str) -> bool:
    try:
        text.encode("ascii")
    except UnicodeEncodeError:
        return False
    return True


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _slugify(text: str) -> str:
    normalized = _normalize_spaces(text).lower().replace("&", " and ")
    slug = SLUG_RE.sub("-", normalized).strip("-")
    return slug


def english_project_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    candidate = _normalize_spaces(english_name) or _normalize_spaces(agent_id.replace("-", " ")) or _normalize_spaces(project_name)
    if not candidate:
        raise SystemExit("project name is required")
    if not _is_ascii(candidate):
        raise SystemExit("english name is required when project name contains non-ASCII characters")
    return candidate


def project_slug(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    slug = _slugify(agent_id or english_name or project_name)
    if not slug:
        raise SystemExit("failed to derive an ASCII project slug; provide --agent-id or --english-name")
    return slug


def project_display_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    source_name = _normalize_spaces(project_name)
    english = english_project_name(project_name, english_name, agent_id)
    if source_name and source_name != english:
        return source_name
    return english


def _display_with_slug(display_name: str, slug: str) -> str:
    display = _normalize_spaces(display_name)
    if not display:
        return slug
    if _slugify(display) == slug:
        return display
    return f"{display} [{slug}]"


def default_tasklist_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    display = project_display_name(project_name, english_name, agent_id)
    return display


def default_doc_folder_name(project_name: str, english_name: str = "", agent_id: str = "") -> str:
    display = project_display_name(project_name, english_name, agent_id)
    return display


def load_json_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid json object: {path}")
    return payload


def write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_template(text: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return values.get(key, match.group(0))

    return TOKEN_RE.sub(replace, text)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _shared_repo_agents_contract(
    *,
    pm_config_path: str,
    repo_root: Path,
    tasklist_name: str,
    doc_folder_name: str,
    default_worker: str,
    preferred_ui_worker: str,
) -> str:
    template_path = repo_template_root() / REPO_AGENTS_TEMPLATE_NAME
    if not template_path.exists():
        raise SystemExit(f"repo AGENTS template not found: {template_path}")
    return render_template(
        template_path.read_text(encoding="utf-8"),
        {
            "pm_config_path": pm_config_path,
            "repo_root": str(repo_root),
            "tasklist_name": tasklist_name,
            "doc_folder_name": doc_folder_name,
            "default_worker": default_worker,
            "preferred_ui_worker": preferred_ui_worker,
        },
    ).strip()


def _merge_repo_agents(existing: str, managed_block: str) -> str:
    text = existing.strip()
    if not text:
        return "# AGENTS.md\n\n" + managed_block + "\n"
    pattern = re.compile(
        rf"{re.escape(REPO_AGENTS_MANAGED_START)}.*?{re.escape(REPO_AGENTS_MANAGED_END)}",
        re.DOTALL,
    )
    if pattern.search(text):
        merged = pattern.sub(managed_block, text)
    else:
        merged = text + "\n\n" + managed_block
    return merged.rstrip() + "\n"


def sync_repo_agents_contract(
    *,
    repo_root: Path,
    pm_config_path: str,
    tasklist_name: str,
    doc_folder_name: str,
    default_worker: str,
    preferred_ui_worker: str,
) -> Path:
    target = repo_root / "AGENTS.md"
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    managed_block = _shared_repo_agents_contract(
        pm_config_path=pm_config_path,
        repo_root=repo_root,
        tasklist_name=tasklist_name,
        doc_folder_name=doc_folder_name,
        default_worker=default_worker,
        preferred_ui_worker=preferred_ui_worker,
    )
    merged = _merge_repo_agents(existing, managed_block)
    _write_text(target, merged)
    return target
