#!/usr/bin/env python3
"""Deterministic code-review lane for project-review."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

CODE_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".java", ".rb", ".rs", ".kt")
TEST_MARKERS = ("test_", "_test.", ".spec.", ".test.", "tests/", "__tests__/")
API_MARKERS = ("api/", "src/api/", "/api/")


def _normalize_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items or []:
        if isinstance(item, dict):
            result.append(item)
    return result


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


def _is_test_file(path: str) -> bool:
    text = str(path or "")
    return any(marker in text for marker in TEST_MARKERS)


def _is_code_file(path: str) -> bool:
    text = str(path or "")
    return text.endswith(CODE_SUFFIXES) and not _is_test_file(text)


def _is_api_file(path: str) -> bool:
    text = str(path or "")
    return any(marker in text for marker in API_MARKERS)


def _build_finding(severity: str, title: str, summary: str, *, file: str = "", category: str = "") -> dict[str, str]:
    return {
        "severity": severity,
        "title": title,
        "summary": summary,
        "file": file,
        "category": category,
    }


def _dedupe_findings(findings: list[dict[str, str]]) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in findings:
        key = (str(item.get("severity") or ""), str(item.get("title") or ""), str(item.get("file") or ""))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _extract_error_path(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    for token in raw.replace("(", " ").replace(")", " ").split():
        candidate = token.strip(":,[]'\"")
        if "/" in candidate and "." in candidate:
            return candidate
    return ""


def run_code_review_lane(payload: dict[str, Any]) -> dict[str, Any]:
    changed_files = _normalize_paths(payload.get("changed_files"))
    file_stats = _normalize_items(payload.get("file_stats"))
    function_stats = _normalize_items(payload.get("function_stats"))
    duplicate_groups = _normalize_items(payload.get("duplicate_groups"))
    import_errors = _normalize_texts(payload.get("import_errors"))
    reference_errors = _normalize_texts(payload.get("reference_errors"))
    type_errors = _normalize_texts(payload.get("type_errors"))
    lint_errors = _normalize_texts(payload.get("lint_errors"))
    findings: list[dict[str, str]] = []
    oversized_files: list[dict[str, Any]] = []
    near_limit_files: list[dict[str, Any]] = []

    code_files = [path for path in changed_files if _is_code_file(path)]
    tests_changed = any(_is_test_file(path) for path in changed_files)
    api_changed = any(_is_api_file(path) for path in changed_files)

    for item in file_stats:
        path = str(item.get("path") or "").strip()
        line_count = int(item.get("line_count") or 0)
        if line_count >= 1000:
            oversized_files.append({"path": path, "line_count": line_count})
            findings.append(
                _build_finding("P1", "单文件超过 1000 行", f"文件约 {line_count} 行，已经超过 1000 行阈值。", file=path, category="size")
            )
        elif line_count >= 800:
            near_limit_files.append({"path": path, "line_count": line_count})
            findings.append(
                _build_finding("P2", "文件接近 1000 行", f"文件约 {line_count} 行，已经接近 1000 行阈值。", file=path, category="size")
            )

    for item in function_stats:
        path = str(item.get("path") or "").strip()
        name = str(item.get("name") or "未知函数").strip()
        line_count = int(item.get("line_count") or 0)
        if line_count >= 120:
            findings.append(
                _build_finding("P0", "函数过长", f"{name} 约 {line_count} 行，容易藏回归和异常路径。", file=path, category="function")
            )
        elif line_count >= 80:
            findings.append(
                _build_finding("P1", "函数偏长", f"{name} 约 {line_count} 行，建议拆责任。", file=path, category="function")
            )

    for item in duplicate_groups:
        files = _normalize_paths(item.get("files"))
        summary = str(item.get("summary") or "发现重复逻辑").strip()
        file_label = files[0] if files else ""
        findings.append(
            _build_finding("P1", "重复代码", summary, file=file_label, category="duplication")
        )

    if code_files and not tests_changed and not bool(payload.get("allow_missing_tests")):
        findings.append(
            _build_finding("P1", "缺少测试覆盖", "这次代码改动没有看到对应测试更新。", file=code_files[0], category="testing")
        )

    if api_changed and payload.get("api_contract_checked") is False:
        api_file = next((path for path in changed_files if _is_api_file(path)), "")
        findings.append(
            _build_finding("P1", "API 契约未确认", "接口改动没有看到状态码、错误处理或返回格式校验。", file=api_file, category="api")
        )

    if bool(payload.get("missing_error_handling")):
        findings.append(
            _build_finding("P0", "缺少异常处理", "关键路径报错后可能直接失败，没有看到明确兜底。", file=code_files[0] if code_files else "", category="error")
        )

    for item in import_errors[:3]:
        findings.append(
            _build_finding("P1", "导入异常", item, file=_extract_error_path(item), category="reference")
        )

    for item in reference_errors[:3]:
        findings.append(
            _build_finding("P1", "引用异常", item, file=_extract_error_path(item), category="reference")
        )

    for item in type_errors[:3]:
        findings.append(
            _build_finding("P1", "类型错误", item, file=_extract_error_path(item), category="type")
        )

    for item in lint_errors[:3]:
        findings.append(
            _build_finding("P2", "静态检查警告", item, file=_extract_error_path(item), category="lint")
        )

    for item in payload.get("performance_flags") or []:
        if isinstance(item, dict):
            findings.append(
                _build_finding(
                    str(item.get("severity") or "P1").upper(),
                    str(item.get("title") or "性能风险").strip(),
                    str(item.get("summary") or "").strip(),
                    file=str(item.get("file") or "").strip(),
                    category="performance",
                )
            )
        else:
            findings.append(
                _build_finding("P1", "性能风险", str(item).strip(), file=code_files[0] if code_files else "", category="performance")
            )

    return {
        "lane": "code-review",
        "findings": _dedupe_findings(findings),
        "meta": {
            "changed_code_files": len(code_files),
            "tests_changed": tests_changed,
            "api_changed": api_changed,
            "oversized_files": oversized_files,
            "near_limit_files": near_limit_files,
            "import_errors": import_errors,
            "reference_errors": reference_errors,
            "type_errors": type_errors,
            "lint_errors": lint_errors,
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
    parser = argparse.ArgumentParser(description="Run the project-review code-review lane.")
    parser.add_argument("--payload", required=True, help="JSON payload or @path")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    payload = _load_payload(args.payload)
    print(json.dumps(run_code_review_lane(payload), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
