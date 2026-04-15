#!/usr/bin/env python3
"""Guard rails for project-review plain-language summaries."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass

BANNED_TERMS = (
    "闭环",
    "赋能",
    "沉淀",
    "对齐",
    "拉通",
    "抓手",
    "协同",
    "颗粒度",
    "方案化",
    "业务侧",
    "链路",
    "驱动",
    "抽象能力",
    "体系化",
    "方法论",
)

DONE_CUES = ("做了", "改了", "补了", "处理了", "完成了", "推进了")
PENDING_CUES = ("还差", "还没做", "还没动", "未做", "没做", "卡在", "待做")
NEXT_CUES = ("下一步", "接下来", "先做", "先看", "先补")

SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    issues: tuple[str, ...]
    summary: str


def normalize_fragment(text: str) -> str:
    cleaned = SPACE_RE.sub("", str(text or "").strip())
    return cleaned.strip("，。；、")


def contains_banned_terms(text: str) -> list[str]:
    content = str(text or "")
    return [term for term in BANNED_TERMS if term in content]


def has_three_part_shape(text: str) -> bool:
    content = str(text or "")
    has_done = any(cue in content for cue in DONE_CUES)
    has_pending = any(cue in content for cue in PENDING_CUES)
    has_next = any(cue in content for cue in NEXT_CUES)
    return has_done and has_pending and has_next


def _render_summary(project: str, done: str, pending: str, next_step: str, *, include_project: bool) -> str:
    prefix = project if include_project and project else ""
    return f"{prefix}做了{done}，还差{pending}，下一步先{next_step}。"


def _shrink_fragment(text: str) -> str:
    if len(text) <= 1:
        return text
    if text.endswith("…"):
        core = text[:-1]
        if len(core) <= 1:
            return text
        return core[:-1] + "…"
    return text[:-1] + "…"


def _fit_summary(project: str, done: str, pending: str, next_step: str, limit: int) -> str:
    parts = [done, pending, next_step]
    summary = _render_summary(project, parts[0], parts[1], parts[2], include_project=bool(project))
    while len(summary) > limit and any(len(part) > 1 for part in parts):
        index = max(range(len(parts)), key=lambda idx: len(parts[idx]))
        parts[index] = _shrink_fragment(parts[index])
        summary = _render_summary(project, parts[0], parts[1], parts[2], include_project=bool(project))
    return summary


def build_project_summary(project: str, done: str, pending: str, next_step: str, *, limit: int = 50) -> str:
    project_name = normalize_fragment(project)
    done_text = normalize_fragment(done)
    pending_text = normalize_fragment(pending)
    next_text = normalize_fragment(next_step)

    if not done_text or not pending_text or not next_text:
        raise ValueError("done, pending, and next_step are required")

    candidates = [
        _render_summary(project_name, done_text, pending_text, next_text, include_project=bool(project_name)),
        _render_summary("", done_text, pending_text, next_text, include_project=False),
        _fit_summary(project_name, done_text, pending_text, next_text, limit),
        _fit_summary("", done_text, pending_text, next_text, limit),
    ]
    for candidate in candidates:
        if len(candidate) <= limit:
            return candidate
    return candidates[-1][:limit]


def validate_project_summary(text: str, *, limit: int = 50) -> ValidationResult:
    summary = str(text or "").strip()
    issues: list[str] = []

    if not summary:
        issues.append("摘要不能为空")
    if len(summary) > limit:
        issues.append(f"摘要超过 {limit} 字")
    banned = contains_banned_terms(summary)
    if banned:
        issues.append("包含禁用词：" + "、".join(banned))
    if summary and not has_three_part_shape(summary):
        issues.append("缺少“已做 / 未做 / 下一步”三段信息")

    return ValidationResult(ok=not issues, issues=tuple(issues), summary=summary)


def _build_command(args: argparse.Namespace) -> int:
    summary = build_project_summary(
        args.project,
        args.done,
        args.pending,
        args.next_step,
        limit=args.limit,
    )
    if args.as_json:
        print(json.dumps({"summary": summary, "ok": validate_project_summary(summary, limit=args.limit).ok}, ensure_ascii=False))
    else:
        print(summary)
    return 0


def _check_command(args: argparse.Namespace) -> int:
    result = validate_project_summary(args.text, limit=args.limit)
    if args.as_json:
        print(json.dumps({"ok": result.ok, "issues": list(result.issues), "summary": result.summary}, ensure_ascii=False))
    else:
        if result.ok:
            print("OK")
        else:
            for issue in result.issues:
                print(issue)
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build or validate project-review summaries.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build a plain-language project summary.")
    build_parser.add_argument("--project", default="", help="Project name.")
    build_parser.add_argument("--done", required=True, help="What was done.")
    build_parser.add_argument("--pending", required=True, help="What is still pending.")
    build_parser.add_argument("--next", dest="next_step", required=True, help="What to do next.")
    build_parser.add_argument("--limit", type=int, default=50, help="Maximum summary length.")
    build_parser.add_argument("--json", dest="as_json", action="store_true", help="Print JSON output.")
    build_parser.set_defaults(func=_build_command)

    check_parser = subparsers.add_parser("check", help="Validate an existing summary.")
    check_parser.add_argument("--text", required=True, help="Summary text to validate.")
    check_parser.add_argument("--limit", type=int, default=50, help="Maximum summary length.")
    check_parser.add_argument("--json", dest="as_json", action="store_true", help="Print JSON output.")
    check_parser.set_defaults(func=_check_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
