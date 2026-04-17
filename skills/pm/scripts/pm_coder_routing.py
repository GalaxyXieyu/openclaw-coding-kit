from __future__ import annotations

import re
from typing import Any

TASK_TYPE_LABELS = (
    "任务类型",
    "任务类别",
    "Task Type",
    "Task Category",
    "task_type",
    "task_category",
)
TASK_TYPE_ALIASES = {
    "frontend": "frontend",
    "front-end": "frontend",
    "ui": "frontend",
    "ux": "frontend",
    "design": "frontend",
    "page": "frontend",
    "pages": "frontend",
    "backend": "backend",
    "back-end": "backend",
    "api": "backend",
    "service": "backend",
    "bug": "bug",
    "bugfix": "bug",
    "fix": "bug",
    "hotfix": "bug",
    "defect": "bug",
    "issue": "bug",
    "incident": "bug",
    "regression": "bug",
    "review": "review",
    "risk": "review",
}
ROUTING_TARGET_KEYS = ("backend", "agent_id", "timeout_seconds", "thinking", "session_key")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_text(item) for item in value if _text(item)]
    text = _text(value)
    return [text] if text else []


def _normalize_token(value: str) -> str:
    lowered = _text(value).lower()
    normalized = re.sub(r"[\s_/]+", "-", lowered)
    normalized = re.sub(r"[^a-z0-9-]+", "", normalized).strip("-")
    return normalized


def normalize_task_type(value: str) -> str:
    normalized = _normalize_token(value)
    if not normalized:
        return ""
    return TASK_TYPE_ALIASES.get(normalized, normalized)


def extract_task_route_type(task: dict[str, Any]) -> str:
    if not isinstance(task, dict):
        return ""
    for key in ("task_type", "taskType", "type"):
        normalized = normalize_task_type(_text(task.get(key)))
        if normalized:
            return normalized
    description = _text(task.get("description"))
    if not description:
        return ""
    for raw_line in description.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        for label in TASK_TYPE_LABELS:
            match = re.match(rf"^{re.escape(label)}\s*[：:]\s*(.+)$", line, flags=re.IGNORECASE)
            if not match:
                continue
            normalized = normalize_task_type(match.group(1))
            if normalized:
                return normalized
    return ""


def _match_regex_list(text: str, patterns: list[str], *, rule_name: str, field_name: str) -> list[str]:
    matched: list[str] = []
    for pattern in patterns:
        try:
            if re.search(pattern, text, flags=re.IGNORECASE):
                matched.append(pattern)
        except re.error as exc:
            raise SystemExit(
                f"invalid coder routing regex in rule '{rule_name}' field '{field_name}': {pattern} ({exc})"
            ) from exc
    return matched


def _normalize_target(raw_target: Any) -> dict[str, Any]:
    target = raw_target if isinstance(raw_target, dict) else {}
    normalized: dict[str, Any] = {}
    backend = _text(target.get("backend"))
    if backend:
        normalized["backend"] = backend
    agent_id = _text(target.get("agent_id") or target.get("agent") or target.get("model"))
    if agent_id:
        normalized["agent_id"] = agent_id
    timeout_raw = target.get("timeout_seconds", target.get("timeout"))
    if timeout_raw not in {None, ""}:
        try:
            normalized["timeout_seconds"] = int(timeout_raw)
        except (TypeError, ValueError):
            raise SystemExit(f"invalid coder routing timeout: {timeout_raw}")
    thinking = _text(target.get("thinking"))
    if thinking:
        normalized["thinking"] = thinking
    session_key = _text(target.get("session_key"))
    if session_key:
        normalized["session_key"] = session_key
    return normalized


def resolve_task_coder_route(coder_config: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    routing = coder_config.get("routing") if isinstance(coder_config, dict) else {}
    if not isinstance(routing, dict):
        return {"matched": False, "reason": "routing-config-missing", "task_type": "", "target": {}, "matched_by": {}}
    if routing.get("enabled") is False:
        return {"matched": False, "reason": "routing-disabled", "task_type": "", "target": {}, "matched_by": {}}
    rules = routing.get("rules")
    if not isinstance(rules, list) or not rules:
        return {"matched": False, "reason": "routing-rules-missing", "task_type": "", "target": {}, "matched_by": {}}
    if not isinstance(task, dict) or not task:
        return {"matched": False, "reason": "task-missing", "task_type": "", "target": {}, "matched_by": {}}

    task_type = extract_task_route_type(task)
    summary = _text(task.get("summary") or task.get("normalized_summary"))
    description = _text(task.get("description"))
    searchable_text = "\n".join(item for item in (summary, description) if item).lower()

    for index, raw_rule in enumerate(rules, start=1):
        if not isinstance(raw_rule, dict):
            continue
        name = _text(raw_rule.get("name")) or f"rule-{index}"
        match = raw_rule.get("match") if isinstance(raw_rule.get("match"), dict) else {}
        keywords = [item.lower() for item in _string_list(match.get("keywords"))]
        task_types = [normalize_task_type(item) for item in _string_list(match.get("task_types"))]
        summary_patterns = _string_list(match.get("summary_patterns"))
        description_patterns = _string_list(match.get("description_patterns"))
        mode = _normalize_token(_text(match.get("mode") or "any")) or "any"
        if mode not in {"any", "all"}:
            raise SystemExit(f"invalid coder routing match mode in rule '{name}': {match.get('mode')}")

        checks: list[bool] = []
        matched_by: dict[str, list[str]] = {}

        if task_types:
            hit = task_type in task_types if task_type else False
            checks.append(hit)
            if hit:
                matched_by["task_types"] = [task_type]
        if keywords:
            keyword_hits = [keyword for keyword in keywords if keyword in searchable_text]
            checks.append(bool(keyword_hits))
            if keyword_hits:
                matched_by["keywords"] = keyword_hits
        if summary_patterns:
            summary_hits = _match_regex_list(summary, summary_patterns, rule_name=name, field_name="summary_patterns")
            checks.append(bool(summary_hits))
            if summary_hits:
                matched_by["summary_patterns"] = summary_hits
        if description_patterns:
            description_hits = _match_regex_list(
                description,
                description_patterns,
                rule_name=name,
                field_name="description_patterns",
            )
            checks.append(bool(description_hits))
            if description_hits:
                matched_by["description_patterns"] = description_hits

        if not checks:
            continue

        matched = all(checks) if mode == "all" else any(checks)
        if not matched:
            continue

        target = _normalize_target(raw_rule.get("target"))
        if not target:
            continue
        return {
            "matched": True,
            "reason": "matched-rule",
            "rule_name": name,
            "task_type": task_type,
            "match_mode": mode,
            "matched_by": matched_by,
            "target": {key: value for key, value in target.items() if key in ROUTING_TARGET_KEYS},
        }

    return {
        "matched": False,
        "reason": "no-rule-matched",
        "task_type": task_type,
        "target": {},
        "matched_by": {},
    }


__all__ = ["extract_task_route_type", "normalize_task_type", "resolve_task_coder_route"]
