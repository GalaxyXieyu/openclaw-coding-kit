#!/usr/bin/env python3
"""GSD-style reviewer orchestration for project-review."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_review_bundle import build_review_bundle
from review_llm_adapter import build_llm_review_request, normalize_llm_review_response
from review_state_store import (
    default_state_path,
    get_review_by_dedupe_key,
    get_review_by_id,
    load_state,
    stable_json_hash,
    upsert_review_record,
)
from risk_card_builder import build_card_payload

DEFAULT_PROMPT_VERSION = "project-review-reviewer/v1"
LLM_REVIEWABLE_LANES = ("code-review", "docs-review")
PROJECT_REVIEW_SCRIPTS_ROOT = Path(__file__).resolve().parent
PM_SCRIPTS_ROOT = PROJECT_REVIEW_SCRIPTS_ROOT.parents[1] / "pm" / "scripts"


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("payload is required")
    if text.startswith("@"):
        with open(text[1:], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(text)


def _load_pm_runtime_module() -> Any:
    pm_root = str(PM_SCRIPTS_ROOT.resolve())
    if pm_root not in sys.path:
        sys.path.insert(0, pm_root)
    import pm_runtime  # type: ignore

    return pm_runtime


def _normalize_key_part(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return re.sub(r"[\s/:]+", "-", text)


def _select_llm_lanes(bundle: dict[str, Any]) -> list[str]:
    trigger = bundle.get("trigger") if isinstance(bundle.get("trigger"), dict) else {}
    lanes = trigger.get("lanes") if isinstance(trigger.get("lanes"), list) else []
    return [lane for lane in lanes if lane in LLM_REVIEWABLE_LANES]


def _latest_commit_hash(bundle: dict[str, Any]) -> str:
    commits = bundle.get("commits") if isinstance(bundle.get("commits"), list) else []
    if not commits:
        return ""
    latest = commits[0] if isinstance(commits[0], dict) else {}
    return str(latest.get("hash") or "").strip()


def build_dedupe_key(payload: dict[str, Any], bundle: dict[str, Any]) -> str:
    explicit = str(payload.get("dedupe_key") or "").strip()
    if explicit:
        return explicit

    trigger = bundle.get("trigger") if isinstance(bundle.get("trigger"), dict) else {}
    project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
    trigger_kind = str(trigger.get("kind") or "").strip() or str(payload.get("trigger_kind") or "review").strip()
    project_name = _normalize_key_part(project.get("name") or payload.get("project_name") or "project")
    channel_id = _normalize_key_part(project.get("channel_id") or payload.get("channel_id"))

    anchor = ""
    for key in ("review_window_key", "period_key", "period_label", "event_key", "trigger_key"):
        candidate = str(payload.get(key) or "").strip()
        if candidate:
            anchor = candidate
            break
    if not anchor and trigger_kind == "code-health":
        anchor = _latest_commit_hash(bundle)
    if not anchor:
        anchor = stable_json_hash(
            {
                "trigger_kind": trigger_kind,
                "projects": bundle.get("projects"),
                "tasks": bundle.get("tasks"),
                "changed_scope": bundle.get("changed_scope"),
            }
        )[:12]

    parts = [trigger_kind or "review", project_name or "project"]
    if channel_id:
        parts.append(channel_id)
    parts.append(_normalize_key_part(anchor) or stable_json_hash(anchor)[:12])
    return ":".join(part for part in parts if part)


def build_review_id(dedupe_key: str, input_hash: str) -> str:
    return f"RV-{stable_json_hash({'dedupe_key': dedupe_key, 'input_hash': input_hash})[:12]}"


def _review_packets(bundle: dict[str, Any], *, prompt_version: str, model: str) -> list[dict[str, Any]]:
    packets: list[dict[str, Any]] = []
    for lane in _select_llm_lanes(bundle):
        request = build_llm_review_request(bundle, lane)
        packets.append(
            {
                "lane": lane,
                "prompt_version": prompt_version,
                "model": model,
                "request_hash": stable_json_hash(request),
                "request": request,
            }
        )
    return packets


def _record_history(record: dict[str, Any]) -> list[dict[str, Any]]:
    history = record.get("history")
    if isinstance(history, list):
        return history
    return []


def _reviewer_repo_root(payload: dict[str, Any]) -> str:
    return str(payload.get("repo_root") or os.getcwd()).strip() or os.getcwd()


def _build_codex_review_prompt(request: dict[str, Any], *, repo_root: str) -> str:
    lane = str(request.get("lane") or "review").strip()
    schema = request.get("expected_schema") if isinstance(request.get("expected_schema"), dict) else {}
    prompt_parts = [
        "你是 project-review 的 reviewer worker。",
        f"当前 review lane：{lane}。",
        f"仓库根目录：{repo_root}。",
        "这是一张会直接发给业务负责人/项目负责人的健康风险卡，不是给工程师写周报。",
        "你必须优先看真实代码和仓库证据，candidate findings 只是提示，不是真相。",
        "如果现有证据不够，请主动检查当前仓库里的相关文件，再决定要不要保留风险。",
        "优先输出真正会影响用户、交付、状态流转、页面结果、联调验收的风险。",
        "只有在找不到更具体的问题时，才允许输出“缺少测试”“文档没同步”“API 不明确”这类流程型风险。",
        "所有可见字段都必须是中文大白话，不能夹英文总结，也不要写抽象术语和空话。",
        "`summary` 要回答三件事：这次主要改了什么、现在最可能出什么问题、下一步先做什么。",
        "`card_title` 要短，适合直接放卡片里；`card_summary` 要直接说影响，不要复述代码细节。",
        "`next_actions` 必须给 1-3 条可执行动作，每条一句中文祈使句。",
        "如果证据不足，就返回空 findings，并在中文 summary 里明确说明还需要看什么。",
        "输出必须严格是一个 JSON object，不要 markdown，不要额外解释。",
        "Expected JSON schema:",
        json.dumps(schema, ensure_ascii=False, indent=2),
        "Review request:",
        json.dumps(request, ensure_ascii=False, indent=2),
    ]
    return "\n\n".join(prompt_parts)


def _extract_json_object(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("reviewer returned empty output")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        return payload

    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _end = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError(f"reviewer returned non-JSON output: {text[:400]}")


def _run_codex_reviewer_request(
    request: dict[str, Any],
    *,
    repo_root: str,
    model: str,
    timeout_seconds: int,
    thinking: str,
) -> dict[str, Any]:
    runtime = _load_pm_runtime_module()
    prompt = _build_codex_review_prompt(request, repo_root=repo_root)
    result = runtime.run_codex_cli(
        agent_id=model,
        message=prompt,
        cwd=repo_root,
        timeout_seconds=timeout_seconds,
        thinking=thinking,
    )
    payloads = result.get("result", {}).get("payloads") if isinstance(result.get("result"), dict) else []
    first_payload = payloads[0] if isinstance(payloads, list) and payloads else {}
    raw_text = str(first_payload.get("text") or "").strip()
    response = _extract_json_object(raw_text)
    return {
        "lane": str(request.get("lane") or "").strip(),
        "response": response,
        "raw_text": raw_text,
        "backend": str(result.get("backend") or "codex-cli"),
        "meta": result.get("result", {}).get("meta") if isinstance(result.get("result"), dict) else {},
    }


def prepare_review(
    payload: dict[str, Any],
    *,
    state_path: str | Path | None = None,
    review_id: str | None = None,
    now_iso: str | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    model: str = "",
) -> dict[str, Any]:
    base_payload = dict(payload)
    base_payload.pop("llm_reviews", None)

    bundle = build_review_bundle(base_payload)
    llm_requests = _review_packets(bundle, prompt_version=prompt_version, model=model)
    input_hash = stable_json_hash(base_payload)
    request_set_hash = stable_json_hash(
        {
            "prompt_version": prompt_version,
            "model": model,
            "requests": [
                {"lane": item["lane"], "request_hash": item["request_hash"]}
                for item in llm_requests
            ],
        }
    )

    normalized_now = str(now_iso or _now_iso())
    resolved_state_path = Path(state_path or default_state_path()).resolve()
    dedupe_key = build_dedupe_key(base_payload, bundle)
    state = load_state(resolved_state_path)
    existing = get_review_by_dedupe_key(state, dedupe_key)
    if existing is not None:
        same_input = (
            str(existing.get("input_hash") or "") == input_hash
            and str(existing.get("prompt_version") or "") == prompt_version
            and str(existing.get("model") or "") == model
        )
        if same_input:
            return {
                "review_id": str(existing.get("review_id") or "").strip(),
                "dedupe_key": dedupe_key,
                "status": str(existing.get("status") or "").strip(),
                "reused_existing": True,
                "input_hash": input_hash,
                "prompt_version": prompt_version,
                "model": model,
                "state_path": str(resolved_state_path),
                "bundle": existing.get("bundle") if isinstance(existing.get("bundle"), dict) else bundle,
                "card": existing.get("card_preview") if isinstance(existing.get("card_preview"), dict) else build_card_payload(bundle),
                "llm_requests": existing.get("reviewer_requests") if isinstance(existing.get("reviewer_requests"), list) else llm_requests,
                "pending_llm_lanes": existing.get("pending_llm_lanes") if isinstance(existing.get("pending_llm_lanes"), list) else [item["lane"] for item in llm_requests],
            }

    next_review_id = str(review_id or (existing or {}).get("review_id") or build_review_id(dedupe_key, input_hash)).strip()
    llm_lanes = [item["lane"] for item in llm_requests]
    status = "drafted" if bool(bundle.get("trigger", {}).get("should_run")) else "detected"
    record = dict(existing) if isinstance(existing, dict) else {}
    history = _record_history(record)
    history.append(
        {
            "event": "prepared" if not existing else "redrafted",
            "at": normalized_now,
            "input_hash": input_hash,
            "request_set_hash": request_set_hash,
            "lanes": llm_lanes,
        }
    )
    card = build_card_payload(bundle)
    record.update(
        {
            "review_id": next_review_id,
            "dedupe_key": dedupe_key,
            "status": status,
            "created_at": str(record.get("created_at") or normalized_now),
            "updated_at": normalized_now,
            "trigger_kind": str(bundle.get("trigger", {}).get("kind") or "").strip(),
            "card_kind": str(bundle.get("trigger", {}).get("card_kind") or "").strip(),
            "project_name": str(bundle.get("project", {}).get("name") or "").strip(),
            "channel_id": str(bundle.get("project", {}).get("channel_id") or "").strip(),
            "latest_commit_hash": _latest_commit_hash(bundle),
            "input_hash": input_hash,
            "request_set_hash": request_set_hash,
            "prompt_version": prompt_version,
            "model": model,
            "source_payload": base_payload,
            "bundle": bundle,
            "card_preview": card,
            "reviewer_requests": llm_requests,
            "llm_verdict": {},
            "pending_llm_lanes": llm_lanes,
            "llm_ready": not llm_lanes,
            "llm_ready_at": normalized_now if not llm_lanes else "",
            "delivery": {},
            "card_sent": {},
            "sent_at": "",
            "history": history,
        }
    )
    upsert_review_record(resolved_state_path, record)
    return {
        "review_id": next_review_id,
        "dedupe_key": dedupe_key,
        "status": status,
        "reused_existing": False,
        "input_hash": input_hash,
        "prompt_version": prompt_version,
        "model": model,
        "state_path": str(resolved_state_path),
        "bundle": bundle,
        "card": card,
        "llm_requests": llm_requests,
        "pending_llm_lanes": llm_lanes,
    }


def execute_review_with_codex(
    payload: dict[str, Any],
    *,
    state_path: str | Path | None = None,
    review_id: str | None = None,
    now_iso: str | None = None,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    model: str = "codex",
    timeout_seconds: int = 900,
    thinking: str = "high",
) -> dict[str, Any]:
    prepared = prepare_review(
        payload,
        state_path=state_path,
        review_id=review_id,
        now_iso=now_iso,
        prompt_version=prompt_version,
        model=model,
    )
    requests = prepared.get("llm_requests") if isinstance(prepared.get("llm_requests"), list) else []
    if not requests:
        return {
            "review_id": prepared["review_id"],
            "prepared": prepared,
            "reviewer_runs": [],
            "ingested": None,
            "llm_ready": True,
            "pending_llm_lanes": [],
            "state_path": prepared["state_path"],
        }

    repo_root = _reviewer_repo_root(payload)
    reviewer_payload: dict[str, Any] = {}
    reviewer_runs: list[dict[str, Any]] = []
    for item in requests:
        if not isinstance(item, dict):
            continue
        request = item.get("request")
        if not isinstance(request, dict):
            continue
        run = _run_codex_reviewer_request(
            request,
            repo_root=repo_root,
            model=model,
            timeout_seconds=timeout_seconds,
            thinking=thinking,
        )
        lane = str(run.get("lane") or "").strip()
        if not lane:
            continue
        reviewer_payload[lane] = run.get("response")
        reviewer_runs.append(
            {
                "lane": lane,
                "backend": run.get("backend"),
                "meta": run.get("meta"),
                "raw_text": run.get("raw_text"),
            }
        )

    ingested = ingest_review_results(
        prepared["review_id"],
        reviewer_payload,
        state_path=state_path,
        now_iso=now_iso,
        prompt_version=prompt_version,
        model=model,
    )
    return {
        "review_id": prepared["review_id"],
        "prepared": prepared,
        "reviewer_runs": reviewer_runs,
        "ingested": ingested,
        "llm_ready": bool(ingested.get("llm_ready")),
        "pending_llm_lanes": list(ingested.get("pending_llm_lanes") or []),
        "state_path": ingested["state_path"],
    }


def _normalize_raw_reviews(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        if isinstance(payload.get("lane"), str):
            lane = str(payload.get("lane") or "").strip()
            return {lane: payload}

        reviews = payload.get("reviews")
        if isinstance(reviews, list):
            result: dict[str, Any] = {}
            for item in reviews:
                if not isinstance(item, dict):
                    continue
                lane = str(item.get("lane") or "").strip()
                if not lane:
                    continue
                response = item.get("response") if "response" in item else item.get("payload")
                result[lane] = response if response is not None else item
            return result

        result = {
            str(lane).strip(): response
            for lane, response in payload.items()
            if str(lane).strip() in LLM_REVIEWABLE_LANES
        }
        if result:
            return result

    raise ValueError("review payload must include lane-keyed responses")


def ingest_review_results(
    review_id: str,
    reviewer_payload: dict[str, Any],
    *,
    state_path: str | Path | None = None,
    now_iso: str | None = None,
    prompt_version: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    resolved_state_path = Path(state_path or default_state_path()).resolve()
    state = load_state(resolved_state_path)
    record = get_review_by_id(state, review_id)
    if record is None:
        raise KeyError(f"review_id not found: {review_id}")

    source_payload = record.get("source_payload")
    if not isinstance(source_payload, dict):
        raise ValueError("review record is missing source_payload")

    raw_reviews = _normalize_raw_reviews(reviewer_payload)
    request_lanes = [
        str(item.get("lane") or "").strip()
        for item in record.get("reviewer_requests") or []
        if isinstance(item, dict) and str(item.get("lane") or "").strip()
    ]
    normalized_reviews = dict(record.get("llm_verdict") or {})
    for lane, raw in raw_reviews.items():
        expected_lane = lane
        if request_lanes and lane not in request_lanes:
            raise ValueError(f"Unexpected lane for review_id {review_id}: {lane}")
        normalized_reviews[expected_lane] = normalize_llm_review_response(raw, expected_lane)

    merged_payload = dict(source_payload)
    merged_payload["llm_reviews"] = normalized_reviews
    bundle = build_review_bundle(merged_payload)
    card = build_card_payload(bundle)
    pending_lanes = [lane for lane in request_lanes if lane not in normalized_reviews]
    normalized_now = str(now_iso or _now_iso())

    next_record = dict(record)
    history = _record_history(next_record)
    history.append(
        {
            "event": "llm_ingested",
            "at": normalized_now,
            "lanes": sorted(raw_reviews.keys()),
            "pending_lanes": pending_lanes,
        }
    )
    next_record.update(
        {
            "updated_at": normalized_now,
            "prompt_version": str(prompt_version or record.get("prompt_version") or DEFAULT_PROMPT_VERSION),
            "model": str(model or record.get("model") or "").strip(),
            "latest_commit_hash": _latest_commit_hash(bundle),
            "llm_verdict": normalized_reviews,
            "pending_llm_lanes": pending_lanes,
            "llm_ready": not pending_lanes,
            "llm_ready_at": normalized_now if not pending_lanes else "",
            "bundle": bundle,
            "card_preview": card,
            "history": history,
        }
    )
    upsert_review_record(resolved_state_path, next_record)
    return {
        "review_id": review_id,
        "dedupe_key": str(next_record.get("dedupe_key") or "").strip(),
        "status": str(next_record.get("status") or "").strip(),
        "prompt_version": str(next_record.get("prompt_version") or "").strip(),
        "model": str(next_record.get("model") or "").strip(),
        "llm_ready": bool(next_record.get("llm_ready")),
        "pending_llm_lanes": pending_lanes,
        "state_path": str(resolved_state_path),
        "llm_reviews": normalized_reviews,
        "bundle": bundle,
        "card": card,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare or ingest GSD-style project-review reviewer work.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Build reviewer requests and persist draft state.")
    prepare_parser.add_argument("--payload", required=True, help="Review payload JSON or @path")
    prepare_parser.add_argument("--state-path", help="Optional state path. Defaults to .pm/project-review-state.json")
    prepare_parser.add_argument("--review-id", help="Optional explicit review_id")
    prepare_parser.add_argument("--now-iso", help="Optional ISO8601 timestamp")
    prepare_parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION, help="Reviewer prompt version")
    prepare_parser.add_argument("--model", default="", help="Reviewer model label")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest reviewer JSON verdicts and rebuild bundle/card.")
    ingest_parser.add_argument("--review-id", required=True, help="Review record id")
    ingest_parser.add_argument("--payload", required=True, help="Lane keyed reviewer payload JSON or @path")
    ingest_parser.add_argument("--state-path", help="Optional state path. Defaults to .pm/project-review-state.json")
    ingest_parser.add_argument("--now-iso", help="Optional ISO8601 timestamp")
    ingest_parser.add_argument("--prompt-version", help="Reviewer prompt version override")
    ingest_parser.add_argument("--model", help="Reviewer model label override")

    codex_parser = subparsers.add_parser("codex", help="Prepare, run Codex reviewer, then ingest structured verdicts.")
    codex_parser.add_argument("--payload", required=True, help="Review payload JSON or @path")
    codex_parser.add_argument("--state-path", help="Optional state path. Defaults to .pm/project-review-state.json")
    codex_parser.add_argument("--review-id", help="Optional explicit review_id")
    codex_parser.add_argument("--now-iso", help="Optional ISO8601 timestamp")
    codex_parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION, help="Reviewer prompt version")
    codex_parser.add_argument("--model", default="codex", help="Codex model label. Use `codex` to keep CLI default.")
    codex_parser.add_argument("--timeout-seconds", type=int, default=900, help="Per-lane reviewer timeout.")
    codex_parser.add_argument("--thinking", default="high", help="Reviewer thinking label for tracing.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "prepare":
        payload = _load_json(args.payload)
        result = prepare_review(
            payload,
            state_path=args.state_path,
            review_id=args.review_id,
            now_iso=args.now_iso,
            prompt_version=args.prompt_version,
            model=args.model,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if args.command == "ingest":
        payload = _load_json(args.payload)
        result = ingest_review_results(
            args.review_id,
            payload,
            state_path=args.state_path,
            now_iso=args.now_iso,
            prompt_version=args.prompt_version,
            model=args.model,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if args.command == "codex":
        payload = _load_json(args.payload)
        result = execute_review_with_codex(
            payload,
            state_path=args.state_path,
            review_id=args.review_id,
            now_iso=args.now_iso,
            prompt_version=args.prompt_version,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
            thinking=args.thinking,
        )
        print(json.dumps(result, ensure_ascii=False))
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
