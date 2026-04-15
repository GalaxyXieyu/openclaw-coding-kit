#!/usr/bin/env python3
"""Route project-review triggers into internal lanes and card kinds."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass

PROJECT_RETRO_TRIGGERS = {
    "weekly": "weekly_review_card_v1",
    "monthly": "monthly_review_card_v1",
    "event": "event_alert_card_v1",
}
DAILY_REVIEW_TRIGGER = "daily"
CODE_HEALTH_TRIGGER = "code-health"

UI_PREFIXES = (
    "pages/",
    "components/",
    "src/app/",
    "src/pages/",
)
UI_SUFFIXES = (
    ".wxml",
    ".wxss",
    ".tsx",
    ".jsx",
    ".css",
    ".scss",
)


@dataclass(frozen=True)
class ReviewRoute:
    trigger_kind: str
    card_kind: str
    lanes: tuple[str, ...]
    should_run: bool
    requires_commits: bool
    requires_uiux: bool
    uses_graph_observe: bool
    skip_reason: str
    reasons: tuple[str, ...]


def normalize_changed_files(changed_files: list[str] | None) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in changed_files or []:
        item = str(raw or "").strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def touches_ui_paths(changed_files: list[str] | None) -> bool:
    for path in normalize_changed_files(changed_files):
        if path.endswith(UI_SUFFIXES):
            return True
        if any(path.startswith(prefix) for prefix in UI_PREFIXES):
            return True
    return False


def route_review(
    trigger_kind: str,
    *,
    changed_files: list[str] | None = None,
    has_recent_commits: bool = True,
    fix_touches_ui: bool = False,
    enable_graph: bool = False,
) -> ReviewRoute:
    trigger = str(trigger_kind or "").strip().lower()
    reasons: list[str] = []
    normalized_files = normalize_changed_files(changed_files)

    if trigger in PROJECT_RETRO_TRIGGERS:
        lanes = ["project-retro"]
        uses_graph_observe = trigger in {"weekly", "monthly"} and enable_graph
        if uses_graph_observe:
            lanes.append("graph-observe")
            reasons.append("周/月复盘允许补充结构观察。")
        reasons.append("项目复盘走 review/event 卡片。")
        return ReviewRoute(
            trigger_kind=trigger,
            card_kind=PROJECT_RETRO_TRIGGERS[trigger],
            lanes=tuple(lanes),
            should_run=True,
            requires_commits=False,
            requires_uiux=False,
            uses_graph_observe=uses_graph_observe,
            skip_reason="",
            reasons=tuple(reasons),
        )

    if trigger in {DAILY_REVIEW_TRIGGER, CODE_HEALTH_TRIGGER}:
        requires_uiux = fix_touches_ui or touches_ui_paths(normalized_files)
        is_daily_review = trigger == DAILY_REVIEW_TRIGGER
        card_kind = "daily_review_card_v1" if is_daily_review else "code_health_risk_card_v1"
        reasons.append("每日项目回顾先看最近 commit，再补 docs review。" if is_daily_review else "代码健康巡检先看最近 commit，再补 docs review。")
        if requires_uiux:
            reasons.append("命中 UI 路径，需要补 ui-ux-review。")
        if not has_recent_commits:
            return ReviewRoute(
                trigger_kind=trigger,
                card_kind=card_kind,
                lanes=tuple(),
                should_run=False,
                requires_commits=True,
                requires_uiux=requires_uiux,
                uses_graph_observe=False,
                skip_reason="最近 24 小时没有新的 commit。",
                reasons=tuple(reasons),
            )
        lanes = ["code-review", "docs-review"]
        if requires_uiux:
            lanes.append("ui-ux-review")
        return ReviewRoute(
            trigger_kind=trigger,
            card_kind=card_kind,
            lanes=tuple(lanes),
            should_run=True,
            requires_commits=True,
            requires_uiux=requires_uiux,
            uses_graph_observe=False,
            skip_reason="",
            reasons=tuple(reasons),
        )

    raise ValueError(f"Unsupported trigger_kind: {trigger_kind}")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route project-review triggers into internal lanes.")
    parser.add_argument("--trigger-kind", required=True, help="daily, weekly, monthly, event, or code-health")
    parser.add_argument("--changed-file", action="append", dest="changed_files", default=[], help="Changed file path.")
    parser.add_argument("--no-recent-commits", action="store_true", help="Mark the review window as having no commits.")
    parser.add_argument("--fix-touches-ui", action="store_true", help="Force ui-ux-review after fix flow.")
    parser.add_argument("--enable-graph", action="store_true", help="Enable graph-observe for weekly/monthly routes.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    route = route_review(
        args.trigger_kind,
        changed_files=args.changed_files,
        has_recent_commits=not args.no_recent_commits,
        fix_touches_ui=args.fix_touches_ui,
        enable_graph=args.enable_graph,
    )
    if args.json:
        print(json.dumps(asdict(route), ensure_ascii=False))
    else:
        print(route.card_kind)
        print(",".join(route.lanes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
