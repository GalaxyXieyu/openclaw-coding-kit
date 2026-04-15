#!/usr/bin/env python3
"""Route project-review card actions into normalized callback decisions."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Callable

from review_state_store import append_history, update_review_status

ACTION_ALIASES = {
    "打开任务列表": "open_tasks",
    "本周归档": "archive",
    "三天后再提醒": "snooze_3d",
    "查看本月详情": "view_details",
    "本月归档": "archive",
    "去看任务": "open_tasks",
    "今天处理": "acknowledge",
    "一周后再提醒": "snooze_7d",
    "这次不用提醒": "archive",
    "开始修复": "fix_now",
    "查看详情": "view_details",
    "明天再看": "snooze_1d",
    "忽略这次": "archive",
}

ALLOWED_ACTIONS = {
    "weekly_review_card_v1": {"open_tasks", "archive", "snooze_3d"},
    "weekly_digest_card_v1": {"open_tasks", "archive", "snooze_3d"},
    "monthly_review_card_v1": {"open_tasks", "view_details", "archive"},
    "event_alert_card_v1": {"open_tasks", "acknowledge", "snooze_7d", "archive"},
    "code_health_risk_card_v1": {"fix_now", "view_details", "snooze_1d", "archive"},
}


@dataclass(frozen=True)
class CallbackDecision:
    action_id: str
    state_changed: bool
    next_state: str
    snooze_until: str
    should_write_pm: bool
    writeback_kind: str
    should_trigger_fix: bool
    should_open_link: bool
    reason: str


FixExecutorFn = Callable[..., dict[str, Any]]


def normalize_action(action: str) -> str:
    text = str(action or "").strip()
    return ACTION_ALIASES.get(text, text)


def _plus_days(now_iso: str, days: int) -> str:
    now = datetime.fromisoformat(now_iso)
    return (now + timedelta(days=days)).isoformat()


def route_callback_action(card_kind: str, action: str, *, now_iso: str) -> CallbackDecision:
    action_id = normalize_action(action)
    allowed = ALLOWED_ACTIONS.get(str(card_kind or "").strip(), set())
    if action_id not in allowed:
        raise ValueError(f"Unsupported action for {card_kind}: {action}")

    if action_id == "open_tasks":
        return CallbackDecision(action_id, False, "", "", False, "", False, True, "仅记录点击并跳转。")
    if action_id == "view_details":
        return CallbackDecision(action_id, False, "", "", False, "", False, True, "仅记录点击并查看详情。")
    if action_id == "archive":
        return CallbackDecision(action_id, True, "archived", "", False, "", False, False, "归档当前 review。")
    if action_id == "acknowledge":
        return CallbackDecision(action_id, True, "acked", "", True, "acknowledge", False, False, "写回 PM 表示已处理。")
    if action_id == "fix_now":
        return CallbackDecision(action_id, True, "acked", "", True, "fix_task", True, False, "创建修复任务并进入修复流。")
    if action_id == "snooze_1d":
        return CallbackDecision(action_id, True, "snoozed", _plus_days(now_iso, 1), False, "", False, False, "一天后再提醒。")
    if action_id == "snooze_3d":
        return CallbackDecision(action_id, True, "snoozed", _plus_days(now_iso, 3), False, "", False, False, "三天后再提醒。")
    if action_id == "snooze_7d":
        return CallbackDecision(action_id, True, "snoozed", _plus_days(now_iso, 7), False, "", False, False, "一周后再提醒。")
    raise ValueError(f"Unhandled action: {action}")


def apply_callback_action(
    state_path: str,
    *,
    review_id: str,
    card_kind: str,
    action: str,
    now_iso: str,
    run_fix_executor_fn: FixExecutorFn | None = None,
    fix_executor_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = route_callback_action(card_kind, action, now_iso=now_iso)
    if decision.state_changed:
        record = update_review_status(
            state_path,
            review_id,
            status=decision.next_state,
            updated_at=now_iso,
            extra={"snooze_until": decision.snooze_until} if decision.snooze_until else None,
        )
    else:
        record = append_history(
            state_path,
            review_id,
            {"event": "callback_clicked", "action": decision.action_id, "at": now_iso},
        )
    fix_execution = None
    if decision.should_trigger_fix:
        executor = run_fix_executor_fn
        if executor is None:
            from fix_executor import execute_fix_flow

            executor = execute_fix_flow
        fix_execution = executor(
            review_id,
            state_path=state_path,
            now_iso=now_iso,
            **(fix_executor_kwargs or {}),
        )
    return {"decision": asdict(decision), "record": record, "fix_execution": fix_execution}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Route one project-review callback action.")
    parser.add_argument("--card-kind", required=True, help="Card kind.")
    parser.add_argument("--action", required=True, help="Action id or label.")
    parser.add_argument("--now-iso", required=True, help="Current ISO timestamp.")
    parser.add_argument("--state-path", help="Optional state file path.")
    parser.add_argument("--review-id", help="Required when --state-path is provided.")
    parser.add_argument("--no-auto-fix", action="store_true", help="Do not trigger fix_executor for fix_now actions.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.state_path:
        if not args.review_id:
            raise ValueError("--review-id is required with --state-path")
        result = apply_callback_action(
            args.state_path,
            review_id=args.review_id,
            card_kind=args.card_kind,
            action=args.action,
            now_iso=args.now_iso,
            fix_executor_kwargs={"auto_run": not args.no_auto_fix},
        )
    else:
        result = asdict(route_callback_action(args.card_kind, args.action, now_iso=args.now_iso))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
