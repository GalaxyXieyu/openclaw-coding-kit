#!/usr/bin/env python3
"""Build and optionally send a main-group review across active projects."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from commit_window import collect_recent_commits
from review_runtime_paths import resolve_main_review_config_path, resolve_main_review_state_path
from review_delivery import send_review_card
from review_orchestrator import prepare_review

TASK_PREFIX_RE = re.compile(r"^\[[^\]]+\]\s*")
COMMIT_PREFIX_RE = re.compile(r"^(feat|fix|docs|doc|chore|refactor|build|ci|test|perf|style|merge|recover)(\([^)]+\))?:\s*", re.I)
SECTION_HEADER_RE = re.compile(r"^###\s+(.+?)\s*$")
CHECKBOX_RE = re.compile(r"^-\s*\[[ xX]\]\s*")


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _text(value: Any) -> str:
    return str(value or "").strip()


def _main_target(config: dict[str, Any]) -> dict[str, str]:
    target = config.get("main_target") if isinstance(config.get("main_target"), dict) else {}
    return {
        "alias": _text(target.get("alias")) or "main",
        "channel": _text(target.get("channel")) or "feishu",
        "chat_id": _text(target.get("chat_id")) or _text(config.get("main_chat_id")),
        "chat_name": _text(target.get("chat_name")) or _text(config.get("main_chat_name")),
    }


def _contains_zh(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in str(text or ""))


def _replace_many(text: str, pairs: list[tuple[str, str]]) -> str:
    result = str(text or "")
    for source, target in pairs:
        result = re.sub(source, target, result, flags=re.I)
    return result


def _trim_fragment(text: str, limit: int = 18) -> str:
    cleaned = _text(text).strip("，。；、:- ")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: max(1, limit - 1)] + "…"


def _clean_task_text(text: str) -> str:
    cleaned = TASK_PREFIX_RE.sub("", _text(text))
    lowered = cleaned.lower()
    if "interaction-board" in lowered:
        return "交互看板样例"
    cleaned = _replace_many(
        cleaned,
        [
            (r"主Agent", "主Agent"),
            (r"knowledge|wiki", "知识整理"),
            (r"interaction-board", "交互看板"),
            (r"build", "补"),
            (r"skill", "技能"),
            (r"sample", "样例"),
            (r"miniapp", "小程序"),
            (r"and", "和"),
        ],
    )
    cleaned = cleaned.replace("闭环", "收口")
    return _trim_fragment(cleaned, limit=16) or "待办整理"


def _extract_active_items(summary_markdown: str) -> list[str]:
    current_section = ""
    items: list[str] = []
    for raw_line in str(summary_markdown or "").splitlines():
        line = raw_line.rstrip()
        section_match = SECTION_HEADER_RE.match(line)
        if section_match:
            current_section = _text(section_match.group(1))
            continue
        if current_section != "Active":
            continue
        if not line.startswith("-"):
            if line.strip():
                break
            continue
        item = CHECKBOX_RE.sub("", line).strip()
        if item:
            items.append(item)
    return items


def _simplify_active_item(text: str) -> str:
    cleaned = _text(text)
    if "：" in cleaned:
        cleaned = cleaned.split("：", 1)[1]
    cleaned = _replace_many(
        cleaned,
        [
            (r".*Java.*附件.*", "Java附件接入"),
            (r".*问题.*调度.*", "问题识别和调度"),
            (r".*问题项.*输出.*", "问题输出整理"),
            (r".*根仓.*文档.*", "根仓文档整理"),
            (r".*模块边界.*", "模块边界说明"),
            (r".*路线图.*", "路线图建议"),
            (r".*主Agent.*主动节律.*", "主Agent主动节律"),
            (r".*知识.*wiki.*", "知识整理入口"),
            (r".*部署.*workflow.*", "部署流程同步"),
        ],
    )
    cleaned = cleaned.replace("闭环", "收口")
    return _trim_fragment(cleaned, limit=16) or "待办整理"


def _humanize_subject(subject: str) -> str:
    raw = COMMIT_PREFIX_RE.sub("", _text(subject))
    if not raw:
        return ""

    lowered = raw.lower()
    if "completion due sync" in lowered:
        return "PM完成时间同步"
    if "auth onboarding" in lowered or ("auth" in lowered and "feishu" in lowered):
        return "PM授权和飞书兼容"
    if "readme" in lowered and ("diagram" in lowered or "architecture" in lowered):
        return "README和结构图收口"
    if "story" in lowered or "showcase" in lowered or "assets" in lowered:
        return "项目说明和展示素材"
    if "submodule" in lowered and ("openclaw" in lowered or "xiaozhi" in lowered):
        return "子模块同步"
    if "deploy" in lowered or "workflow" in lowered or "snapshot" in lowered:
        return "部署流程同步"
    if "guiquan" in lowered and ("community" in lowered or "supply" in lowered):
        return "龟圈和补给体验"
    if "webhook" in lowered:
        return "回调接入"
    if "problem" in lowered and "迁移" in raw:
        return "问题迁移修复"
    if "主键" in raw and ("identity" in lowered or "迁移" in raw):
        return "主键兼容和迁移修复"
    if "migration" in lowered and "problem" in lowered:
        return "问题迁移修复"
    if "cache" in lowered or "injection" in lowered:
        return "缓存和注入优化"

    normalized = _replace_many(
        raw,
        [
            (r"robotsrun", "项目"),
            (r"readme", "README"),
            (r"pm", "PM"),
            (r"submodule", "子模块"),
            (r"deployment", "部署"),
            (r"deploy", "部署"),
            (r"workflow", "流程"),
            (r"story", "说明"),
            (r"showcase", "展示"),
            (r"assets", "素材"),
            (r"planning", "规划"),
            (r"guiquan", "龟圈"),
            (r"supply", "补给"),
            (r"community", "社区"),
            (r"miniapp", "小程序"),
            (r"webhook", "回调"),
            (r"problem", "问题"),
            (r"identity", "身份"),
            (r"migration", "迁移"),
            (r"script", "脚本"),
            (r"scripts", "脚本"),
            (r"sync", "同步"),
            (r"update", "更新"),
            (r"rewrite", "重写"),
            (r"improve", "优化"),
            (r"refine", "补齐"),
            (r"polish", "补齐"),
            (r"replace", "替换"),
            (r"remove", "清理"),
            (r"rename", "改名"),
            (r"align", "对齐"),
            (r"bump", "更新"),
            (r"and", "、"),
        ],
    )
    normalized = re.sub(r"[-_/]+", " ", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    return _trim_fragment(normalized, limit=16)


def _is_main_digest_review(review: dict[str, Any]) -> bool:
    if not isinstance(review, dict):
        return False

    source_payload = review.get("source_payload") if isinstance(review.get("source_payload"), dict) else {}
    bundle = review.get("bundle") if isinstance(review.get("bundle"), dict) else {}
    bundle_project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}

    names = {
        _text(review.get("project_name")),
        _text(source_payload.get("project_name")),
        _text(bundle_project.get("name")),
    }
    if "全部项目" in names:
        return True

    period_key = _text(source_payload.get("period_key")) or _text(review.get("period_key"))
    dedupe_key = _text(review.get("dedupe_key"))
    if period_key.startswith("main-weekly-") or "main-weekly-" in dedupe_key:
        return True

    return False


def _aggregate_review_projects(repo_root: Path, *, limit: int = 2) -> dict[str, str] | None:
    state_path = repo_root / ".pm" / "project-review-state.json"
    if not state_path.exists():
        return None
    try:
        state = _load_json(state_path)
    except Exception:
        return None
    reviews = state.get("reviews") if isinstance(state.get("reviews"), list) else []
    weekly = [
        item
        for item in reviews
        if isinstance(item, dict)
        and _text(item.get("trigger_kind")) == "weekly"
        and not _is_main_digest_review(item)
    ]
    if not weekly:
        return None
    latest = sorted(weekly, key=lambda item: _text(item.get("updated_at") or item.get("created_at")), reverse=True)[0]
    bundle = latest.get("bundle") if isinstance(latest.get("bundle"), dict) else {}
    projects = bundle.get("projects") if isinstance(bundle.get("projects"), list) else []
    if not projects:
        return None

    def join_field(key: str) -> str:
        values: list[str] = []
        for item in projects:
            value = _trim_fragment(_text((item or {}).get(key)), limit=12)
            if value and value not in values:
                values.append(value)
            if len(values) >= limit:
                break
        return "、".join(values)

    done = join_field("done")
    pending = join_field("pending")
    next_step = join_field("next_step")
    if not done or not pending or not next_step:
        return None
    return {"done": done, "pending": pending, "next_step": next_step}


def _load_current_context(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".pm" / "current-context.json"
    if not path.exists():
        return {}
    try:
        return _load_json(path)
    except Exception:
        return {}


def _load_project_scan(repo_root: Path) -> dict[str, Any]:
    path = repo_root / ".pm" / "project-scan.json"
    if not path.exists():
        return {}
    try:
        return _load_json(path)
    except Exception:
        return {}


def _derive_pending_next(repo_root: Path) -> tuple[str, str]:
    review_summary = _aggregate_review_projects(repo_root)
    if review_summary:
        return review_summary["pending"], review_summary["next_step"]

    current_context = _load_current_context(repo_root)
    open_tasks = current_context.get("open_tasks") if isinstance(current_context.get("open_tasks"), list) else []
    if open_tasks:
        first = _clean_task_text(_text(open_tasks[0].get("summary")))
        second = _clean_task_text(_text(open_tasks[1].get("summary"))) if len(open_tasks) > 1 else first
        return first or "待办整理", second or "补任务复盘"

    project_scan = _load_project_scan(repo_root)
    gsd = project_scan.get("gsd") if isinstance(project_scan.get("gsd"), dict) else {}
    summaries = gsd.get("summaries") if isinstance(gsd.get("summaries"), dict) else {}
    project_summary = _text(summaries.get("project"))
    active_items = _extract_active_items(project_summary)
    if active_items:
        first = _simplify_active_item(active_items[0])
        second = _simplify_active_item(active_items[1]) if len(active_items) > 1 else first
        if second == first:
            project_summary = _text(project_summary)
            if "问题" in project_summary and "调度" in project_summary:
                second = "问题识别和调度"
        return first or "待办整理", second or "补任务复盘"

    return "待办整理", "补任务复盘"


def _derive_done(repo_root: Path, commits: list[dict[str, str]]) -> str:
    review_summary = _aggregate_review_projects(repo_root)
    if review_summary:
        return review_summary["done"]

    topics: list[str] = []
    for item in commits[:3]:
        topic = _humanize_subject(_text(item.get("subject")))
        if topic and topic not in topics:
            topics.append(topic)
        if len(topics) >= 2:
            break
    if not topics:
        return "本周改动整理"
    if "PM完成时间同步" in topics and "README和结构图收口" in topics:
        return "PM同步和文档收口"
    if topics[0] == "问题迁移修复" and len(topics) > 1 and "缓存" in topics[1]:
        return "问题迁移修复和缓存优化"
    return "、".join(topics)


def _project_name(source: dict[str, Any], repo_root: Path) -> str:
    explicit = _text(source.get("project_name"))
    if explicit:
        return explicit
    current_context = _load_current_context(repo_root)
    project = current_context.get("project") if isinstance(current_context.get("project"), dict) else {}
    if _text(project.get("name")):
        return _text(project.get("name"))
    pm_path = repo_root / "pm.json"
    if pm_path.exists():
        try:
            pm_data = _load_json(pm_path)
        except Exception:
            pm_data = {}
        project_cfg = pm_data.get("project") if isinstance(pm_data.get("project"), dict) else {}
        if _text(project_cfg.get("name")):
            return _text(project_cfg.get("name"))
    return repo_root.name


def _source_status(repo_root: Path) -> str:
    if _aggregate_review_projects(repo_root):
        return "推进中"
    current_context = _load_current_context(repo_root)
    open_tasks = current_context.get("open_tasks") if isinstance(current_context.get("open_tasks"), list) else []
    if open_tasks:
        return "推进中"
    project_scan = _load_project_scan(repo_root)
    gsd = project_scan.get("gsd") if isinstance(project_scan.get("gsd"), dict) else {}
    summaries = gsd.get("summaries") if isinstance(gsd.get("summaries"), dict) else {}
    if _extract_active_items(_text(summaries.get("project"))):
        return "推进中"
    return "待收口"


def _period_key(now_iso: str) -> str:
    current = datetime.fromisoformat(now_iso)
    week = current.isocalendar()
    return f"main-weekly-{week.year}-W{week.week:02d}"


def build_main_review_payload(
    config: dict[str, Any],
    *,
    since: str,
    until: str | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    summaries: list[dict[str, Any]] = []
    source_meta: list[dict[str, Any]] = []
    current_now = str(now_iso or _now_iso())
    main_target = _main_target(config)

    sources = config.get("sources") if isinstance(config.get("sources"), list) else []
    for source in sources:
        if not isinstance(source, dict):
            continue
        if source.get("enabled") is False:
            continue
        repo_root = Path(_text(source.get("repo_root"))).expanduser()
        if not repo_root.exists():
            continue
        try:
            commits = collect_recent_commits(str(repo_root), since, until)
        except Exception:
            continue
        if not commits:
            continue

        done = _derive_done(repo_root, commits)
        pending, next_step = _derive_pending_next(repo_root)
        summaries.append(
            {
                "project": _project_name(source, repo_root),
                "done": done,
                "pending": pending,
                "next_step": next_step,
                "status": _source_status(repo_root),
            }
        )
        source_meta.append(
            {
                "key": _text(source.get("key")) or repo_root.name,
                "repo_root": str(repo_root),
                "commit_count": len(commits),
                "latest_commit": commits[0],
            }
        )

    if not summaries:
        raise ValueError("no active projects with recent commits found for main review")
    if not main_target["chat_id"]:
        raise ValueError("main review config is missing main target chat_id")

    return {
        "trigger_kind": "weekly",
        "project_name": _text(config.get("main_project_name")) or "全部项目",
        "channel_id": main_target["chat_id"],
        "project_summaries": summaries,
        "period_key": _period_key(current_now),
        "meta": {
            "main_target_alias": main_target["alias"],
            "main_target_channel": main_target["channel"],
            "main_chat_name": main_target["chat_name"],
            "since": since,
            "until": until,
            "generated_at": current_now,
            "sources": source_meta,
        },
    }


def prepare_main_review(
    config: dict[str, Any],
    *,
    since: str,
    until: str | None = None,
    state_path: str | Path | None = None,
    now_iso: str | None = None,
    model: str = "main-review",
) -> dict[str, Any]:
    payload = build_main_review_payload(config, since=since, until=until, now_iso=now_iso)
    prepared = prepare_review(
        payload,
        state_path=state_path,
        now_iso=now_iso,
        model=model,
    )
    return {
        "payload": payload,
        "prepared": prepared,
    }


def send_main_review(
    config: dict[str, Any],
    *,
    since: str,
    until: str | None = None,
    state_path: str | Path | None = None,
    now_iso: str | None = None,
    model: str = "main-review",
    openclaw_bin: str = "openclaw",
    dry_run: bool = False,
) -> dict[str, Any]:
    prepared_result = prepare_main_review(
        config,
        since=since,
        until=until,
        state_path=state_path,
        now_iso=now_iso,
        model=model,
    )
    prepared = prepared_result["prepared"]
    delivery = send_review_card(
        prepared["review_id"],
        state_path=state_path,
        now_iso=now_iso,
        openclaw_bin=openclaw_bin,
        dry_run=dry_run,
    )
    return {
        "payload": prepared_result["payload"],
        "prepared": prepared,
        "delivery": delivery,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or send a main-group review across active projects.")
    parser.add_argument("--config", help="Main review config JSON. Defaults to OpenClaw runtime config, then bundled skill config.")
    parser.add_argument("--since", help="Git --since window. Defaults to config.default_since or 7 days ago.")
    parser.add_argument("--until", help="Optional Git --until window.")
    parser.add_argument("--state-path", help="Review state path for the aggregate review. Defaults beside the OpenClaw runtime config.")
    parser.add_argument("--now-iso", help="Optional ISO8601 timestamp.")
    parser.add_argument("--model", default="main-review", help="Review model label.")
    parser.add_argument("--openclaw-bin", default="openclaw", help="OpenClaw CLI binary.")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("build", help="Build one aggregate payload.")
    subparsers.add_parser("prepare", help="Build payload and persist one drafted review.")
    send_parser = subparsers.add_parser("send", help="Build payload, prepare review, and send to main.")
    send_parser.add_argument("--dry-run", action="store_true", help="Only prepare and render the outgoing card.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    resolved_config_path = resolve_main_review_config_path(args.config)
    resolved_state_path = resolve_main_review_state_path(args.state_path, config_path=resolved_config_path)
    config = _load_json(resolved_config_path)
    since = _text(args.since) or _text(config.get("default_since")) or "7 days ago"

    if args.command == "build":
        result = build_main_review_payload(config, since=since, until=args.until, now_iso=args.now_iso)
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.command == "prepare":
        result = prepare_main_review(
            config,
            since=since,
            until=args.until,
            state_path=resolved_state_path,
            now_iso=args.now_iso,
            model=args.model,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.command == "send":
        result = send_main_review(
            config,
            since=since,
            until=args.until,
            state_path=resolved_state_path,
            now_iso=args.now_iso,
            model=args.model,
            openclaw_bin=args.openclaw_bin,
            dry_run=bool(getattr(args, "dry_run", False)),
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0

    raise ValueError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())


def build_main_digest_payload(
    config: dict[str, Any],
    *,
    since: str,
    until: str | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    return build_main_review_payload(config, since=since, until=until, now_iso=now_iso)


def prepare_main_digest(
    config: dict[str, Any],
    *,
    since: str,
    until: str | None = None,
    state_path: str | Path | None = None,
    now_iso: str | None = None,
    model: str = "main-digest",
) -> dict[str, Any]:
    return prepare_main_review(config, since=since, until=until, state_path=state_path, now_iso=now_iso, model=model)


def send_main_digest(
    config: dict[str, Any],
    *,
    since: str,
    until: str | None = None,
    state_path: str | Path | None = None,
    now_iso: str | None = None,
    model: str = "main-digest",
    openclaw_bin: str = "openclaw",
    dry_run: bool = False,
) -> dict[str, Any]:
    return send_main_review(
        config,
        since=since,
        until=until,
        state_path=state_path,
        now_iso=now_iso,
        model=model,
        openclaw_bin=openclaw_bin,
        dry_run=dry_run,
    )
