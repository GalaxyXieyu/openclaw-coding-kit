#!/usr/bin/env python3
"""Build normalized project-review bundles before lane execution."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from code_review_lane import run_code_review_lane
from docs_review_lane import run_docs_review_lane
from review_router import normalize_changed_files, route_review, touches_ui_paths
from summary_guard import build_project_summary, validate_project_summary


def _normalize_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items or []:
        if isinstance(item, dict):
            result.append(item)
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


def _project_summary_rows(project_summaries: list[dict[str, Any]] | None, *, limit: int = 50) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _normalize_items(project_summaries):
        project = str(item.get("project") or "").strip()
        done = str(item.get("done") or "").strip()
        pending = str(item.get("pending") or "").strip()
        next_step = str(item.get("next_step") or "").strip()
        summary = build_project_summary(project, done, pending, next_step, limit=limit)
        validation = validate_project_summary(summary, limit=limit)
        rows.append(
            {
                "project": project,
                "done": done,
                "pending": pending,
                "next_step": next_step,
                "summary": summary,
                "summary_ok": validation.ok,
                "validation_issues": list(validation.issues),
                "status": str(item.get("status") or "").strip(),
            }
        )
    return rows


def _task_bucket(task_items: dict[str, Any] | None, key: str) -> list[dict[str, Any]]:
    if not isinstance(task_items, dict):
        return []
    bucket = task_items.get(key)
    return _normalize_items(bucket if isinstance(bucket, list) else [])


def _merge_findings(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for group in groups:
        for item in group:
            if not isinstance(item, dict):
                continue
            key = (
                str(item.get("severity") or "").upper(),
                str(item.get("title") or "").strip(),
                str(item.get("file") or "").strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result


def _merge_text_flags(*groups: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for raw in group:
            item = str(raw or "").strip()
            if not item or item in seen:
                continue
            seen.add(item)
            result.append(item)
    return result


def _llm_lane_result(llm_reviews: dict[str, Any], lane: str) -> dict[str, Any]:
    review = llm_reviews.get(lane)
    if not isinstance(review, dict):
        return {"lane": lane, "findings": [], "docs_flags": [], "summary": "", "source": ""}
    return review


def build_review_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")

    trigger_kind = str(payload.get("trigger_kind") or "").strip()
    changed_files = normalize_changed_files(payload.get("changed_files"))
    commits = _normalize_items(payload.get("commits"))
    has_recent_commits = bool(payload.get("has_recent_commits")) if "has_recent_commits" in payload else bool(commits)
    route = route_review(
        trigger_kind,
        changed_files=changed_files,
        has_recent_commits=has_recent_commits,
        fix_touches_ui=bool(payload.get("fix_touches_ui")),
        enable_graph=bool(payload.get("enable_graph")),
    )

    tasks = payload.get("tasks") if isinstance(payload.get("tasks"), dict) else {}
    summaries = _project_summary_rows(payload.get("project_summaries"))
    explicit_findings = _normalize_items(payload.get("findings"))
    explicit_docs_flags = [str(item).strip() for item in payload.get("docs_flags") or [] if str(item).strip()]
    code_lane = {"lane": "code-review", "findings": [], "meta": {}}
    docs_lane = {"lane": "docs-review", "docs_flags": [], "meta": {}}
    llm_reviews = payload.get("llm_reviews") if isinstance(payload.get("llm_reviews"), dict) else {}
    llm_code_review = _llm_lane_result(llm_reviews, "code-review")
    llm_docs_review = _llm_lane_result(llm_reviews, "docs-review")
    if route.trigger_kind in {"daily", "code-health"} and route.should_run:
        code_lane = run_code_review_lane(payload)
        docs_lane = run_docs_review_lane(payload)
    bundle = {
        "project": {
            "name": str(payload.get("project_name") or "").strip(),
            "channel_id": str(payload.get("channel_id") or "").strip(),
            "repo_root": str(payload.get("repo_root") or "").strip(),
        },
        "trigger": {
            "kind": route.trigger_kind,
            "card_kind": route.card_kind,
            "lanes": list(route.lanes),
            "should_run": route.should_run,
            "skip_reason": route.skip_reason,
            "reasons": list(route.reasons),
        },
        "projects": summaries,
        "tasks": {
            "active": _task_bucket(tasks, "active"),
            "completed": _task_bucket(tasks, "completed"),
            "blocked": _task_bucket(tasks, "blocked"),
            "stale": _task_bucket(tasks, "stale"),
        },
        "changed_scope": {
            "files": changed_files,
            "file_count": len(changed_files),
            "touches_ui": touches_ui_paths(changed_files),
        },
        "audit": {
            "file_stats": _normalize_items(payload.get("file_stats")),
            "function_stats": _normalize_items(payload.get("function_stats")),
            "import_errors": _normalize_texts(payload.get("import_errors")),
            "reference_errors": _normalize_texts(payload.get("reference_errors")),
            "type_errors": _normalize_texts(payload.get("type_errors")),
            "lint_errors": _normalize_texts(payload.get("lint_errors")),
            "signals": {
                "file_stats_provided": "file_stats" in payload,
                "function_stats_provided": "function_stats" in payload,
                "import_errors_provided": "import_errors" in payload,
                "reference_errors_provided": "reference_errors" in payload,
                "type_errors_provided": "type_errors" in payload,
                "lint_errors_provided": "lint_errors" in payload,
            },
        },
        "commits": commits,
        "findings": _merge_findings(code_lane.get("findings") or [], llm_code_review.get("findings") or [], explicit_findings),
        "docs_flags": _merge_text_flags(docs_lane.get("docs_flags") or [], llm_docs_review.get("docs_flags") or [], explicit_docs_flags),
        "graph": {
            "enabled": route.uses_graph_observe,
            "snapshot_path": str(payload.get("graph_snapshot_path") or "").strip(),
        },
        "lane_results": {
            "code_review": code_lane,
            "docs_review": docs_lane,
            "llm_code_review": llm_code_review,
            "llm_docs_review": llm_docs_review,
        },
    }
    return bundle


def _load_payload(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("payload is required")
    if text.startswith("@"):
        with open(text[1:], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a normalized project-review bundle from JSON input.")
    parser.add_argument("--payload", required=True, help="JSON payload or @path/to/payload.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = _load_payload(args.payload)
    print(json.dumps(build_review_bundle(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
