#!/usr/bin/env python3
"""Build card payloads from normalized project-review bundles."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

SEVERITY_ORDER = ("P0", "P1", "P2")
GENERIC_RISK_MARKERS = ("缺少测试", "测试覆盖", "API 契约", "文档", "文件偏长", "重复代码")
DAILY_GENERIC_FINDING_TITLES = {
    "单文件超过 1000 行",
    "文件接近 1000 行",
    "缺少测试覆盖",
    "导入异常",
    "引用异常",
    "类型错误",
    "静态检查警告",
}
DOC_FLAG_LABELS = {
    "canonical-miniapp-route-drift": "页面路由说明和真实跳转可能对不上。",
    "missing-guiquan-supply-business-flows": "社区和供销的新流程说明还没补齐。",
}
COMMIT_PREFIX_RE = re.compile(r"^(feat|fix|style|refactor|chore|docs|test|perf)(\([^)]+\))?:\s*", re.IGNORECASE)
NOISE_PATH_PREFIXES = (
    ".planning/",
    ".pm/",
    ".agents/",
    ".github/",
    ".trae/",
    "out/",
    "outbound/",
    "test-results/",
    "issues/",
    "plan/",
    "docs/plan/",
)
LOW_SIGNAL_PATHS = {"AGENTS.md", "CLAUDE.md", "pm.json", "package.json"}
DAILY_CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs", ".kt")


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


def _text(value: Any) -> str:
    return str(value or "").strip()


def _severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {level: 0 for level in SEVERITY_ORDER}
    for item in findings:
        severity = str(item.get("severity") or "").upper()
        if severity in counts:
            counts[severity] += 1
    return counts


def _top_risks(findings: list[dict[str, Any]], limit: int = 3) -> list[dict[str, str]]:
    def priority(item: dict[str, Any]) -> tuple[int, int, str]:
        severity = str(item.get("severity") or "P2").upper()
        severity_index = SEVERITY_ORDER.index(severity) if severity in SEVERITY_ORDER else len(SEVERITY_ORDER)
        title = str(item.get("title") or "").strip()
        generic_penalty = 1 if any(marker in title for marker in GENERIC_RISK_MARKERS) else 0
        return (severity_index, generic_penalty, title)

    sortable = sorted(
        findings,
        key=priority,
    )
    result: list[dict[str, str]] = []
    for item in sortable[:limit]:
        result.append(
            {
                "severity": str(item.get("severity") or "").upper(),
                "title": str(item.get("title") or item.get("summary") or "").strip(),
                "summary": str(item.get("summary") or "").strip(),
                "card_title": str(item.get("card_title") or item.get("title") or item.get("summary") or "").strip(),
                "card_summary": str(item.get("card_summary") or item.get("summary") or "").strip(),
                "file": str(item.get("file") or "").strip(),
                "suggestion": str(item.get("suggestion") or "").strip(),
            }
        )
    return result


def _humanize_docs_flag(flag: str) -> str:
    text = _text(flag)
    if not text:
        return ""
    return DOC_FLAG_LABELS.get(text, text)


def _humanize_commit_subject(subject: str) -> str:
    raw = COMMIT_PREFIX_RE.sub("", _text(subject))
    if not raw:
        return ""
    lowered = raw.lower()
    if lowered.startswith("merge "):
        return ""
    replacements = [
        (r"\bminiapp\b", "小程序"),
        (r"\bweapp\b", "weapp"),
        (r"\bentry\b", "入口"),
        (r"\bseller\b", "卖家"),
        (r"\bmarketplace\b", "市场"),
        (r"\bmarket\b", "市场"),
        (r"\bworkspace\b", "工作区"),
        (r"\bguiquan\b", "龟圈"),
        (r"\bcommunity\b", "社区"),
        (r"\bsupply\b", "供销"),
        (r"\bpayment\b", "支付"),
        (r"\bpayments\b", "支付"),
        (r"\borders\b", "订单"),
        (r"\bcart\b", "购物车"),
        (r"\bcss\b", "样式"),
        (r"\bsync\b", "同步"),
        (r"\bupdates\b", "更新"),
        (r"\bupdate\b", "更新"),
        (r"\btrim\b", "收尾"),
        (r"\bconnect\b", "打通"),
        (r"\brefresh\b", "刷新"),
        (r"\beof\b", ""),
        (r"\band\b", "和"),
    ]
    normalized = raw
    for pattern, replacement in replacements:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"[-_]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip(" .")
    normalized = normalized.replace("卖家 市场", "卖家市场")
    normalized = normalized.replace("工作区 更新", "工作区更新")
    normalized = normalized.replace("入口 和", "入口和")
    normalized = normalized.replace(" 和 ", "、")
    normalized = normalized.replace(" 更新", "更新")
    normalized = normalized.replace(" 收尾", "收尾")
    normalized = normalized.replace("入口和 卖家市场", "入口和卖家市场")
    normalized = normalized.replace("供销 购物车 样式", "供销购物车样式")
    normalized = normalized.replace("社区、供销 工作区更新", "社区和供销工作区更新")
    return normalized


def _today_updates(commits: list[dict[str, Any]], changed_files: list[str], *, limit: int = 3) -> list[str]:
    updates: list[str] = []
    for item in commits:
        subject = _humanize_commit_subject(item.get("subject"))
        if subject and subject not in updates:
            updates.append(subject)
        if len(updates) >= limit:
            break
    if updates:
        return updates
    highlights = _highlight_files(changed_files, limit=limit)
    return [f"改动 {path}" for path in highlights]


def _file_priority(path: str) -> tuple[int, int, str]:
    text = _text(path)
    if not text:
        return (99, 99, text)
    if text in LOW_SIGNAL_PATHS:
        return (10, len(text), text)
    if any(text.startswith(prefix) for prefix in NOISE_PATH_PREFIXES):
        return (9, len(text), text)
    if text.startswith(("apps/api/src/", "apps/miniapp/src/", "src/", "pages/", "components/")):
        return (0, len(text), text)
    if text.startswith(("apps/api/prisma/", "packages/", "apps/web/", "apps/admin/")):
        return (1, len(text), text)
    if text.startswith("docs/") or text.endswith(".md"):
        return (2, len(text), text)
    if text.endswith((".css", ".scss", ".wxss")):
        return (3, len(text), text)
    if text.endswith((".png", ".jpg", ".jpeg", ".svg")):
        return (8, len(text), text)
    return (5, len(text), text)


def _highlight_files(changed_files: list[str], *, limit: int = 6) -> list[str]:
    files = _normalize_texts(changed_files)
    meaningful = [path for path in files if _file_priority(path)[0] < 9]
    candidates = meaningful or files
    ordered = sorted(candidates, key=_file_priority)
    result = ordered[:limit]
    doc_candidates = [path for path in ordered if path.startswith("docs/") or path.endswith(".md")]
    has_doc = any(path.startswith("docs/") or path.endswith(".md") for path in result)
    if doc_candidates and not has_doc:
        result = result[: max(limit - 1, 0)]
        preferred_doc = next((path for path in doc_candidates if not path.endswith("README.md")), doc_candidates[0])
        result.append(preferred_doc)
    return result[:limit]


def _build_check(label: str, status: str, detail: str) -> dict[str, str]:
    return {
        "label": label,
        "status": status,
        "detail": _text(detail),
    }


def _doc_update_rows(doc_updates: list[dict[str, Any]] | None, *, limit: int = 3) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in _normalize_items(doc_updates):
        path = _text(item.get("path"))
        summary = _text(item.get("summary"))
        if not path or not summary:
            continue
        key = (path, summary)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"path": path, "summary": summary})
        if len(rows) >= limit:
            break
    return rows


def _daily_audit_checks(bundle: dict[str, Any], docs_flags: list[str], findings: list[dict[str, Any]]) -> list[dict[str, str]]:
    audit = bundle.get("audit") if isinstance(bundle.get("audit"), dict) else {}
    signals = audit.get("signals") if isinstance(audit.get("signals"), dict) else {}
    file_stats = _normalize_items(audit.get("file_stats"))
    lane_results = bundle.get("lane_results") if isinstance(bundle.get("lane_results"), dict) else {}
    code_lane = lane_results.get("code_review") if isinstance(lane_results.get("code_review"), dict) else {}
    docs_lane = lane_results.get("docs_review") if isinstance(lane_results.get("docs_review"), dict) else {}
    code_meta = code_lane.get("meta") if isinstance(code_lane.get("meta"), dict) else {}
    docs_meta = docs_lane.get("meta") if isinstance(docs_lane.get("meta"), dict) else {}

    oversized_files = _normalize_items(code_meta.get("oversized_files"))
    near_limit_files = _normalize_items(code_meta.get("near_limit_files"))
    explicit_errors = {
        "导入异常": _normalize_texts(audit.get("import_errors")) + _normalize_texts(code_meta.get("import_errors")),
        "引用异常": _normalize_texts(audit.get("reference_errors")) + _normalize_texts(code_meta.get("reference_errors")),
        "类型错误": _normalize_texts(audit.get("type_errors")) + _normalize_texts(code_meta.get("type_errors")),
        "静态检查警告": _normalize_texts(audit.get("lint_errors")) + _normalize_texts(code_meta.get("lint_errors")),
    }

    checks: list[dict[str, str]] = []
    if oversized_files:
        first = oversized_files[0]
        checks.append(
            _build_check(
                "单文件 > 1000 行",
                "risk",
                f"发现 {len(oversized_files)} 个超长文件，最明显的是 {_text(first.get('path'))}（{int(first.get('line_count') or 0)} 行）。",
            )
        )
    elif near_limit_files:
        first = near_limit_files[0]
        checks.append(
            _build_check(
                "单文件 > 1000 行",
                "warn",
                f"还没超过 1000 行，但 {_text(first.get('path'))} 已接近阈值（{int(first.get('line_count') or 0)} 行）。",
            )
        )
    elif file_stats or bool(signals.get("file_stats_provided")):
        checks.append(_build_check("单文件 > 1000 行", "ok", "本次变更里没发现超过 1000 行的文件。"))
    else:
        checks.append(_build_check("单文件 > 1000 行", "unknown", "这次没有带文件行数统计，暂时无法判断。"))

    import_errors = explicit_errors["导入异常"]
    reference_errors = explicit_errors["引用异常"]
    type_errors = explicit_errors["类型错误"]
    lint_errors = explicit_errors["静态检查警告"]
    if import_errors or reference_errors or type_errors:
        first_error = (import_errors + reference_errors + type_errors)[0]
        checks.append(_build_check("导入/引用异常", "risk", first_error))
    elif lint_errors:
        checks.append(_build_check("导入/引用异常", "warn", lint_errors[0]))
    elif any(
        bool(signals.get(key))
        for key in (
            "import_errors_provided",
            "reference_errors_provided",
            "type_errors_provided",
            "lint_errors_provided",
        )
    ):
        checks.append(_build_check("导入/引用异常", "ok", "本次输入里没有导入、引用或类型报错记录。"))
    else:
        checks.append(_build_check("导入/引用异常", "unknown", "这次没有带编译或静态检查结果，暂时看不到这类报错。"))

    changed_code_files = int(code_meta.get("changed_code_files") or 0)
    tests_changed = bool(code_meta.get("tests_changed"))
    if changed_code_files > 0 and tests_changed:
        checks.append(_build_check("测试覆盖", "ok", "这次代码改动带了测试更新。"))
    elif changed_code_files > 0:
        checks.append(_build_check("测试覆盖", "risk", "这次代码改动没看到对应测试更新。"))
    else:
        checks.append(_build_check("测试覆盖", "unknown", "这次没有识别到明确的代码改动范围。"))

    code_changed = bool(docs_meta.get("code_changed"))
    docs_changed = bool(docs_meta.get("docs_changed"))
    humanized_doc_flags = [_humanize_docs_flag(item) for item in docs_flags if _humanize_docs_flag(item)]
    if code_changed and docs_changed and humanized_doc_flags:
        checks.append(_build_check("功能文档同步", "warn", humanized_doc_flags[0]))
    elif code_changed and docs_changed:
        checks.append(_build_check("功能文档同步", "ok", "代码和 docs 一起更新了。"))
    elif code_changed and not docs_changed:
        checks.append(_build_check("功能文档同步", "risk", "代码改了，但没看到 docs 更新。"))
    elif docs_changed:
        checks.append(_build_check("功能文档同步", "ok", "这次主要补了文档或说明。"))
    elif humanized_doc_flags:
        checks.append(_build_check("功能文档同步", "warn", humanized_doc_flags[0]))
    else:
        checks.append(_build_check("功能文档同步", "unknown", "这次没有看到明确的文档同步信号。"))

    return checks


def _review_summary(bundle: dict[str, Any]) -> str:
    lane_results = bundle.get("lane_results") if isinstance(bundle.get("lane_results"), dict) else {}
    llm_code_review = lane_results.get("llm_code_review") if isinstance(lane_results.get("llm_code_review"), dict) else {}
    llm_docs_review = lane_results.get("llm_docs_review") if isinstance(lane_results.get("llm_docs_review"), dict) else {}
    for candidate in (llm_code_review.get("summary"), llm_docs_review.get("summary")):
        text = _text(candidate)
        if text:
            return text
    commits = _normalize_items(bundle.get("commits"))
    if commits:
        return f"今天有 {len(commits)} 次提交，先按代码和文档两条线做回顾。"
    return ""


def _daily_focus_findings(findings: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, str]]:
    filtered = [
        item
        for item in findings
        if _text(item.get("title")) not in DAILY_GENERIC_FINDING_TITLES
    ]
    return _top_risks(filtered, limit=limit)


def _daily_next_actions(next_actions: list[str], audit_checks: list[dict[str, str]], docs_flags: list[str]) -> list[str]:
    if next_actions:
        return next_actions[:3]

    derived: list[str] = []
    for item in audit_checks:
        label = _text(item.get("label"))
        status = _text(item.get("status"))
        if label == "单文件 > 1000 行" and status == "risk":
            derived.append("先拆今天命中的超长文件")
        elif label == "导入/引用异常" and status == "risk":
            derived.append("先修导入和引用报错")
        elif label == "测试覆盖" and status == "risk":
            derived.append("补今天改动的回归测试")
        elif label == "功能文档同步" and status in {"risk", "warn"}:
            derived.append("把新增功能说明补到 docs")
    if docs_flags and "把新增功能说明补到 docs" not in derived:
        derived.append("把新增功能说明补到 docs")
    if not derived:
        derived.append("继续盯今天改动的核心模块")
    return _normalize_texts(derived)[:3]


def _has_llm_daily_review(review: dict[str, Any]) -> bool:
    return _text(review.get("source")) == "llm-review"


def _daily_doc_update_items(doc_updates: list[dict[str, str]]) -> list[str]:
    items: list[str] = []
    for item in doc_updates:
        summary = _text(item.get("summary"))
        if not summary:
            continue
        if summary.startswith("业务文档已补充"):
            items.append(summary)
            continue
        quoted = re.search(r"「([^」]+)」", summary)
        label = quoted.group(1).strip() if quoted else summary
        label = re.sub(r"^(补充|新增说明：|更新说明：|新增|更新)\s*", "", label).strip()
        label = label.replace("章节", "").strip(" 。；")
        if not label:
            label = "本次功能说明"
        if not label.endswith(("功能", "说明", "规则", "文档", "口径")):
            label = f"{label}功能"
        items.append(f"业务文档已补充 {label}")
    return _normalize_texts(items)[:2]


def _daily_changed_code(changed_scope: dict[str, Any]) -> bool:
    return any(
        _text(path).endswith(DAILY_CODE_SUFFIXES)
        for path in changed_scope.get("files") or []
    )


def _daily_review_summary(bundle: dict[str, Any], llm_daily_review: dict[str, Any]) -> str:
    summary = _text(llm_daily_review.get("summary"))
    if summary:
        return summary
    return _review_summary(bundle) or "今天完成了本次项目回顾，重点看业务进展、文档同步和风险。"


def _daily_done_items(
    llm_daily_review: dict[str, Any],
    *,
    commits: list[dict[str, Any]],
    changed_files: list[str],
) -> list[str]:
    done_items = _normalize_texts(llm_daily_review.get("done_items"))
    if done_items:
        return done_items[:2]
    if commits:
        return _today_updates(commits, [], limit=2)
    if any(path.startswith("docs/") or path.endswith(".md") for path in changed_files):
        return ["今天补充了相关业务说明。"]
    return ["今天没有识别到明确的业务功能变更。"]


def _daily_docs_sync(
    llm_daily_review: dict[str, Any],
    *,
    doc_updates: list[dict[str, str]],
    docs_flags: list[str],
    changed_scope: dict[str, Any],
) -> dict[str, Any]:
    raw_sync = llm_daily_review.get("docs_sync") if isinstance(llm_daily_review.get("docs_sync"), dict) else {}
    status = _text(raw_sync.get("status")).lower()
    if status not in {"synced", "partial", "missing"}:
        status = "partial"
    summary = _text(raw_sync.get("summary"))
    items = _normalize_texts(raw_sync.get("items"))
    doc_items = _daily_doc_update_items(doc_updates)
    if doc_items:
        status = "synced"
        items = _normalize_texts(items + doc_items)[:2]
        if not summary or "没" in summary or "未" in summary:
            summary = items[0]
    elif not _has_llm_daily_review(llm_daily_review):
        humanized_flags = [_humanize_docs_flag(item) for item in docs_flags if _humanize_docs_flag(item)]
        if humanized_flags:
            status = "partial"
            summary = humanized_flags[0]
        elif _daily_changed_code(changed_scope):
            status = "missing"
            summary = "本次功能说明还没补。"
        else:
            status = "partial"
            summary = "暂未识别到需要同步的业务文档。"
    if not summary:
        summary = {
            "synced": "业务文档已补充本次功能说明。",
            "missing": "本次功能说明还没补。",
            "partial": "文档同步状态还需要继续确认。",
        }[status]
    return {
        "status": status,
        "summary": summary,
        "items": items[:2],
    }


def _daily_risk_items(
    llm_daily_review: dict[str, Any],
    *,
    findings: list[dict[str, Any]],
) -> list[dict[str, str]]:
    raw_risks = _normalize_items(llm_daily_review.get("risk_items"))
    if raw_risks:
        source = raw_risks[:2]
    else:
        source = _daily_focus_findings(findings, limit=2)
    risks: list[dict[str, str]] = []
    for item in source:
        title = _text(item.get("card_title") or item.get("title"))
        summary = _text(item.get("card_summary") or item.get("summary"))
        if not title and not summary:
            continue
        risks.append(
            {
                "severity": _text(item.get("severity")).upper() or "P1",
                "title": title or summary,
                "summary": summary,
            }
        )
    return risks[:2]


def _daily_next_action(
    llm_daily_review: dict[str, Any],
    *,
    fallback_actions: list[str],
    docs_sync: dict[str, Any],
    risk_items: list[dict[str, str]],
) -> str:
    direct = _text(llm_daily_review.get("next_action"))
    if direct:
        return direct
    if fallback_actions:
        return fallback_actions[0]
    if risk_items:
        return "先处理今天识别到的交付风险。"
    if _text(docs_sync.get("status")) == "missing":
        return "先把本次功能说明补到业务文档。"
    return "继续推进下一步验收。"


def build_code_health_risk_card(bundle: dict[str, Any]) -> dict[str, Any]:
    findings = _normalize_items(bundle.get("findings"))
    docs_flags = [str(item).strip() for item in bundle.get("docs_flags") or [] if str(item).strip()]
    doc_updates = _doc_update_rows(bundle.get("doc_updates"))
    changed_scope = bundle.get("changed_scope") if isinstance(bundle.get("changed_scope"), dict) else {}
    commits = _normalize_items(bundle.get("commits"))
    trigger = bundle.get("trigger") if isinstance(bundle.get("trigger"), dict) else {}
    lane_results = bundle.get("lane_results") if isinstance(bundle.get("lane_results"), dict) else {}
    llm_code_review = lane_results.get("llm_code_review") if isinstance(lane_results.get("llm_code_review"), dict) else {}
    llm_docs_review = lane_results.get("llm_docs_review") if isinstance(lane_results.get("llm_docs_review"), dict) else {}
    llm_findings = _normalize_items(llm_code_review.get("findings")) + _normalize_items(llm_docs_review.get("findings"))
    card_findings = llm_findings or findings
    next_actions = _normalize_texts(llm_code_review.get("next_actions")) + _normalize_texts(llm_docs_review.get("next_actions"))
    next_actions = _normalize_texts(next_actions)

    return {
        "card_kind": "code_health_risk_card_v1",
        "title": "代码健康提醒",
        "should_run": bool(trigger.get("should_run")),
        "skip_reason": str(trigger.get("skip_reason") or "").strip(),
        "severity_counts": _severity_counts(card_findings),
        "top_risks": _top_risks(card_findings),
        "docs_flags": docs_flags[:3],
        "doc_updates": doc_updates,
        "changed_scope": {
            "file_count": int(changed_scope.get("file_count") or 0),
            "files": list(changed_scope.get("files") or []),
            "requires_uiux": bool(changed_scope.get("touches_ui")),
        },
        "commit_window": {
            "count": len(commits),
            "latest_subject": str(commits[0].get("subject") or "").strip() if commits else "",
        },
        "next_actions": next_actions[:3],
        "actions": ["开始修复", "忽略这次"],
    }


def build_daily_review_card(bundle: dict[str, Any]) -> dict[str, Any]:
    findings = _normalize_items(bundle.get("findings"))
    docs_flags = [str(item).strip() for item in bundle.get("docs_flags") or [] if str(item).strip()]
    doc_updates = _doc_update_rows(bundle.get("doc_updates"))
    changed_scope = bundle.get("changed_scope") if isinstance(bundle.get("changed_scope"), dict) else {}
    commits = _normalize_items(bundle.get("commits"))
    trigger = bundle.get("trigger") if isinstance(bundle.get("trigger"), dict) else {}
    lane_results = bundle.get("lane_results") if isinstance(bundle.get("lane_results"), dict) else {}
    llm_daily_review = lane_results.get("llm_daily_review") if isinstance(lane_results.get("llm_daily_review"), dict) else {}
    changed_files = [str(item).strip() for item in changed_scope.get("files") or [] if str(item).strip()]
    docs_sync = _daily_docs_sync(
        llm_daily_review,
        doc_updates=doc_updates,
        docs_flags=docs_flags,
        changed_scope=changed_scope,
    )
    risk_items = _daily_risk_items(llm_daily_review, findings=findings)
    fallback_actions = _daily_next_actions([], [], docs_sync.get("items") or [docs_sync.get("summary")])
    next_action = _daily_next_action(
        llm_daily_review,
        fallback_actions=fallback_actions,
        docs_sync=docs_sync,
        risk_items=risk_items,
    )

    return {
        "card_kind": "daily_review_card_v1",
        "title": "每日项目回顾",
        "should_run": bool(trigger.get("should_run")),
        "skip_reason": str(trigger.get("skip_reason") or "").strip(),
        "review_summary": _daily_review_summary(bundle, llm_daily_review),
        "done_items": _daily_done_items(llm_daily_review, commits=commits, changed_files=changed_files),
        "docs_sync": docs_sync,
        "risk_items": risk_items,
        "next_action": next_action,
        "changed_scope": {
            "requires_uiux": bool(changed_scope.get("touches_ui")),
        },
        "actions": [],
    }


def build_review_card(bundle: dict[str, Any]) -> dict[str, Any]:
    trigger = bundle.get("trigger") if isinstance(bundle.get("trigger"), dict) else {}
    tasks = bundle.get("tasks") if isinstance(bundle.get("tasks"), dict) else {}
    card_kind = str(trigger.get("card_kind") or "").strip()
    title = {
        "weekly_review_card_v1": "本周项目回顾",
        "weekly_digest_card_v1": "本周项目回顾",
        "monthly_review_card_v1": "本月项目复盘",
        "event_alert_card_v1": "项目提醒",
    }.get(card_kind, "项目回顾")
    actions = {
        "event_alert_card_v1": ["去看任务", "今天处理", "一周后再提醒", "这次不用提醒"],
    }.get(card_kind, [])
    return {
        "card_kind": card_kind,
        "title": title,
        "projects": _normalize_items(bundle.get("projects")),
        "stats": {
            "completed_count": len(_normalize_items(tasks.get("completed"))),
            "active_count": len(_normalize_items(tasks.get("active"))),
            "blocked_count": len(_normalize_items(tasks.get("blocked"))),
            "stale_count": len(_normalize_items(tasks.get("stale"))),
        },
        "actions": actions,
    }


def build_card_payload(bundle: dict[str, Any]) -> dict[str, Any]:
    trigger = bundle.get("trigger") if isinstance(bundle.get("trigger"), dict) else {}
    card_kind = str(trigger.get("card_kind") or "").strip()
    if card_kind == "daily_review_card_v1":
        return build_daily_review_card(bundle)
    if card_kind == "code_health_risk_card_v1":
        return build_code_health_risk_card(bundle)
    return build_review_card(bundle)


def build_digest_card(bundle: dict[str, Any]) -> dict[str, Any]:
    return build_review_card(bundle)


def _load_payload(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("payload is required")
    if text.startswith("@"):
        with open(text[1:], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build project-review card payloads from a normalized bundle.")
    parser.add_argument("--payload", required=True, help="JSON bundle or @path/to/bundle.json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = _load_payload(args.payload)
    print(json.dumps(build_card_payload(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
