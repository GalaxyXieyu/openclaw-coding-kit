#!/usr/bin/env python3
"""Deterministic docs-review lane for project-review."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

DOC_PREFIXES = ("docs/", "doc/", "plan/", ".planning/")
DOC_FILES = ("README.md", "README.zh-CN.md", "AGENTS.md")
TEST_MARKERS = ("test_", "_test.", ".spec.", ".test.", "tests/", "__tests__/")


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
    text = str(path or "")
    return text.startswith(DOC_PREFIXES) or text.endswith(".md") or text in DOC_FILES


def _is_test_file(path: str) -> bool:
    text = str(path or "")
    return any(marker in text for marker in TEST_MARKERS)


def _is_code_like(path: str) -> bool:
    text = str(path or "")
    return not _is_doc_file(text) and not _is_test_file(text)


def run_docs_review_lane(payload: dict[str, Any]) -> dict[str, Any]:
    changed_files = _normalize_paths(payload.get("changed_files"))
    stale_doc_candidates = _normalize_texts(payload.get("stale_doc_candidates"))
    duplicate_tool_candidates = _normalize_texts(payload.get("duplicate_tool_candidates"))
    explicit_flags = _normalize_texts(payload.get("docs_flags"))

    code_changed = any(_is_code_like(path) for path in changed_files)
    docs_changed = any(_is_doc_file(path) for path in changed_files)
    agents_changed = any(path.endswith("AGENTS.md") or path == "AGENTS.md" for path in changed_files)
    repo_has_agents = payload.get("repo_has_agents")
    flags: list[str] = []

    if code_changed and not docs_changed:
        flags.append("代码改了，但没看到 docs 更新。")

    if repo_has_agents is False:
        flags.append("仓库还没有 AGENTS.md。")
    elif bool(payload.get("agent_sync_required")) and not agents_changed:
        flags.append("AGENTS.md 可能没同步。")

    for item in stale_doc_candidates[:3]:
        flags.append(f"过期文档候选：{item}")

    for item in duplicate_tool_candidates[:3]:
        flags.append(f"工具可能重复：{item}")

    flags.extend(explicit_flags)
    return {
        "lane": "docs-review",
        "docs_flags": _normalize_texts(flags),
        "meta": {
            "code_changed": code_changed,
            "docs_changed": docs_changed,
            "agents_changed": agents_changed,
        },
    }


def _load_payload(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("payload is required")
    if text.startswith("@"):
        with open(text[1:], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the project-review docs-review lane.")
    parser.add_argument("--payload", required=True, help="JSON payload or @path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = _load_payload(args.payload)
    print(json.dumps(run_docs_review_lane(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
