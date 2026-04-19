#!/usr/bin/env python3
"""Nightly auto review runner for project-review."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from commit_window import collect_recent_commits
from fix_executor import execute_fix_flow
from review_delivery import send_review_card
from review_orchestrator import execute_review_with_codex, prepare_review
from review_state_store import default_state_path, get_review_by_id, load_state, upsert_review_record

DOC_PREFIXES = ("docs/", "doc/", "plan/", ".planning/")
DOC_FILES = {"README.md", "README.zh-CN.md", "AGENTS.md"}
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs", ".kt")
TEST_MARKERS = ("test_", "_test.", ".spec.", ".test.", "tests/", "__tests__/")
LONG_FILE_TITLES = {"单文件超过 1000 行", "文件接近 1000 行"}
DEFAULT_AUTO_FIX_MODE = "long-file-and-docs"
DEFAULT_TIMEZONE = "Asia/Shanghai"
DEFAULT_CRON = "30 0 * * *"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid JSON object: {path}")
    return payload


def _load_pm_config(pm_config_path: str, repo_root: Path) -> tuple[Path, dict[str, Any]]:
    config_path = Path(pm_config_path).expanduser() if pm_config_path else repo_root / "pm.json"
    if not config_path.is_absolute():
        config_path = (repo_root / config_path).resolve()
    if not config_path.exists():
        return config_path, {}
    return config_path, _load_json(config_path)


def _run_git(repo_root: Path, args: list[str], *, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if check and completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout).strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def _normalize_paths(paths: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in paths or []:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _normalize_doc_updates(items: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if not path or not summary:
            continue
        key = (path, summary)
        if key in seen:
            continue
        seen.add(key)
        result.append({"path": path, "summary": summary})
    return result


def _normalize_texts(items: list[Any] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in items or []:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _is_doc_file(path: str) -> bool:
    return path.startswith(DOC_PREFIXES) or path.endswith(".md") or path in DOC_FILES


def _is_test_file(path: str) -> bool:
    return any(marker in path for marker in TEST_MARKERS)


def _is_code_file(path: str) -> bool:
    return path.endswith(CODE_SUFFIXES) and not _is_test_file(path)


def _parse_status_path(raw: str) -> str:
    text = str(raw or "").rstrip()
    if len(text) < 4:
        return ""
    path = text[3:].strip()
    if " -> " in path:
        path = path.split(" -> ", 1)[1].strip()
    return path


def collect_dirty_files(repo_root: Path) -> list[str]:
    output = _run_git(repo_root, ["status", "--porcelain"], check=True)
    return _normalize_paths([_parse_status_path(line) for line in output.splitlines()])


def collect_recent_changed_files(repo_root: Path, since: str, until: str | None = None) -> list[str]:
    args = ["log", "--name-only", "--pretty=format:", f"--since={since}"]
    if until:
        args.append(f"--until={until}")
    output = _run_git(repo_root, args, check=True)
    return _normalize_paths(output.splitlines())


def list_tracked_files(repo_root: Path) -> list[str]:
    output = _run_git(repo_root, ["ls-files"], check=True)
    return _normalize_paths(output.splitlines())


def _safe_line_count(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except UnicodeDecodeError:
        return len(path.read_text(encoding="utf-8", errors="ignore").splitlines())
    except FileNotFoundError:
        return 0


def collect_file_stats(repo_root: Path, paths: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative_path in paths:
        target = repo_root / relative_path
        if not target.is_file():
            continue
        line_count = _safe_line_count(target)
        if line_count <= 0:
            continue
        rows.append({"path": relative_path, "line_count": line_count})
    return rows


def _function_length(node: ast.AST) -> int:
    start = int(getattr(node, "lineno", 0) or 0)
    end = int(getattr(node, "end_lineno", 0) or 0)
    if start <= 0 or end <= 0:
        return 0
    return max(end - start + 1, 0)


def collect_python_function_stats(repo_root: Path, paths: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    stats: list[dict[str, Any]] = []
    errors: list[str] = []
    for relative_path in paths:
        if not relative_path.endswith(".py"):
            continue
        target = repo_root / relative_path
        if not target.is_file():
            continue
        try:
            source = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = target.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source, filename=relative_path)
        except SyntaxError as exc:
            errors.append(f"{relative_path}:{exc.lineno or 0}: {exc.msg}")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            line_count = _function_length(node)
            if line_count <= 0:
                continue
            stats.append(
                {
                    "path": relative_path,
                    "name": str(node.name),
                    "line_count": line_count,
                }
            )
    return stats, _normalize_texts(errors)


def _commit_diff_range(commits: list[dict[str, Any]]) -> str:
    if not commits:
        return ""
    oldest = str(commits[-1].get("hash") or "").strip()
    if not oldest:
        return ""
    return f"{oldest}^..HEAD"


def _collect_diff_text(repo_root: Path, path: str, diff_range: str) -> str:
    texts: list[str] = []
    if diff_range:
        for range_spec in (diff_range, diff_range.replace("^..", "..")):
            if not range_spec:
                continue
            try:
                text = _run_git(repo_root, ["diff", "--unified=0", "--no-color", range_spec, "--", path], check=True)
            except RuntimeError:
                text = ""
            if text:
                texts.append(text)
                break
    for args in (
        ["diff", "--cached", "--unified=0", "--no-color", "--", path],
        ["diff", "--unified=0", "--no-color", "--", path],
    ):
        try:
            text = _run_git(repo_root, args, check=True)
        except RuntimeError:
            text = ""
        if text:
            texts.append(text)
    return "\n".join(texts)


def _diff_added_lines(diff_text: str) -> list[str]:
    rows: list[str] = []
    for raw in str(diff_text or "").splitlines():
        if not raw.startswith("+") or raw.startswith("+++"):
            continue
        rows.append(raw[1:])
    return rows


def _clean_doc_line(text: str) -> str:
    item = str(text or "").strip()
    if not item:
        return ""
    item = item.strip("`")
    item = item.lstrip("#").strip()
    item = item.lstrip("-*").strip()
    while item[:2].isdigit() and len(item) > 2 and item[2] in {".", "、"}:
        item = item[3:].strip()
    item = " ".join(item.split())
    if len(item) < 6:
        return ""
    return item[:120]


def _doc_summary_candidates(lines: list[str]) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        cleaned = _clean_doc_line(raw)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        stripped = str(raw or "").lstrip()
        if stripped.startswith("#"):
            candidates.append(f"补充「{cleaned}」章节")
        elif stripped.startswith(("-", "*")):
            candidates.append(f"新增说明：{cleaned}")
        else:
            candidates.append(f"更新说明：{cleaned}")
        if len(candidates) >= 2:
            break
    return candidates


def collect_doc_updates(repo_root: Path, doc_paths: list[str], commits: list[dict[str, Any]]) -> list[dict[str, str]]:
    diff_range = _commit_diff_range(commits)
    updates: list[dict[str, str]] = []
    expanded_paths: list[str] = []
    for relative_path in _normalize_paths(doc_paths):
        target = repo_root / relative_path
        if target.is_dir():
            for child in sorted(target.rglob("*.md"))[:8]:
                expanded_paths.append(str(child.relative_to(repo_root)))
            continue
        expanded_paths.append(relative_path)
    for relative_path in _normalize_paths(expanded_paths):
        target = repo_root / relative_path
        added_lines = _diff_added_lines(_collect_diff_text(repo_root, relative_path, diff_range))
        if not added_lines and target.is_file() and relative_path not in list_tracked_files(repo_root):
            try:
                added_lines = target.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                added_lines = target.read_text(encoding="utf-8", errors="ignore").splitlines()
        candidates = _doc_summary_candidates(added_lines)
        if not candidates:
            summary = f"更新 {relative_path} 的项目说明"
        else:
            summary = "；".join(candidates)
        updates.append({"path": relative_path, "summary": summary})
    return _normalize_doc_updates(updates)


def _review_bundle(review_result: dict[str, Any]) -> dict[str, Any]:
    if isinstance(review_result.get("ingested"), dict) and isinstance(review_result["ingested"].get("bundle"), dict):
        return review_result["ingested"]["bundle"]
    if isinstance(review_result.get("prepared"), dict) and isinstance(review_result["prepared"].get("bundle"), dict):
        return review_result["prepared"]["bundle"]
    if isinstance(review_result.get("bundle"), dict):
        return review_result["bundle"]
    return {}


def _review_id(review_result: dict[str, Any]) -> str:
    for key in ("review_id",):
        value = str(review_result.get(key) or "").strip()
        if value:
            return value
    prepared = review_result.get("prepared") if isinstance(review_result.get("prepared"), dict) else {}
    return str(prepared.get("review_id") or "").strip()


def _resolve_channel_id(config: dict[str, Any], explicit: str = "") -> str:
    if explicit:
        return explicit
    nightly = config.get("project_review") if isinstance(config.get("project_review"), dict) else {}
    nightly_cfg = nightly.get("nightly") if isinstance(nightly.get("nightly"), dict) else {}
    for candidate in (
        nightly_cfg.get("channel_id"),
        (nightly_cfg.get("delivery") if isinstance(nightly_cfg.get("delivery"), dict) else {}).get("channel_id"),
        (config.get("project") if isinstance(config.get("project"), dict) else {}).get("group_id"),
    ):
        text = str(candidate or "").strip()
        if text:
            return text
    return ""


def _nightly_cfg(config: dict[str, Any]) -> dict[str, Any]:
    project_review = config.get("project_review")
    if isinstance(project_review, dict) and isinstance(project_review.get("nightly"), dict):
        return project_review["nightly"]
    return {}


def _build_payload(
    *,
    repo_root: Path,
    config: dict[str, Any],
    since: str,
    until: str | None,
    channel_id: str,
    include_dirty: bool,
) -> dict[str, Any]:
    commits = collect_recent_commits(str(repo_root), since, until)
    commit_files = collect_recent_changed_files(repo_root, since, until)
    dirty_files = collect_dirty_files(repo_root) if include_dirty else []
    changed_files = _normalize_paths(commit_files + dirty_files)
    tracked_files = list_tracked_files(repo_root)
    tracked_code_files = [path for path in tracked_files if _is_code_file(path)]
    extra_code_files = [path for path in changed_files if _is_code_file(path)]
    stat_targets = _normalize_paths(tracked_code_files + extra_code_files)
    file_stats = collect_file_stats(repo_root, stat_targets)
    function_stats, syntax_errors = collect_python_function_stats(repo_root, stat_targets)
    doc_paths = [path for path in changed_files if _is_doc_file(path)]
    doc_updates = collect_doc_updates(repo_root, doc_paths, commits)
    project = config.get("project") if isinstance(config.get("project"), dict) else {}
    project_name = str(project.get("name") or "").strip() or repo_root.name
    return {
        "trigger_kind": "daily",
        "project_name": project_name,
        "channel_id": channel_id,
        "repo_root": str(repo_root),
        "has_recent_commits": bool(commits or changed_files),
        "commits": commits,
        "changed_files": changed_files,
        "file_stats": file_stats,
        "function_stats": function_stats,
        "type_errors": syntax_errors,
        "doc_updates": doc_updates,
        "repo_has_agents": (repo_root / "AGENTS.md").exists(),
        "agent_sync_required": bool([path for path in changed_files if _is_code_file(path)]),
        "review_window": {
            "since": since,
            "until": until or "",
        },
    }


def _auto_fix_signal(bundle: dict[str, Any], mode: str) -> tuple[bool, str]:
    normalized_mode = str(mode or "off").strip().lower()
    findings = bundle.get("findings") if isinstance(bundle.get("findings"), list) else []
    docs_flags = _normalize_texts(bundle.get("docs_flags"))
    has_any = bool(findings or docs_flags)
    has_long_file = False
    for item in findings:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        category = str(item.get("category") or "").strip()
        if title in LONG_FILE_TITLES or category == "size":
            has_long_file = True
            break
    if normalized_mode == "off":
        return False, "disabled"
    if normalized_mode == "all":
        return has_any, "any finding/docs drift"
    if normalized_mode == "long-file":
        return has_long_file, "long file findings"
    if normalized_mode == "long-file-and-docs":
        return (has_long_file or bool(docs_flags)), "long file or docs drift"
    raise ValueError(f"Unsupported auto-fix mode: {mode}")


def _automation_updates(fix_result: dict[str, Any] | None, *, dry_run: bool, auto_fix_reason: str, auto_fix_triggered: bool) -> list[str]:
    if dry_run:
        if auto_fix_triggered:
            return [f"dry-run：本轮会按「{auto_fix_reason}」策略触发自动修复。"]
        return []
    if not isinstance(fix_result, dict) or not fix_result:
        return []
    status = str(fix_result.get("status") or "").strip()
    task_id = str(fix_result.get("task_id") or "").strip()
    lines: list[str] = []
    if status == "coder_completed":
        lines.append(f"已自动创建并执行修复任务 {task_id or '未命名任务'}。")
    elif status == "task_created":
        lines.append(f"已自动创建修复任务 {task_id or '未命名任务'}，等待后续执行。")
    elif status:
        lines.append(f"自动修复状态：{status}")
    fix_files = _normalize_texts(fix_result.get("fix_files"))
    if fix_files:
        lines.append(f"优先处理文件：{', '.join(fix_files[:3])}")
    if bool(fix_result.get("docs_update_expected")):
        lines.append("修复要求里已包含 docs/AGENTS 同步，并要求说明具体补了什么描述。")
    return lines[:4]


def _augment_record(
    *,
    state_path: Path,
    review_id: str,
    channel_id: str,
    doc_updates: list[dict[str, Any]],
    automation_updates: list[str],
    now_iso: str,
) -> dict[str, Any]:
    state = load_state(state_path)
    current = get_review_by_id(state, review_id)
    if current is None:
        raise KeyError(f"review_id not found: {review_id}")
    record = dict(current)
    bundle = dict(record.get("bundle") or {})
    source_payload = dict(record.get("source_payload") or {})
    card_preview = dict(record.get("card_preview") or {})
    normalized_doc_updates = _normalize_doc_updates(doc_updates)
    if normalized_doc_updates:
        bundle["doc_updates"] = normalized_doc_updates
        source_payload["doc_updates"] = normalized_doc_updates
        card_preview["doc_updates"] = normalized_doc_updates
    if automation_updates:
        card_preview["automation_updates"] = _normalize_texts(automation_updates)
    if channel_id:
        record["channel_id"] = channel_id
    record["bundle"] = bundle
    record["source_payload"] = source_payload
    record["card_preview"] = card_preview
    record["updated_at"] = now_iso
    return upsert_review_record(state_path, record)


def run_nightly_review(
    *,
    repo_root: str,
    pm_config: str = "",
    since: str = "24 hours ago",
    until: str | None = None,
    state_path: str = "",
    channel_id: str = "",
    reviewer_model: str = "",
    reviewer_timeout_seconds: int = 1200,
    reviewer_thinking: str = "high",
    auto_fix_mode: str = DEFAULT_AUTO_FIX_MODE,
    auto_fix_model: str = "codex",
    auto_fix_timeout_seconds: int = 1800,
    auto_fix_thinking: str = "high",
    send_if_possible: bool = True,
    include_dirty: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    resolved_repo_root = Path(repo_root).expanduser().resolve()
    config_path, config = _load_pm_config(pm_config, resolved_repo_root)
    nightly = _nightly_cfg(config)
    resolved_channel_id = _resolve_channel_id(config, explicit=channel_id)
    resolved_state_path = Path(state_path).resolve() if state_path else default_state_path(str(resolved_repo_root))
    payload = _build_payload(
        repo_root=resolved_repo_root,
        config=config,
        since=since,
        until=until,
        channel_id=resolved_channel_id,
        include_dirty=include_dirty,
    )

    if reviewer_model:
        review_result = execute_review_with_codex(
            payload,
            state_path=resolved_state_path,
            now_iso=_now_iso(),
            model=reviewer_model,
            timeout_seconds=reviewer_timeout_seconds,
            thinking=reviewer_thinking,
        )
    else:
        review_result = prepare_review(
            payload,
            state_path=resolved_state_path,
            now_iso=_now_iso(),
        )

    review_id = _review_id(review_result)
    bundle = _review_bundle(review_result)
    auto_fix_triggered, auto_fix_reason = _auto_fix_signal(bundle, auto_fix_mode)
    fix_result: dict[str, Any] | None = None
    if auto_fix_triggered and not dry_run:
        fix_result = execute_fix_flow(
            review_id,
            state_path=resolved_state_path,
            now_iso=_now_iso(),
            auto_run=True,
            model=auto_fix_model,
            timeout_seconds=auto_fix_timeout_seconds,
            thinking=auto_fix_thinking,
        )

    refreshed_payload = _build_payload(
        repo_root=resolved_repo_root,
        config=config,
        since=since,
        until=until,
        channel_id=resolved_channel_id,
        include_dirty=include_dirty,
    )
    automation_updates = _automation_updates(
        fix_result,
        dry_run=dry_run,
        auto_fix_reason=auto_fix_reason,
        auto_fix_triggered=auto_fix_triggered,
    )
    augmented = _augment_record(
        state_path=resolved_state_path,
        review_id=review_id,
        channel_id=resolved_channel_id,
        doc_updates=refreshed_payload.get("doc_updates") or [],
        automation_updates=automation_updates,
        now_iso=_now_iso(),
    )

    send_result: dict[str, Any]
    if not send_if_possible:
        send_result = {"status": "skipped", "reason": "disabled_by_flag"}
    elif not resolved_channel_id:
        send_result = {"status": "skipped", "reason": "missing_channel_id"}
    elif dry_run:
        preview = send_review_card(review_id, state_path=resolved_state_path, dry_run=True)
        send_result = {"status": "dry_run", "preview": preview}
    else:
        delivery = send_review_card(review_id, state_path=resolved_state_path)
        send_result = {"status": "sent", "delivery": delivery}

    project_name = str((config.get("project") if isinstance(config.get("project"), dict) else {}).get("name") or "").strip() or resolved_repo_root.name
    return {
        "ok": True,
        "repo_root": str(resolved_repo_root),
        "pm_config_path": str(config_path),
        "project_name": project_name,
        "channel_id": resolved_channel_id,
        "state_path": str(resolved_state_path),
        "review_id": review_id,
        "reviewer_model": reviewer_model,
        "auto_fix_mode": auto_fix_mode,
        "auto_fix_triggered": auto_fix_triggered,
        "auto_fix_reason": auto_fix_reason,
        "auto_fix_result": fix_result or {},
        "doc_updates": refreshed_payload.get("doc_updates") or [],
        "changed_files": refreshed_payload.get("changed_files") or [],
        "commits": refreshed_payload.get("commits") or [],
        "send_result": send_result,
        "record_status": str(augmented.get("status") or "").strip(),
        "nightly_config": nightly,
        "dry_run": dry_run,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one nightly project-review flow for a repo.")
    parser.add_argument("--repo-root", default=".", help="Repo root to review.")
    parser.add_argument("--pm-config", default="", help="Optional pm.json path.")
    parser.add_argument("--since", default="24 hours ago", help="Git review window start.")
    parser.add_argument("--until", default=None, help="Optional Git review window end.")
    parser.add_argument("--state-path", default="", help="Optional review state path.")
    parser.add_argument("--channel-id", default="", help="Optional explicit chat id override.")
    parser.add_argument("--reviewer-model", default="", help="Optional reviewer model. Empty means deterministic-only.")
    parser.add_argument("--reviewer-timeout-seconds", type=int, default=1200, help="Reviewer timeout per run.")
    parser.add_argument("--reviewer-thinking", default="high", help="Reviewer thinking mode.")
    parser.add_argument(
        "--auto-fix-mode",
        default=DEFAULT_AUTO_FIX_MODE,
        choices=("off", "long-file", "long-file-and-docs", "all"),
        help="Auto-fix trigger strategy.",
    )
    parser.add_argument("--auto-fix-model", default="codex", help="Auto-fix worker model.")
    parser.add_argument("--auto-fix-timeout-seconds", type=int, default=1800, help="Auto-fix timeout.")
    parser.add_argument("--auto-fix-thinking", default="high", help="Auto-fix thinking mode.")
    parser.add_argument("--no-send", action="store_true", help="Do not send the review card.")
    parser.add_argument("--no-dirty", action="store_true", help="Ignore local dirty files.")
    parser.add_argument("--dry-run", action="store_true", help="Build/preview only; do not send or auto-fix.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_nightly_review(
        repo_root=args.repo_root,
        pm_config=args.pm_config,
        since=args.since,
        until=args.until,
        state_path=args.state_path,
        channel_id=args.channel_id,
        reviewer_model=args.reviewer_model,
        reviewer_timeout_seconds=args.reviewer_timeout_seconds,
        reviewer_thinking=args.reviewer_thinking,
        auto_fix_mode=args.auto_fix_mode,
        auto_fix_model=args.auto_fix_model,
        auto_fix_timeout_seconds=args.auto_fix_timeout_seconds,
        auto_fix_thinking=args.auto_fix_thinking,
        send_if_possible=not args.no_send,
        include_dirty=not args.no_dirty,
        dry_run=bool(args.dry_run),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"review_id={result['review_id']}")
        print(f"project={result['project_name']}")
        print(f"auto_fix_triggered={result['auto_fix_triggered']}")
        print(f"send_status={result['send_result']['status']}")
        for item in result.get("doc_updates") or []:
            print(f"doc_update={item['path']}: {item['summary']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
