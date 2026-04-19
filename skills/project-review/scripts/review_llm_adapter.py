#!/usr/bin/env python3
"""Build and normalize GSD-style LLM review requests and verdicts."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


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


def _schema_for_lane(lane: str) -> dict[str, Any]:
    return {
        "lane": lane,
        "summary": "string",
        "findings": [
            {
                "severity": "P0|P1|P2",
                "title": "string",
                "summary": "string",
                "file": "string",
                "evidence": ["string"],
                "suggestion": "string",
                "card_title": "string",
                "card_summary": "string",
            }
        ],
        "docs_flags": ["string"],
        "next_actions": ["string"],
    }


def build_llm_review_request(bundle: dict[str, Any], lane: str) -> dict[str, Any]:
    lane_name = str(lane or "").strip()
    if lane_name not in {"code-review", "docs-review"}:
        raise ValueError(f"Unsupported lane: {lane}")

    lane_results = bundle.get("lane_results") if isinstance(bundle.get("lane_results"), dict) else {}
    lane_payload = lane_results.get("code_review" if lane_name == "code-review" else "docs_review")
    if not isinstance(lane_payload, dict):
        lane_payload = {}

    request = {
        "lane": lane_name,
        "task": "Review the provided evidence and return strict JSON only.",
        "project": bundle.get("project") if isinstance(bundle.get("project"), dict) else {},
        "trigger": bundle.get("trigger") if isinstance(bundle.get("trigger"), dict) else {},
        "changed_scope": bundle.get("changed_scope") if isinstance(bundle.get("changed_scope"), dict) else {},
        "commits": _normalize_items(bundle.get("commits")),
        "candidate_findings": _normalize_items(lane_payload.get("findings") or bundle.get("findings")),
        "candidate_docs_flags": _normalize_texts(lane_payload.get("docs_flags") or bundle.get("docs_flags")),
        "expected_schema": _schema_for_lane(lane_name),
        "instructions": [
            "Judge semantic drift or real risk; do not invent files outside the evidence.",
            "Return JSON only, no markdown.",
            "Only keep findings you can justify from the evidence bundle.",
            "If evidence is insufficient, return an empty findings list and explain uncertainty in summary.",
            "Candidate findings are only hints, not truth. You may discard them after repo inspection.",
            "Prefer user-visible or delivery-blocking risks before generic process issues like missing tests or vague API uncertainty.",
            "All summaries, titles, suggestions, and docs_flags must be written in plain Chinese.",
            "Prefer business-facing phrasing over internal jargon; do not output English-only risk summaries unless the code identifier itself must stay in English.",
            "The top-level `summary` must also be plain Chinese and explain what changed, what may go wrong, and what to do next.",
            "For every finding, `title` and `summary` should still be useful to engineers, but `card_title` and `card_summary` must be suitable for a project manager or business owner reading the card.",
            "`card_title` should be short plain Chinese, ideally within 18 Chinese characters; `card_summary` should say the user or project impact in 1 sentence.",
            "Avoid generic titles like `API 契约未确认` or `缺少测试覆盖` unless no stronger concrete risk can be proven from the repo.",
            "Return 1-3 `next_actions` in plain Chinese that tell the user what to do next.",
            "Each `next_actions` item should be an imperative sentence in plain Chinese, ideally within 18 Chinese characters.",
        ],
    }
    return request


def normalize_llm_review_response(raw: dict[str, Any] | str, expected_lane: str) -> dict[str, Any]:
    payload = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(payload, dict):
        raise ValueError("LLM response must be a dict or JSON object")

    lane = str(payload.get("lane") or expected_lane).strip()
    if lane != expected_lane:
        raise ValueError(f"Lane mismatch: expected {expected_lane}, got {lane}")

    findings: list[dict[str, Any]] = []
    for item in payload.get("findings") or []:
        if not isinstance(item, dict):
            continue
        findings.append(
            {
                "severity": str(item.get("severity") or "P1").upper(),
                "title": str(item.get("title") or "").strip(),
                "summary": str(item.get("summary") or "").strip(),
                "card_title": str(item.get("card_title") or item.get("title") or "").strip(),
                "card_summary": str(item.get("card_summary") or item.get("summary") or "").strip(),
                "file": str(item.get("file") or "").strip(),
                "evidence": _normalize_texts(item.get("evidence")),
                "suggestion": str(item.get("suggestion") or "").strip(),
                "source": "llm-review",
            }
        )

    return {
        "lane": lane,
        "summary": str(payload.get("summary") or "").strip(),
        "findings": findings,
        "docs_flags": _normalize_texts(payload.get("docs_flags")),
        "next_actions": _normalize_texts(payload.get("next_actions")),
        "source": "llm-review",
    }


def _load_json(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("payload is required")
    if text.startswith("@"):
        with open(text[1:], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or normalize project-review LLM review payloads.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    request_parser = subparsers.add_parser("request", help="Build one LLM review request from a bundle.")
    request_parser.add_argument("--payload", required=True, help="Bundle JSON or @path")
    request_parser.add_argument("--lane", required=True, help="code-review or docs-review")

    parse_parser = subparsers.add_parser("parse", help="Normalize one LLM review response.")
    parse_parser.add_argument("--payload", required=True, help="Response JSON or @path")
    parse_parser.add_argument("--lane", required=True, help="Expected lane")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = _load_json(args.payload)
    if args.command == "request":
        print(json.dumps(build_llm_review_request(payload, args.lane), ensure_ascii=False))
        return 0
    if args.command == "parse":
        print(json.dumps(normalize_llm_review_response(payload, args.lane), ensure_ascii=False))
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
