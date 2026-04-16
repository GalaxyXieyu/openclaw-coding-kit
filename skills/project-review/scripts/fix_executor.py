#!/usr/bin/env python3
"""Execute fix-now flows for project-review risk cards."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from review_state_store import append_history, default_state_path, get_review_by_id, load_state, upsert_review_record


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_pm_module() -> Any:
    pm_root = str(Path(__file__).resolve().parents[2] / "pm" / "scripts")
    if pm_root not in sys.path:
        sys.path.insert(0, pm_root)
    import pm  # type: ignore

    return pm


def _load_review_record(state_path: str | Path, review_id: str) -> dict[str, Any]:
    state = load_state(state_path)
    record = get_review_by_id(state, review_id)
    if record is None:
        raise KeyError(f"review_id not found: {review_id}")
    return record


def _repo_root(record: dict[str, Any]) -> Path:
    source_payload = record.get("source_payload") if isinstance(record.get("source_payload"), dict) else {}
    bundle = record.get("bundle") if isinstance(record.get("bundle"), dict) else {}
    project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
    for candidate in (
        source_payload.get("repo_root"),
        project.get("repo_root"),
    ):
        text = str(candidate or "").strip()
        if text:
            return Path(text).expanduser().resolve()
    return Path.cwd().resolve()


def _normalize_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items or []:
        if isinstance(item, dict):
            result.append(item)
    return result


def build_fix_scope(record: dict[str, Any]) -> dict[str, Any]:
    bundle = record.get("bundle") if isinstance(record.get("bundle"), dict) else {}
    findings = _normalize_items(bundle.get("findings"))
    docs_flags = [str(item).strip() for item in bundle.get("docs_flags") or [] if str(item).strip()]
    changed_scope = bundle.get("changed_scope") if isinstance(bundle.get("changed_scope"), dict) else {}
    commits = _normalize_items(bundle.get("commits"))

    severity_order = {"P0": 0, "P1": 1, "P2": 2}
    findings = sorted(
        findings,
        key=lambda item: (
            severity_order.get(str(item.get("severity") or "P2").upper(), 9),
            str(item.get("title") or ""),
            str(item.get("file") or ""),
        ),
    )
    top_findings = findings[:5]
    files = []
    seen: set[str] = set()
    for item in top_findings:
        path = str(item.get("file") or "").strip()
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    if not files:
        for raw in changed_scope.get("files") or []:
            path = str(raw or "").strip()
            if path and path not in seen:
                seen.add(path)
                files.append(path)
    return {
        "review_id": str(record.get("review_id") or "").strip(),
        "project_name": str(record.get("project_name") or "").strip(),
        "card_kind": str(record.get("card_kind") or "").strip(),
        "trigger_kind": str(record.get("trigger_kind") or "").strip(),
        "top_findings": top_findings,
        "docs_flags": docs_flags[:5],
        "changed_files": [str(item).strip() for item in changed_scope.get("files") or [] if str(item).strip()],
        "fix_files": files,
        "requires_uiux_review": bool(changed_scope.get("touches_ui")),
        "latest_commit_hash": str(record.get("latest_commit_hash") or "").strip() or str((commits[0] if commits else {}).get("hash") or "").strip(),
        "latest_commit_subject": str((commits[0] if commits else {}).get("subject") or "").strip(),
    }


def _fix_request(scope: dict[str, Any], *, repo_root: Path) -> str:
    lines = [
        f"本次需要修复 review `{scope.get('review_id')}` 暴露出的代码健康问题。",
        f"仓库：{repo_root}",
        "修复要求：",
        "- 先处理 P0 / P1 风险，再处理明显的 P2。",
        "- 涉及 docs 漂移时，同时更新相关文档和 AGENTS.md。",
        "- 如果命中了超长文件，优先按职责拆分，不要只做格式化或搬空行。",
        "- 如果更新了文档，完成说明里要明确写出“补了什么项目描述/规则”。",
        "- 改动范围尽量收敛在当前风险涉及文件。",
    ]
    if scope.get("requires_uiux_review"):
        lines.append("- 本次涉及 UI 路径，修完后需要补一轮 ui-ux-review。")
    latest_commit_subject = str(scope.get("latest_commit_subject") or "").strip()
    if latest_commit_subject:
        lines.append(f"- 最近提交：{latest_commit_subject}")
    top_findings = scope.get("top_findings") if isinstance(scope.get("top_findings"), list) else []
    if top_findings:
        lines.append("")
        lines.append("重点风险：")
        for item in top_findings:
            severity = str(item.get("severity") or "P2").upper()
            title = str(item.get("title") or "").strip()
            summary = str(item.get("summary") or "").strip()
            file_path = str(item.get("file") or "").strip()
            text = f"- [{severity}] {title}"
            if file_path:
                text += f" ({file_path})"
            if summary:
                text += f"：{summary}"
            lines.append(text)
    docs_flags = scope.get("docs_flags") if isinstance(scope.get("docs_flags"), list) else []
    if docs_flags:
        lines.append("")
        lines.append("文档治理：")
        lines.extend(f"- {item}" for item in docs_flags)
    fix_files = scope.get("fix_files") if isinstance(scope.get("fix_files"), list) else []
    if fix_files:
        lines.append("")
        lines.append("优先关注文件：")
        lines.extend(f"- {item}" for item in fix_files[:8])
    return "\n".join(lines)


def _activate_pm(pm: Any, *, repo_root: Path) -> tuple[dict[str, Any], str]:
    snapshot = dict(getattr(pm, "ACTIVE_CONFIG", {}))
    config_path = str((repo_root / "pm.json").resolve())
    active_config = getattr(pm, "ACTIVE_CONFIG")
    active_config.clear()
    active_config.update(pm.load_config(config_path))
    active_config["repo_root"] = str(repo_root)
    return snapshot, config_path


def _restore_pm(pm: Any, snapshot: dict[str, Any]) -> None:
    active_config = getattr(pm, "ACTIVE_CONFIG")
    active_config.clear()
    active_config.update(snapshot)


def _task_id_from_task(pm: Any, task: dict[str, Any]) -> str:
    parsed = pm.parse_task_summary(str(task.get("summary") or "").strip()) or {}
    return str(parsed.get("task_id") or task.get("normalized_task_id") or "").strip()


def _repair_contract_path(repo_root: Path, review_id: str) -> Path:
    safe_id = "".join(char.lower() if char.isalnum() else "-" for char in str(review_id or "").strip()).strip("-") or "review"
    return repo_root / ".pm" / f"project-review-fix-{safe_id}.json"


def _write_repair_contract(
    *,
    repo_root: Path,
    review_id: str,
    now_iso: str,
    scope: dict[str, Any],
    request: str,
    task_id: str,
    task_guid: str,
) -> Path:
    path = _repair_contract_path(repo_root, review_id)
    payload = {
        "review_id": review_id,
        "generated_at": now_iso,
        "repo_root": str(repo_root),
        "task_id": task_id,
        "task_guid": task_guid,
        "scope": scope,
        "request_markdown": request,
        "execution_rules": [
            "先处理 P0/P1，再处理明显的 P2。",
            "优先收敛在 fix_files；若测试、文档或 AGENTS.md 必须联动，可扩展到直接相关文件。",
            "如果只有 docs_flags，没有实质代码风险，允许只做文档修复。",
            "涉及 docs 漂移时，同步更新相关 docs 与 AGENTS.md。",
            "如果命中了超长文件，优先做职责拆分，不要只做表面清理。",
            "完成后要说明文档新增/修正了哪些项目描述、规则或约束。",
            "完成后给出变更文件、测试结果和剩余风险。",
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _build_fix_run_message(
    base_message: str,
    *,
    contract_path: Path,
    scope: dict[str, Any],
) -> str:
    lines = [str(base_message or "").strip(), "", "Project-review repair contract:"]
    lines.append(f"- Review id: {scope.get('review_id') or ''}")
    lines.append(f"- Contract JSON: {contract_path}")
    lines.append("- Read the repair contract JSON before coding.")
    lines.append("- Keep edits scoped to the listed fix files unless tests/docs/AGENTS sync requires a nearby change.")
    if scope.get("docs_flags"):
        lines.append("- This run includes docs drift; update the relevant docs and AGENTS.md if needed.")
        lines.append("- In the completion summary, explicitly list which product/project descriptions were updated in docs.")
    if scope.get("requires_uiux_review"):
        lines.append("- This run touches UI scope; keep notes for a follow-up ui-ux-review.")
    fix_files = [str(item).strip() for item in (scope.get("fix_files") or []) if str(item).strip()]
    if fix_files:
        lines.append("Fix files:")
        lines.extend(f"- {item}" for item in fix_files[:12])
    return "\n".join(line for line in lines if str(line).strip())


def _error_message(exc: BaseException) -> str:
    text = str(exc).strip()
    if text:
        return text[:400]
    return exc.__class__.__name__


def _upsert_fix_execution(
    state_path: Path,
    review_id: str,
    *,
    now_iso: str,
    payload: dict[str, Any],
    history_event: str,
) -> dict[str, Any]:
    record = _load_review_record(state_path, review_id)
    next_record = dict(record)
    next_record["fix_execution"] = payload
    if payload.get("task_id"):
        next_record["fix_task_id"] = payload["task_id"]
    if payload.get("task_guid"):
        next_record["fix_task_guid"] = payload["task_guid"]
    next_record["updated_at"] = now_iso
    upsert_review_record(state_path, next_record)
    append_history(
        state_path,
        review_id,
        {
            "event": history_event,
            "at": now_iso,
            "fix_execution": payload,
        },
    )
    return next_record


def _create_or_reuse_fix_task(pm: Any, *, scope: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    tasklist = pm.ensure_tasklist()
    summary = f"修复代码健康风险 {scope.get('review_id')}"
    existing = pm.find_existing_task_by_summary(summary, include_completed=True)
    reused_existing = isinstance(existing, dict) and str(existing.get("guid") or "").strip() != ""
    request = _fix_request(scope, repo_root=repo_root)

    if reused_existing:
        task = pm.get_task_record_by_guid(str(existing.get("guid") or "").strip())
    else:
        task_id = pm.next_task_id()
        title = f"[{task_id}] {summary}"
        description = pm.build_description(task_id, summary, request, str(repo_root), pm.task_kind())
        owner = tasklist.get("owner") if isinstance(tasklist.get("owner"), dict) else {}
        task = pm.create_task(
            summary=title,
            description=description,
            tasklists=[{"tasklist_guid": str(tasklist.get("guid") or "").strip()}],
            current_user_id=str(owner.get("id") or "").strip(),
        )
        pm.refresh_context_cache(task_guid=str(task.get("guid") or "").strip())

    task_guid = str(task.get("guid") or "").strip()
    task_id = _task_id_from_task(pm, task)
    task_comment = pm.create_task_comment(task_guid, request) if task_guid else None
    return {
        "task": task,
        "task_id": task_id,
        "task_guid": task_guid,
        "request": request,
        "task_comment": task_comment,
        "reused_existing": reused_existing,
    }


def _build_execution_payload(
    *,
    review_id: str,
    repo_root: Path,
    config_path: str,
    scope: dict[str, Any],
    task_context: dict[str, Any],
    repair_contract_path: Path,
    updated_at: str,
) -> dict[str, Any]:
    task = task_context["task"]
    return {
        "status": "task_created",
        "review_id": review_id,
        "repo_root": str(repo_root),
        "config_path": config_path,
        "task_id": task_context["task_id"],
        "task_guid": task_context["task_guid"],
        "task_summary": str(task.get("summary") or "").strip(),
        "reused_existing": bool(task_context["reused_existing"]),
        "requires_uiux_review": bool(scope.get("requires_uiux_review")),
        "docs_update_expected": bool(scope.get("docs_flags")),
        "fix_files": list(scope.get("fix_files") or []),
        "repair_contract_path": str(repair_contract_path),
        "task_comment_result": task_context["task_comment"],
        "updated_at": updated_at,
    }


def _run_fix_coder(
    pm: Any,
    *,
    task_guid: str,
    repo_root: Path,
    scope: dict[str, Any],
    repair_contract_path: Path,
    model: str,
    timeout_seconds: int,
    thinking: str,
) -> dict[str, Any]:
    context_path = None
    message = ""
    try:
        bundle, context_path = pm.build_coder_context(task_guid=task_guid)
        message = _build_fix_run_message(
            pm.build_run_message(bundle),
            contract_path=repair_contract_path,
            scope=scope,
        )
        run_result = pm.run_codex_cli(
            agent_id=model,
            message=message,
            cwd=str(repo_root),
            timeout_seconds=timeout_seconds,
            thinking=thinking,
        )
        side_effects = pm.persist_run_side_effects(bundle, run_result)
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            raise
        return {
            "status": "coder_failed",
            "coder_context_path": str(context_path) if context_path else "",
            "coder_backend": "codex-cli",
            "coder_model": model,
            "coder_message_preview": message[:4000],
            "coder_error": _error_message(exc),
            "coder_error_type": exc.__class__.__name__,
            "uiux_review_status": "pending_integration" if scope.get("requires_uiux_review") else "not_required",
        }
    return {
        "status": "coder_completed",
        "coder_context_path": str(context_path),
        "coder_backend": str(run_result.get("backend") or "codex-cli"),
        "coder_model": model,
        "coder_message_preview": message[:4000],
        "coder_result": run_result,
        "coder_side_effects": side_effects,
        "uiux_review_status": "pending_integration" if scope.get("requires_uiux_review") else "not_required",
    }


def execute_fix_flow(
    review_id: str,
    *,
    state_path: str | Path | None = None,
    now_iso: str | None = None,
    auto_run: bool = True,
    model: str = "codex",
    timeout_seconds: int = 900,
    thinking: str = "high",
) -> dict[str, Any]:
    resolved_state_path = Path(state_path or default_state_path()).resolve()
    record = _load_review_record(resolved_state_path, review_id)
    scope = build_fix_scope(record)
    repo_root = _repo_root(record)
    pm = _load_pm_module()
    current_now = str(now_iso or _now_iso())

    snapshot, config_path = _activate_pm(pm, repo_root=repo_root)
    try:
        task_context = _create_or_reuse_fix_task(pm, scope=scope, repo_root=repo_root)
        repair_contract_path = _write_repair_contract(
            repo_root=repo_root,
            review_id=review_id,
            now_iso=current_now,
            scope=scope,
            request=str(task_context["request"] or ""),
            task_id=str(task_context["task_id"] or ""),
            task_guid=str(task_context["task_guid"] or ""),
        )
        execution = _build_execution_payload(
            review_id=review_id,
            repo_root=repo_root,
            config_path=config_path,
            scope=scope,
            task_context=task_context,
            repair_contract_path=repair_contract_path,
            updated_at=current_now,
        )
        if auto_run and task_context["task_guid"]:
            execution.update(
                _run_fix_coder(
                    pm,
                    task_guid=str(task_context["task_guid"] or ""),
                    repo_root=repo_root,
                    scope=scope,
                    repair_contract_path=repair_contract_path,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    thinking=thinking,
                )
            )

        _upsert_fix_execution(
            resolved_state_path,
            review_id,
            now_iso=current_now,
            payload=execution,
            history_event="fix_flow_executed",
        )
        return execution
    finally:
        _restore_pm(pm, snapshot)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute one project-review fix-now flow.")
    parser.add_argument("--review-id", required=True, help="Review id to fix")
    parser.add_argument("--state-path", help="Optional project-review state path")
    parser.add_argument("--now-iso", help="Optional ISO8601 timestamp")
    parser.add_argument("--no-auto-run", action="store_true", help="Only create/reuse the fix task, skip coder execution")
    parser.add_argument("--model", default="codex", help="Codex model label")
    parser.add_argument("--timeout-seconds", type=int, default=900, help="Coder timeout")
    parser.add_argument("--thinking", default="high", help="Coder thinking label")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = execute_fix_flow(
        args.review_id,
        state_path=args.state_path,
        now_iso=args.now_iso,
        auto_run=not args.no_auto_run,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
        thinking=args.thinking,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
