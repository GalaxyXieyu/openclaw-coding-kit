from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_NIGHTLY_CRON = "0 6 * * *"
DEFAULT_NIGHTLY_TIMEZONE = "Asia/Shanghai"
DEFAULT_NIGHTLY_SINCE = "yesterday 00:00"
DEFAULT_NIGHTLY_UNTIL = "today 00:00"


def _apply_stagger_to_cron(expr: str, stagger_minutes: int) -> str:
    normalized = str(expr or DEFAULT_NIGHTLY_CRON).strip() or DEFAULT_NIGHTLY_CRON
    offset = int(stagger_minutes or 0)
    if offset <= 0:
        return normalized
    parts = normalized.split()
    if len(parts) != 5:
        return normalized
    try:
        minute = int(parts[0])
        hour = int(parts[1])
    except ValueError:
        return normalized
    total_minutes = (hour * 60) + minute + offset
    parts[0] = str(total_minutes % 60)
    parts[1] = str((total_minutes // 60) % 24)
    return " ".join(parts)


def _default_main_digest_config() -> dict[str, Any]:
    return {
        "main_target": {
            "alias": "main",
            "channel": "feishu",
            "chat_id": "",
            "chat_name": "",
        },
        "main_chat_id": "",
        "main_chat_name": "",
        "main_project_name": "全部项目",
        "default_since": "7 days ago",
        "sources": [],
    }


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return payload


def _seed_main_digest_config(template_path: Path | None = None) -> dict[str, Any]:
    payload = _default_main_digest_config()
    if template_path and template_path.exists():
        try:
            template = _load_json(template_path)
        except Exception:
            template = {}
        for key in ("main_target", "main_chat_id", "main_chat_name", "main_project_name", "default_since"):
            value = template.get(key)
            if value in (None, "", []):
                continue
            payload[key] = value
    return payload


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _load_cron_jobs(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "jobs": []}
    payload = _load_json(path)
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        payload["jobs"] = []
    payload.setdefault("version", 1)
    return payload


def _default_session_key(agent_id: str, group_id: str = "") -> str:
    normalized_agent = str(agent_id or "main").strip() or "main"
    normalized_group = str(group_id or "").strip()
    if normalized_group:
        return f"agent:{normalized_agent}:feishu:group:{normalized_group}"
    if normalized_agent == "main":
        return "agent:main:main"
    return f"agent:{normalized_agent}:main"


def _nightly_review_message(
    *,
    repo_root: Path,
    pm_config_path: Path,
    since: str,
    until: str,
    reviewer_model: str,
    auto_fix_mode: str,
    send_if_possible: bool,
    include_dirty: bool,
) -> str:
    review_script = repo_root / "skills" / "project-review" / "scripts" / "nightly_auto_review.py"
    command = [
        "python3",
        str(review_script),
        "--repo-root",
        str(repo_root),
        "--pm-config",
        str(pm_config_path),
        "--since",
        since,
    ]
    if str(until or "").strip():
        command.extend(["--until", until])
    command.extend([
        "--auto-fix-mode",
        auto_fix_mode,
        "--json",
    ])
    if reviewer_model:
        command.extend(["--reviewer-model", reviewer_model])
    if not send_if_possible:
        command.append("--no-send")
    if not include_dirty:
        command.append("--no-dirty")
    joined_command = " ".join(json.dumps(part, ensure_ascii=False) for part in command)
    return "\n".join(
        [
            f"Project review for repo {repo_root}.",
            "",
            f"Review window: previous calendar day (`{since}` → `{until}`).",
            "",
            "Run this exact command from the repo root:",
            joined_command,
            "",
            "Rules:",
            "- Keep the run scoped to this repo only.",
            "- Summarize the previous day's commits, changed files, docs updates, and delivery risks; do not summarize today's partial work.",
            "- If the project chat is not configured, still complete the local review and report `send_status=skipped`.",
            "- Reply with review_id, auto-fix result, and what docs descriptions were updated.",
        ]
    )


def resolve_main_review_registry_path(openclaw_config_path: Path) -> Path:
    runtime_dir = openclaw_config_path.expanduser().resolve().parent / "project-review"
    review_path = runtime_dir / "main_review_sources.json"
    legacy_path = runtime_dir / "main_digest_sources.json"
    if legacy_path.exists() and not review_path.exists():
        return legacy_path
    return review_path


def resolve_main_digest_registry_path(openclaw_config_path: Path) -> Path:
    return resolve_main_review_registry_path(openclaw_config_path)


def resolve_cron_jobs_path(openclaw_config_path: Path) -> Path:
    return openclaw_config_path.expanduser().resolve().parent / "cron" / "jobs.json"


def register_main_review_source(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    project_name: str,
    source_key: str,
    enabled: bool = True,
    dry_run: bool = False,
    template_path: Path | None = None,
) -> dict[str, Any]:
    config_path = resolve_main_review_registry_path(openclaw_config_path)
    existed = config_path.exists()
    payload = _load_json(config_path) if existed else _seed_main_digest_config(template_path)
    sources = payload.get("sources")
    if not isinstance(sources, list):
        sources = []
        payload["sources"] = sources

    normalized_repo_root = str(repo_root.expanduser().resolve())
    normalized_key = str(source_key or "").strip() or repo_root.name
    normalized_project_name = str(project_name or "").strip() or repo_root.name

    existing: dict[str, Any] | None = None
    for item in sources:
        if not isinstance(item, dict):
            continue
        item_repo_root = str(item.get("repo_root") or "").strip()
        item_key = str(item.get("key") or "").strip()
        if item_repo_root == normalized_repo_root or (normalized_key and item_key == normalized_key):
            existing = item
            break

    action = "created"
    if existing is None:
        entry = {
            "key": normalized_key,
            "project_name": normalized_project_name,
            "repo_root": normalized_repo_root,
            "enabled": bool(enabled),
        }
        sources.append(entry)
        existing = entry
    else:
        action = "updated"
        existing["key"] = str(existing.get("key") or normalized_key).strip() or normalized_key
        existing["project_name"] = normalized_project_name
        existing["repo_root"] = normalized_repo_root
        if "enabled" not in existing:
            existing["enabled"] = bool(enabled)

    main_target = payload.get("main_target") if isinstance(payload.get("main_target"), dict) else {}
    main_ready = bool(str(main_target.get("chat_id") or payload.get("main_chat_id") or "").strip())

    if not dry_run:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "dry_run" if dry_run else "ok",
        "action": action if existed else "bootstrapped",
        "config_path": str(config_path),
        "source": dict(existing),
        "source_count": len([item for item in sources if isinstance(item, dict)]),
        "main_ready": main_ready,
        "created_config": not existed,
    }


def register_main_digest_source(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    project_name: str,
    source_key: str,
    enabled: bool = True,
    dry_run: bool = False,
    template_path: Path | None = None,
) -> dict[str, Any]:
    return register_main_review_source(
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
    cron_expr: str = DEFAULT_NIGHTLY_CRON,
    stagger_minutes: int = 0,
    timezone_name: str = DEFAULT_NIGHTLY_TIMEZONE,
    since: str = DEFAULT_NIGHTLY_SINCE,
    until: str = DEFAULT_NIGHTLY_UNTIL,
    reviewer_model: str = "",
    auto_fix_mode: str = "long-file-and-docs",
    send_if_possible: bool = True,
    include_dirty: bool = True,
) -> dict[str, Any]:
    jobs_path = resolve_cron_jobs_path(openclaw_config_path)
    payload = _load_cron_jobs(jobs_path)
    jobs = payload.get("jobs")
    if not isinstance(jobs, list):
        jobs = []
        payload["jobs"] = jobs

    normalized_repo_root = str(repo_root.expanduser().resolve())
    normalized_pm_config = str(pm_config_path.expanduser().resolve())
    normalized_project_name = str(project_name or repo_root.name).strip() or repo_root.name
    normalized_agent_id = str(agent_id or "main").strip() or "main"
    normalized_group_id = str(group_id or "").strip()
    normalized_name = f"Project review · {normalized_project_name}"
    normalized_session_key = _default_session_key(normalized_agent_id, normalized_group_id)
    message = _nightly_review_message(
        repo_root=Path(normalized_repo_root),
        pm_config_path=Path(normalized_pm_config),
        since=since,
        until=until,
        reviewer_model=reviewer_model,
        auto_fix_mode=auto_fix_mode,
        send_if_possible=send_if_possible,
        include_dirty=include_dirty,
    )

    existing: dict[str, Any] | None = None
    for item in jobs:
        if not isinstance(item, dict):
            continue
        payload_item = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        payload_message = str(payload_item.get("message") or "").strip()
        if str(item.get("name") or "").strip() == normalized_name or normalized_repo_root in payload_message:
            existing = item
            break

    action = "created"
    created_at_ms = _now_ms()
    entry = copy.deepcopy(existing) if isinstance(existing, dict) else {}
    if existing is not None:
        action = "updated"
    entry.update(
        {
            "id": str(entry.get("id") or uuid.uuid4()),
            "agentId": normalized_agent_id,
            "sessionKey": normalized_session_key,
            "name": normalized_name,
            "enabled": bool(enabled),
            "createdAtMs": int(entry.get("createdAtMs") or created_at_ms),
            "updatedAtMs": created_at_ms,
            "schedule": {
                "kind": "cron",
                "expr": _apply_stagger_to_cron(cron_expr, stagger_minutes),
                "tz": str(timezone_name or DEFAULT_NIGHTLY_TIMEZONE).strip() or DEFAULT_NIGHTLY_TIMEZONE,
            },
            "sessionTarget": "isolated",
            "wakeMode": "now",
            "payload": {
                "kind": "agentTurn",
                "thinking": "medium",
                "timeoutSeconds": 3600,
                "message": message,
            },
        }
    )

    if existing is None:
        jobs.append(entry)

    if not dry_run:
        jobs_path.parent.mkdir(parents=True, exist_ok=True)
        jobs_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "dry_run" if dry_run else "ok",
        "action": action,
        "jobs_path": str(jobs_path),
        "job": entry,
        "job_count": len([item for item in jobs if isinstance(item, dict)]),
    }


def unregister_main_digest_source(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    source_key: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    config_path = resolve_main_review_registry_path(openclaw_config_path)
    if not config_path.exists():
        return {
            "status": "missing",
            "config_path": str(config_path),
            "removed": [],
            "source_count": 0,
        }

    payload = _load_json(config_path)
    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    normalized_repo_root = str(repo_root.expanduser().resolve())
    normalized_key = str(source_key or "").strip()

    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for item in sources:
        if not isinstance(item, dict):
            kept.append(item)
            continue
        item_repo_root = str(item.get("repo_root") or "").strip()
        item_key = str(item.get("key") or "").strip()
        if item_repo_root == normalized_repo_root or (normalized_key and item_key == normalized_key):
            removed.append(copy.deepcopy(item))
        else:
            kept.append(item)

    if removed and not dry_run:
        payload["sources"] = kept
        config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": ("dry_run" if dry_run else "deleted") if removed else "missing",
        "config_path": str(config_path),
        "removed": removed,
        "source_count": len([item for item in kept if isinstance(item, dict)]),
    }


def unregister_nightly_review_job(
    *,
    openclaw_config_path: Path,
    repo_root: Path,
    project_name: str = "",
    dry_run: bool = False,
) -> dict[str, Any]:
    jobs_path = resolve_cron_jobs_path(openclaw_config_path)
    if not jobs_path.exists():
        return {
            "status": "missing",
            "jobs_path": str(jobs_path),
            "removed": [],
            "job_count": 0,
        }

    payload = _load_cron_jobs(jobs_path)
    jobs = payload.get("jobs") if isinstance(payload.get("jobs"), list) else []
    normalized_repo_root = str(repo_root.expanduser().resolve())
    project_label = str(project_name or repo_root.name).strip() or repo_root.name
    normalized_name = f"Project review · {project_label}"
    legacy_name = f"Nightly {project_label} review"

    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for item in jobs:
        if not isinstance(item, dict):
            kept.append(item)
            continue
        payload_item = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        payload_message = str(payload_item.get("message") or "").strip()
        item_name = str(item.get("name") or "").strip()
        if item_name in {normalized_name, legacy_name} or normalized_repo_root in payload_message:
            removed.append(copy.deepcopy(item))
        else:
            kept.append(item)

    if removed and not dry_run:
        payload["jobs"] = kept
        jobs_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": ("dry_run" if dry_run else "deleted") if removed else "missing",
        "jobs_path": str(jobs_path),
        "removed": removed,
        "job_count": len([item for item in kept if isinstance(item, dict)]),
    }
