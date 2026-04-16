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
MAX_FILE_REFS = 6
GENERIC_FILE_NAMES = {
    "readme.md",
    "agents.md",
    "skill.md",
    "index.ts",
    "index.tsx",
    "index.js",
    "index.jsx",
    "main.py",
    "__init__.py",
}
CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs", ".kt")
TEST_MARKERS = ("test_", "_test.", ".spec.", ".test.", "tests/", "__tests__/")
ASSET_SUFFIXES = (".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp")


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


def _short_file_name(path: str) -> str:
    text = _text(path)
    if not text:
        return ""
    parts = [item for item in text.split("/") if item]
    if not parts:
        return text
    if text.endswith("/"):
        return f"{parts[-1]}/"
    if len(parts) >= 2 and parts[-1].lower() in GENERIC_FILE_NAMES:
        return "/".join(parts[-2:])
    return parts[-1]


def _register_file_ref(path: str, refs: dict[str, str], ordered: list[str]) -> str:
    text = _text(path)
    if not text:
        return ""
    if text in refs:
        return refs[text]
    if len(ordered) >= MAX_FILE_REFS:
        return ""
    marker = f"F{len(ordered) + 1}"
    refs[text] = marker
    ordered.append(text)
    return marker


def _file_tag(path: str, refs: dict[str, str], ordered: list[str]) -> str:
    marker = _register_file_ref(path, refs, ordered)
    label = _short_file_name(path)
    if marker and label:
        return f"[{marker}] `{label}`"
    if marker:
        return f"[{marker}]"
    return f"`{label}`" if label else ""


def _file_ref_suffix(path: str, refs: dict[str, str], ordered: list[str]) -> str:
    marker = _register_file_ref(path, refs, ordered)
    return f" [{marker}]" if marker else ""


def _path_category(path: str) -> str:
    text = _text(path).lower()
    if not text:
        return "其他"
    if text.startswith("docs/") or text.endswith(".md"):
        return "文档"
    if any(marker in text for marker in TEST_MARKERS):
        return "测试"
    if text.endswith(CODE_SUFFIXES):
        return "代码"
    if text.endswith((".json", ".yaml", ".yml", ".toml", ".ini", ".lock")):
        return "配置"
    if text.endswith(ASSET_SUFFIXES):
        return "资源"
    return "其他"


def _file_scope_summary(paths: list[str]) -> str:
    rows = [_text(item) for item in paths if _text(item)]
    if not rows:
        return ""
    counts: dict[str, int] = {}
    for path in rows:
        label = _path_category(path)
        counts[label] = counts.get(label, 0) + 1
    ordered_labels = ["文档", "代码", "测试", "配置", "资源", "其他"]
    parts = [f"{label} {counts[label]} 个" for label in ordered_labels if counts.get(label)]
    return f"共 {len(rows)} 个文件，" + "、".join(parts[:4]) + "。"


def _render_file_index_lines(ordered: list[str], refs: dict[str, str]) -> list[str]:
    if not ordered:
        return []
    entries: list[str] = []
    for path in ordered:
        marker = refs.get(path)
        if not marker:
            continue
        label = _short_file_name(path)
        entries.append(f"[{marker}] `{label}`" if label else f"[{marker}]")
    if not entries:
        return []
    lines = ["**文件索引**"]
    chunk_size = 3
    for index in range(0, len(entries), chunk_size):
        lines.append(f"<font color='grey'>{' · '.join(entries[index:index + chunk_size])}</font>")
    return lines


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
    file_refs: dict[str, str] = {}
    file_ref_order: list[str] = []

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
            ref_tag = _file_ref_suffix(file_path, file_refs, file_ref_order)
            lines.append(f"- [{severity}] {title}{ref_tag}")
            if summary:
                lines.append(f"  {summary}")

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
                tag = _file_tag(path, file_refs, file_ref_order)
                if tag:
                    line += f" {tag}"
                lines.append(line)

    how_to_fix = _how_to_fix_lines(record)
    if how_to_fix:
        lines.extend(["", "**建议怎么做**"])
        for index, item in enumerate(how_to_fix, start=1):
            lines.append(f"{index}. {item}")

    if bool(changed_scope.get("requires_uiux")):
        lines.extend(["", "这次改动碰到页面，修完后最好补一轮页面冒烟检查。"])

    file_index_lines = _render_file_index_lines(file_ref_order, file_refs)
    if file_index_lines:
        lines.extend(["", *file_index_lines])

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
    docs_sync = preview.get("docs_sync") if isinstance(preview.get("docs_sync"), dict) else {}
    risk_items = _normalize_items(preview.get("risk_items"))
    done_items = [_text(item) for item in (preview.get("done_items") or []) if _text(item)]
    review_summary = _text(preview.get("review_summary"))
    next_action = _text(preview.get("next_action"))
    should_run = bool(preview.get("should_run", True))
    skip_reason = _text(preview.get("skip_reason"))

    lines: list[str] = []
    project_name = _text(project.get("name"))
    if project_name:
        lines.append(f"**项目** {project_name}")

    if not should_run:
        lines.extend(["", skip_reason or "今天没有新的变更需要回顾。"])
    else:
        if review_summary:
            lines.extend(["", review_summary])

        if done_items:
            lines.extend(["", "**今天完成**"])
            for index, item in enumerate(done_items[:3], start=1):
                lines.append(f"{index}. {item}")

        docs_summary = _text(docs_sync.get("summary"))
        docs_items = [_text(item) for item in (docs_sync.get("items") or []) if _text(item)]
        lines.extend(["", "**文档同步**"])
        if docs_summary:
            lines.append(docs_summary)
        for item in docs_items[:2]:
            lines.append(f"- {item}")

        lines.extend(["", "**风险**"])
        if risk_items:
            for index, item in enumerate(risk_items[:2], start=1):
                severity = _text(item.get("severity")) or "P1"
                title = _text(item.get("title")) or "需要继续确认"
                summary = _text(item.get("summary"))
                lines.append(f"{index}. [{severity}] {title}")
                if summary:
                    lines.append(f"   {summary}")
        else:
            lines.append("暂无明显的交付风险。")

        lines.extend(["", "**下一步**"])
        lines.append(next_action or "继续推进下一步验收。")

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
        template = _review_template(card_kind)
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
