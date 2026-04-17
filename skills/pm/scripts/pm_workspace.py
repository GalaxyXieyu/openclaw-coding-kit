from __future__ import annotations

import copy
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DEVTEAM_TEMPLATES = WORKSPACE_ROOT / "incubator" / "devteam" / "templates"
REPO_WORKSPACE_TEMPLATES = WORKSPACE_ROOT / "skills" / "pm" / "templates" / "workspace"
WORKSPACE_ROOT_ENV_VARS = ("PM_WORKSPACE_ROOT", "OPENCLAW_WORKSPACE_ROOT")
WORKSPACE_TEMPLATE_ENV_VARS = ("PM_WORKSPACE_TEMPLATE_ROOT", "OPENCLAW_PM_TEMPLATE_ROOT")
TOKEN_RE = re.compile(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}")
SLUG_RE = re.compile(r"[^a-z0-9]+")
DEFAULT_SKILLS = ("pm", "coder", "code-review")
DEFAULT_ALLOW_AGENTS = ("codex", "gemini", "writer")


def _first_env_path(env_vars: tuple[str, ...]) -> Path | None:
    for env_name in env_vars:
        raw = str(os.environ.get(env_name) or "").strip()
        if raw:
            return Path(raw).expanduser()
    return None


def workspace_template_root() -> Path:
    explicit = _first_env_path(WORKSPACE_TEMPLATE_ENV_VARS)
    if explicit is not None:
        return explicit
    if REPO_WORKSPACE_TEMPLATES.exists():
        return REPO_WORKSPACE_TEMPLATES
    return DEVTEAM_TEMPLATES


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


def default_workspace_root(openclaw_config: dict[str, Any], agent_id: str, config_path: Path) -> Path:
    agents = openclaw_config.get("agents") if isinstance(openclaw_config.get("agents"), dict) else {}
    defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
    env_root = _first_env_path(WORKSPACE_ROOT_ENV_VARS)
    if env_root is not None:
        base = env_root.expanduser().resolve()
    else:
        configured = str(defaults.get("workspace") or "").strip()
        base = Path(configured or config_path.parent / "workspace").expanduser().resolve()
    return base / "workspaces" / agent_id


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
    source_name = _normalize_spaces(project_name)
    english = _normalize_spaces(english_name)
    profile = {
        "projectId": agent_id,
        "projectName": english,
        "channel": channel,
        "groupId": group_id,
        "frontAgentId": agent_id,
        "workspaceRoot": str(workspace_root),
        "repoRoot": str(repo_root),
        "docFolderName": doc_folder_name,
        "taskBackend": {
            "type": task_backend_type,
            "tasklistName": tasklist_name,
            "configPath": str(repo_root / "pm.json"),
        },
        "workers": {
            "default": default_worker,
            "reviewer": reviewer_worker,
        },
        "taskPrefix": task_prefix,
    }
    if source_name and source_name != english:
        profile["sourceProjectName"] = source_name
    return profile


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


def _memory_markdown(
    *,
    english_name: str,
    source_name: str,
    group_id: str,
    repo_root: Path,
    tasklist_name: str,
    doc_folder_name: str,
) -> str:
    lines = [
        "# memory.md",
        "",
        f"- project: `{english_name}`",
        f"- group id: `{group_id}`",
        f"- repo root: `{repo_root}`",
        f"- tasklist: `{tasklist_name}`",
        f"- doc folder: `{doc_folder_name}`",
    ]
    if source_name and source_name != english_name:
        lines.insert(3, f"- source project name: `{source_name}`")
    return "\n".join(lines) + "\n"


def _heartbeat_markdown(*, english_name: str, group_id: str, repo_root: Path) -> str:
    return "\n".join(
        [
            "# HEARTBEAT.md",
            "",
            f"- project: `{english_name}`",
            f"- group: `{group_id}`",
            f"- first read: `AGENTS.md`, `{repo_root / 'pm.json'}`, `memory.md`",
            "- when reporting progress, ground it in the real repo and current task context",
            "",
        ]
    )


def _bootstrap_markdown(*, english_name: str, repo_root: Path) -> str:
    return "\n".join(
        [
            "# BOOTSTRAP.md",
            "",
            f"1. Read `AGENTS.md` for the `{english_name}` front-agent contract.",
            f"2. Read `{repo_root / 'pm.json'}` to confirm repo root, tasklist, and doc folder.",
            "3. Read `memory.md` for persisted project identity.",
            "4. If the project is new, run `pm init` from the real repo after verifying Feishu access.",
            "",
        ]
    )


def _workspace_openclaw_config(*, english_name: str, repo_root: Path) -> dict[str, Any]:
    return {
        "heartbeat": {
            "prompt": f"Return to {english_name}: read {repo_root / 'pm.json'} first, then confirm repo path, tasklist, and current task context."
        }
    }


def scaffold_workspace(
    *,
    output: Path,
    profile: dict[str, Any],
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    workspace_exists = output.exists()
    workspace_non_empty = False
    if workspace_exists:
        try:
            workspace_non_empty = any(output.iterdir())
        except OSError:
            workspace_non_empty = False
    if output.exists() and force:
        if not dry_run:
            shutil.rmtree(output)
    elif workspace_exists and workspace_non_empty and not dry_run:
        raise SystemExit(f"workspace already exists and is not empty: {output}")

    task_backend = profile["taskBackend"]
    workers = profile["workers"]
    english_name = str(profile["projectName"])
    source_name = str(profile.get("sourceProjectName") or "")
    group_id = str(profile["groupId"])
    repo_root = Path(str(profile["repoRoot"])).expanduser().resolve()
    tasklist_name = str(task_backend.get("tasklistName") or english_name)
    doc_folder_name = str(profile.get("docFolderName") or english_name)

    values = {
        "project_id": str(profile["projectId"]),
        "project_name": english_name,
        "channel": str(profile["channel"]),
        "group_id": group_id,
        "front_agent_id": str(profile["frontAgentId"]),
        "repo_root": str(repo_root),
        "task_backend_type": str(task_backend["type"]),
        "pm_config_path": str(task_backend.get("configPath") or repo_root / "pm.json"),
        "tasklist_name": tasklist_name,
        "doc_folder_name": doc_folder_name,
        "default_worker": str(workers.get("default") or "codex"),
        "reviewer_worker": str(workers.get("reviewer") or "reviewer"),
    }

    template_map = {
        "AGENTS.md.tpl": output / "AGENTS.md",
        "IDENTITY.md.tpl": output / "IDENTITY.md",
        "TOOLS.md.tpl": output / "TOOLS.md",
        "WORKFLOW_AUTO.md.tpl": output / "WORKFLOW_AUTO.md",
    }
    template_root = workspace_template_root()

    generated_files: list[str] = []
    if dry_run:
        preview_files = list(template_map.values()) + [
            output / "config/project-profile.json",
            output / "subagents" / values["reviewer_worker"] / "AGENTS.md",
            output / "subagents" / values["reviewer_worker"] / "IDENTITY.md",
            output / "memory.md",
            output / "HEARTBEAT.md",
            output / "BOOTSTRAP.md",
            output / "openclaw.json",
        ]
        return {
            "workspace_root": str(output),
            "workspace_exists": workspace_exists,
            "workspace_non_empty": workspace_non_empty,
            "would_replace_existing": bool(force and workspace_exists),
            "template_root": str(template_root),
            "template_root_exists": template_root.exists(),
            "generated_files": sorted(str(path) for path in preview_files),
        }

    missing_templates = [name for name in template_map if not (template_root / name).exists()]
    if missing_templates:
        raise SystemExit(
            "workspace templates not found; set PM_WORKSPACE_TEMPLATE_ROOT, restore repo-local skills/pm/templates/workspace, "
            "or restore incubator/devteam/templates. "
            f"template_root={template_root}; missing={', '.join(missing_templates)}"
        )

    for template_name, target in template_map.items():
        source = template_root / template_name
        content = render_template(source.read_text(encoding="utf-8"), values)
        _write_text(target, content)
        generated_files.append(str(target))

    _write_text(output / "config/project-profile.json", json.dumps(profile, ensure_ascii=False, indent=2) + "\n")
    generated_files.append(str(output / "config/project-profile.json"))

    reviewer_worker = values["reviewer_worker"]
    reviewer_dir = output / "subagents" / reviewer_worker
    _write_text(
        reviewer_dir / "AGENTS.md",
        "# AGENTS.md\n\n"
        f"You are the reviewer worker for `{english_name}`.\n"
        "Review code, tests, and evidence only; do not act as the front agent.\n",
    )
    _write_text(
        reviewer_dir / "IDENTITY.md",
        "# IDENTITY.md\n\n"
        f"Reviewer worker for `{english_name}`.\n"
        f"Default repo root: `{repo_root}`.\n",
    )
    generated_files.extend(
        [
            str(reviewer_dir / "AGENTS.md"),
            str(reviewer_dir / "IDENTITY.md"),
        ]
    )

    _write_text(
        output / "memory.md",
        _memory_markdown(
            english_name=english_name,
            source_name=source_name,
            group_id=group_id,
            repo_root=repo_root,
            tasklist_name=tasklist_name,
            doc_folder_name=doc_folder_name,
        ),
    )
    _write_text(output / "HEARTBEAT.md", _heartbeat_markdown(english_name=english_name, group_id=group_id, repo_root=repo_root))
    _write_text(output / "BOOTSTRAP.md", _bootstrap_markdown(english_name=english_name, repo_root=repo_root))
    write_json_file(output / "openclaw.json", _workspace_openclaw_config(english_name=english_name, repo_root=repo_root))
    generated_files.extend(
        [
            str(output / "memory.md"),
            str(output / "HEARTBEAT.md"),
            str(output / "BOOTSTRAP.md"),
            str(output / "openclaw.json"),
        ]
    )

    for path in [output / "memory", output / "skills", output / "outbound", output / ".openclaw"]:
        _ensure_dir(path)

    return {
        "workspace_root": str(output),
        "generated_files": sorted(generated_files),
    }


def _copy_model(openclaw_config: dict[str, Any], model_primary: str = "") -> dict[str, Any] | str:
    if model_primary.strip():
        return {"primary": model_primary.strip()}
    agents = openclaw_config.get("agents") if isinstance(openclaw_config.get("agents"), dict) else {}
    defaults = agents.get("defaults") if isinstance(agents.get("defaults"), dict) else {}
    default_model = defaults.get("model")
    if isinstance(default_model, dict):
        return copy.deepcopy(default_model)
    if isinstance(default_model, str) and default_model.strip():
        return default_model.strip()
    for item in agents.get("list") or []:
        if not isinstance(item, dict):
            continue
        if str(item.get("id") or "").strip() in {"main", "writer", "codex"}:
            model = item.get("model")
            if isinstance(model, dict):
                return copy.deepcopy(model)
            if isinstance(model, str) and model.strip():
                return model.strip()
    return {"primary": "yuyu/gpt-5.4"}


def _dedupe(items: list[str], defaults: tuple[str, ...]) -> list[str]:
    raw = items or list(defaults)
    seen: set[str] = set()
    ordered: list[str] = []
    for item in raw:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


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
    payload = load_json_file(config_path)
    agents = payload.setdefault("agents", {})
    if not isinstance(agents, dict):
        raise SystemExit("openclaw config has invalid agents section")
    agent_list = agents.setdefault("list", [])
    if not isinstance(agent_list, list):
        raise SystemExit("openclaw config has invalid agents.list section")

    bindings = payload.setdefault("bindings", [])
    if not isinstance(bindings, list):
        raise SystemExit("openclaw config has invalid bindings section")

    existing_agent: dict[str, Any] | None = None
    for item in agent_list:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == agent_id:
            existing_agent = item
            break

    existing_binding: dict[str, Any] | None = None
    conflicting_binding: dict[str, Any] | None = None
    for item in bindings:
        if not isinstance(item, dict):
            continue
        match = item.get("match") if isinstance(item.get("match"), dict) else {}
        peer = match.get("peer") if isinstance(match.get("peer"), dict) else {}
        same_channel = str(match.get("channel") or "").strip() == channel
        same_group = str(peer.get("kind") or "").strip() == "group" and str(peer.get("id") or "").strip() == group_id
        if not same_channel or not same_group:
            continue
        if str(item.get("agentId") or "").strip() == agent_id:
            existing_binding = item
        else:
            conflicting_binding = item
        break

    if conflicting_binding and not replace_binding:
        raise SystemExit(
            f"group binding already exists for {channel}:{group_id} -> {conflicting_binding.get('agentId')}; use --replace-binding to override"
        )

    agent_entry = {
        "id": agent_id,
        "name": agent_id,
        "workspace": str(workspace_root),
        "model": _copy_model(payload, model_primary=model_primary),
        "skills": _dedupe(skills, DEFAULT_SKILLS),
        "subagents": {
            "allowAgents": _dedupe(allow_agents, DEFAULT_ALLOW_AGENTS),
        },
    }

    if existing_agent:
        existing_agent.update(agent_entry)
    else:
        agent_list.append(agent_entry)

    binding_entry = {
        "agentId": agent_id,
        "match": {
            "channel": channel,
            "peer": {
                "kind": "group",
                "id": group_id,
            },
        },
    }
    if conflicting_binding and replace_binding:
        conflicting_binding.clear()
        conflicting_binding.update(binding_entry)
    elif existing_binding:
        existing_binding.clear()
        existing_binding.update(binding_entry)
    else:
        bindings.append(binding_entry)

    if not dry_run:
        write_json_file(config_path, payload)

    return {
        "config_path": str(config_path),
        "agent_entry": agent_entry,
        "binding_entry": binding_entry,
        "agent_action": "updated" if existing_agent else "created",
        "binding_action": "replaced" if conflicting_binding and replace_binding else ("updated" if existing_binding else "created"),
    }
