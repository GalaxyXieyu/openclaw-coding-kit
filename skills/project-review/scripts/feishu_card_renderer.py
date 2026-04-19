#!/usr/bin/env python3
"""Render project-review records into Feishu interactive cards."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

DOC_FLAG_LABELS = {
    "canonical-miniapp-route-drift": "页面路由说明和真实跳转可能对不上。",
    "missing-guiquan-supply-business-flows": "供销业务流程说明还没补齐。",
}

ACTION_STYLE = {
    "开始修复": "primary",
    "查看详情": "default",
    "明天再看": "default",
    "忽略这次": "danger",
    "打开任务列表": "primary",
    "本周归档": "default",
    "三天后再提醒": "default",
    "去看任务": "primary",
    "今天处理": "primary",
    "一周后再提醒": "default",
    "这次不用提醒": "danger",
}
CHECK_STATUS_PREFIX = {
    "ok": "通过",
    "warn": "关注",
    "risk": "异常",
    "unknown": "待补检查",
}


def _normalize_preview(record: dict[str, Any]) -> dict[str, Any]:
    preview = record.get("card_preview")
    return preview if isinstance(preview, dict) else {}


def _normalize_bundle(record: dict[str, Any]) -> dict[str, Any]:
    bundle = record.get("bundle")
    return bundle if isinstance(bundle, dict) else {}


def _normalize_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items or []:
        if isinstance(item, dict):
            result.append(item)
    return result


def _text(value: Any) -> str:
    return str(value or "").strip()


def _fmt_timestamp(raw: Any) -> str:
    value = _text(raw)
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).strftime("%m-%d %H:%M")
    except ValueError:
        return value


def _is_mostly_ascii(text: str) -> bool:
    raw = _text(text)
    if not raw:
        return False
    ascii_count = sum(1 for char in raw if ord(char) < 128)
    return ascii_count >= max(12, int(len(raw) * 0.6))


def _humanize_docs_flag(flag: str) -> str:
    text = _text(flag)
    if not text:
        return ""
    return DOC_FLAG_LABELS.get(text, text)


def _risk_display_title(item: dict[str, Any]) -> str:
    text = _text(item.get("card_title") or item.get("title"))
    if not text:
        return "需要进一步确认的风险"
    return text


def _risk_display_summary(item: dict[str, Any]) -> str:
    summary = _text(item.get("card_summary") or item.get("summary"))
    if summary and not _is_mostly_ascii(summary):
        return summary
    suggestion = _text(item.get("suggestion"))
    if suggestion and not _is_mostly_ascii(suggestion):
        return suggestion
    return summary or "这条风险需要再核对一次业务影响和用户可见结果。"


def _topic_summary(record: dict[str, Any]) -> str:
    bundle = _normalize_bundle(record)
    changed_scope = bundle.get("changed_scope") if isinstance(bundle.get("changed_scope"), dict) else {}
    files = [str(item).strip() for item in (changed_scope.get("files") or []) if str(item).strip()]
    commit_count = len(_normalize_items(bundle.get("commits")))
    topics: list[str] = []
    if any("/supply" in path or "supply-" in path for path in files):
        topics.append("供销")
    if any("/payments" in path or "payment" in path for path in files):
        topics.append("支付")
    if any("community" in path for path in files):
        topics.append("社区")
    if any("styles/" in path or path.endswith(".css") for path in files):
        topics.append("页面样式")
    if any(path.startswith("docs/") or path.endswith(".md") for path in files):
        topics.append("文档")
    if not topics:
        return f"最近 {commit_count} 次改动，主要在功能代码和文档。".strip()
    ordered = []
    for item in topics:
        if item not in ordered:
            ordered.append(item)
    label = "、".join(ordered[:4])
    return f"最近 {commit_count} 次改动，主要碰了{label}。".strip()


def _how_to_fix_lines(record: dict[str, Any]) -> list[str]:
    preview = _normalize_preview(record)
    next_actions = [_text(item) for item in (preview.get("next_actions") or []) if _text(item)]
    if next_actions:
        return next_actions[:3]

    risks = _normalize_items(preview.get("top_risks"))
    suggestions = []
    for item in risks:
        suggestion = _text(item.get("suggestion"))
        if suggestion and not _is_mostly_ascii(suggestion):
            suggestions.append(suggestion)
    suggestions.extend(
        _humanize_docs_flag(str(item))
        for item in preview.get("docs_flags") or []
        if _humanize_docs_flag(str(item))
    )
    suggestions = [item for item in suggestions if item]
    if suggestions:
        return suggestions[:3]
    return ["先处理最影响用户的风险，再补测试和文档。"]


def _build_action_buttons(record: dict[str, Any]) -> list[dict[str, Any]]:
    preview = _normalize_preview(record)
    actions = [str(item).strip() for item in (preview.get("actions") or []) if str(item).strip()]
    review_id = _text(record.get("review_id"))
    card_kind = _text(record.get("card_kind")) or _text(preview.get("card_kind"))
    buttons: list[dict[str, Any]] = []
    for label in actions[:4]:
        buttons.append(
            {
                "tag": "button",
                "type": ACTION_STYLE.get(label, "default"),
                "text": {"tag": "plain_text", "content": label},
                "value": {
                    "review_id": review_id,
                    "card_kind": card_kind,
                    "action": label,
                },
            }
        )
    return buttons


def _review_template(card_kind: str) -> str:
    return {
        "daily_review_card_v1": "blue",
        "weekly_review_card_v1": "blue",
        "weekly_digest_card_v1": "blue",
        "monthly_review_card_v1": "indigo",
        "event_alert_card_v1": "orange",
    }.get(card_kind, "blue")


def _code_health_template(preview: dict[str, Any]) -> str:
    counts = preview.get("severity_counts") if isinstance(preview.get("severity_counts"), dict) else {}
    if int(counts.get("P0") or 0) > 0:
        return "red"
    if int(counts.get("P1") or 0) > 0:
        return "orange"
    return "blue"


def _render_review_body(record: dict[str, Any]) -> str:
    preview = _normalize_preview(record)
    bundle = _normalize_bundle(record)
    project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
    projects = _normalize_items(preview.get("projects"))
    stats = preview.get("stats") if isinstance(preview.get("stats"), dict) else {}

    lines: list[str] = []
    project_name = _text(project.get("name"))
    if project_name:
        lines.append(f"**项目组** {project_name}")

    if projects:
        for item in projects[:6]:
            name = _text(item.get("project"))
            status = _text(item.get("status"))
            summary = _text(item.get("summary"))
            heading = f"**{name or '项目'}**"
            if status:
                heading = f"{heading} · {status}"
            lines.extend(["", heading])
            if summary:
                lines.append(summary)
    else:
        lines.extend(["", "这期还没有可推送的项目摘要。"])

    completed = int(stats.get("completed_count") or 0)
    active = int(stats.get("active_count") or 0)
    blocked = int(stats.get("blocked_count") or 0)
    stale = int(stats.get("stale_count") or 0)
    if any((completed, active, blocked, stale)):
        lines.extend(
            [
                "",
                f"<font color='grey'>本期完成 {completed} 项，推进中 {active} 项，阻塞 {blocked} 项，待跟进 {stale} 项。</font>",
            ]
        )

    next_steps = [_text(item.get("next_step")) for item in projects if _text(item.get("next_step"))]
    if next_steps:
        lines.extend(["", f"**下步先看**：{'；'.join(next_steps[:3])}"])

    review_id = _text(record.get("review_id"))
    updated_at = _fmt_timestamp(record.get("updated_at"))
    meta = " · ".join(part for part in (f"review_id `{review_id}`" if review_id else "", updated_at) if part)
    if meta:
        lines.extend(["", f"<font color='grey'>{meta}</font>"])

    return "\n".join(line for line in lines if line is not None).strip()


def _render_code_health_body(record: dict[str, Any]) -> str:
    preview = _normalize_preview(record)
    bundle = _normalize_bundle(record)
    project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
    counts = preview.get("severity_counts") if isinstance(preview.get("severity_counts"), dict) else {}
    changed_scope = preview.get("changed_scope") if isinstance(preview.get("changed_scope"), dict) else {}
    top_risks = _normalize_items(preview.get("top_risks"))
    docs_flags = [_humanize_docs_flag(str(item)) for item in preview.get("docs_flags") or [] if _humanize_docs_flag(str(item))]
    doc_updates = _normalize_items(preview.get("doc_updates"))

    lines: list[str] = []
    project_name = _text(project.get("name"))
    if project_name:
        lines.append(f"**项目** {project_name}")

    p0 = int(counts.get("P0") or 0)
    p1 = int(counts.get("P1") or 0)
    p2 = int(counts.get("P2") or 0)
    lines.extend(["", f"<font color='orange'>P0 {p0} · P1 {p1} · P2 {p2}</font>"])

    lines.extend(["", f"**这次主要动了什么**：{_topic_summary(record)}"])

    if top_risks:
        lines.extend(["", "**现在最要紧的 3 件事**"])
        for item in top_risks[:3]:
            severity = _text(item.get("severity")) or "P2"
            title = _risk_display_title(item)
            summary = _risk_display_summary(item)
            file_path = _text(item.get("file"))
            lines.append(f"- [{severity}] {title}")
            if summary:
                lines.append(f"  {summary}")
            if file_path:
                lines.append(f"  <font color='grey'>{file_path}</font>")

    if docs_flags:
        lines.extend(["", "**还要补的说明**"])
        for item in docs_flags[:3]:
            lines.append(f"- {item}")

    if doc_updates:
        lines.extend(["", "**这次文档主要改了什么**"])
        for item in doc_updates[:3]:
            summary = _text(item.get("summary"))
            path = _text(item.get("path"))
            if summary:
                line = f"- {summary}"
                if path:
                    line += f" <font color='grey'>({path})</font>"
                lines.append(line)

    how_to_fix = _how_to_fix_lines(record)
    if how_to_fix:
        lines.extend(["", "**建议怎么做**"])
        for index, item in enumerate(how_to_fix, start=1):
            lines.append(f"{index}. {item}")

    if bool(changed_scope.get("requires_uiux")):
        lines.extend(["", "这次改动碰到页面，修完后最好补一轮页面冒烟检查。"])

    review_id = _text(record.get("review_id"))
    updated_at = _fmt_timestamp(record.get("updated_at"))
    meta = " · ".join(part for part in (f"review_id `{review_id}`" if review_id else "", updated_at) if part)
    if meta:
        lines.extend(["", f"<font color='grey'>{meta}</font>"])

    return "\n".join(line for line in lines if line is not None).strip()


def _render_daily_review_body(record: dict[str, Any]) -> str:
    preview = _normalize_preview(record)
    bundle = _normalize_bundle(record)
    project = bundle.get("project") if isinstance(bundle.get("project"), dict) else {}
    changed_scope = preview.get("changed_scope") if isinstance(preview.get("changed_scope"), dict) else {}
    commit_window = preview.get("commit_window") if isinstance(preview.get("commit_window"), dict) else {}
    top_risks = _normalize_items(preview.get("focus_findings") or preview.get("top_risks"))
    docs_flags = [_humanize_docs_flag(str(item)) for item in preview.get("docs_flags") or [] if _humanize_docs_flag(str(item))]
    doc_updates = _normalize_items(preview.get("doc_updates"))
    audit_checks = _normalize_items(preview.get("audit_checks"))
    today_updates = [_text(item) for item in (preview.get("today_updates") or []) if _text(item)]
    file_highlights = [_text(item) for item in (preview.get("file_highlights") or []) if _text(item)]
    review_summary = _text(preview.get("review_summary"))
    automation_updates = [_text(item) for item in (preview.get("automation_updates") or []) if _text(item)]

    lines: list[str] = []
    project_name = _text(project.get("name"))
    if project_name:
        lines.append(f"**项目** {project_name}")

    if review_summary:
        lines.extend(["", review_summary])

    if today_updates:
        lines.extend(["", "**今天具体推进**"])
        for index, item in enumerate(today_updates[:3], start=1):
            lines.append(f"{index}. {item}")
    else:
        lines.extend(["", f"**今天主要看了什么**：{_topic_summary(record)}"])

    if file_highlights:
        lines.extend(["", "**今天实际改到的文件**"])
        for item in file_highlights[:6]:
            lines.append(f"- `{item}`")

    if audit_checks:
        lines.extend(["", "**审核结果**"])
        for item in audit_checks[:4]:
            label = _text(item.get("label")) or "检查项"
            detail = _text(item.get("detail"))
            status = CHECK_STATUS_PREFIX.get(_text(item.get("status")).lower(), "检查")
            lines.append(f"- {label}：{status}。{detail}")

    if doc_updates:
        lines.extend(["", "**今天文档主要更新了什么**"])
        for item in doc_updates[:3]:
            summary = _text(item.get("summary"))
            path = _text(item.get("path"))
            if summary:
                line = f"- {summary}"
                if path:
                    line += f" <font color='grey'>({path})</font>"
                lines.append(line)

    if top_risks:
        lines.extend(["", "**最值得看的问题**"])
        for index, item in enumerate(top_risks[:3], start=1):
            title = _risk_display_title(item)
            summary = _risk_display_summary(item)
            file_path = _text(item.get("file"))
            lines.append(f"{index}. {title}")
            if summary:
                lines.append(f"   {summary}")
            if file_path:
                lines.append(f"   <font color='grey'>{file_path}</font>")
    elif docs_flags:
        lines.extend(["", "**文档/规则待同步**"])
        for item in docs_flags[:3]:
            lines.append(f"- {item}")

    how_to_fix = _how_to_fix_lines(record)
    if how_to_fix:
        lines.extend(["", "**下一步**"])
        for index, item in enumerate(how_to_fix, start=1):
            lines.append(f"{index}. {item}")

    if automation_updates:
        lines.extend(["", "**自动处理**"])
        for item in automation_updates[:4]:
            lines.append(f"- {item}")

    latest_subject = _text(commit_window.get("latest_subject"))
    if latest_subject and not today_updates:
        lines.append(f"<font color='grey'>最新提交：{latest_subject}</font>")

    if bool(changed_scope.get("requires_uiux")):
        lines.extend(["", "这次改动碰到页面，修完后最好补一轮页面冒烟检查。"])

    review_id = _text(record.get("review_id"))
    updated_at = _fmt_timestamp(record.get("updated_at"))
    meta = " · ".join(part for part in (f"review_id `{review_id}`" if review_id else "", updated_at) if part)
    if meta:
        lines.extend(["", f"<font color='grey'>{meta}</font>"])

    return "\n".join(line for line in lines if line is not None).strip()


def build_feishu_card(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("record must be a dict")

    preview = _normalize_preview(record)
    card_kind = _text(record.get("card_kind")) or _text(preview.get("card_kind"))
    title = _text(preview.get("title")) or "项目回顾"

    if card_kind == "code_health_risk_card_v1":
        template = _code_health_template(preview)
        body = _render_code_health_body(record)
    elif card_kind == "daily_review_card_v1":
        template = _code_health_template(preview)
        body = _render_daily_review_body(record)
    else:
        template = _review_template(card_kind)
        body = _render_review_body(record)

    elements: list[dict[str, Any]] = [
        {
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": body or "暂无可展示内容。",
            },
        }
    ]
    buttons = _build_action_buttons(record)
    if buttons:
        elements.extend(
            [
                {"tag": "hr"},
                {"tag": "action", "actions": buttons},
            ]
        )

    return {
        "config": {
            "wide_screen_mode": True,
            "enable_forward": True,
            "update_multi": True,
        },
        "header": {
            "template": template,
            "title": {
                "tag": "plain_text",
                "content": title,
            },
        },
        "elements": elements,
    }


def _load_record(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("record is required")
    if text.startswith("@"):
        with open(text[1:], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Render a project-review record into a Feishu card payload.")
    parser.add_argument("--record", required=True, help="JSON record or @path/to/record.json")
    args = parser.parse_args(argv)
    card = build_feishu_card(_load_record(args.record))
    print(json.dumps(card, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
