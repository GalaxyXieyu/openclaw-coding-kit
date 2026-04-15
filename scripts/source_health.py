#!/usr/bin/env python3
"""Warn about oversized source files without blocking the workflow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_THRESHOLD = 800
SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".java",
    ".go",
    ".rs",
    ".sh",
    ".bash",
    ".zsh",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".scala",
    ".lua",
}
EXCLUDED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "out",
    "exports",
    "screenshots",
    "generated",
    "graphify-out",
    ".planning",
    "plan",
}
EXCLUDED_FILE_SUFFIXES = {".min.js", ".min.css"}


def _is_source_file(path: Path, *, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_DIR_NAMES for part in relative.parts[:-1]):
        return False
    name = path.name
    if any(name.endswith(suffix) for suffix in EXCLUDED_FILE_SUFFIXES):
        return False
    return path.suffix.lower() in SOURCE_EXTENSIONS


def _count_lines(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _ in handle)


def scan_source_health(root: Path, *, threshold: int = DEFAULT_THRESHOLD) -> dict[str, Any]:
    resolved_root = root.expanduser().resolve()
    scanned_files = 0
    offenders: list[dict[str, Any]] = []
    for path in sorted(resolved_root.rglob("*")):
        if not path.is_file():
            continue
        if not _is_source_file(path, root=resolved_root):
            continue
        scanned_files += 1
        lines = _count_lines(path)
        if lines > threshold:
            offenders.append(
                {
                    "path": str(path.relative_to(resolved_root)),
                    "lines": lines,
                }
            )
    offenders.sort(key=lambda item: (-int(item["lines"]), str(item["path"])))
    return {
        "root": str(resolved_root),
        "threshold": int(threshold),
        "scanned_files": scanned_files,
        "offender_count": len(offenders),
        "offenders": offenders,
    }


def _render_text(report: dict[str, Any]) -> str:
    root = str(report.get("root") or "")
    threshold = int(report.get("threshold") or DEFAULT_THRESHOLD)
    scanned_files = int(report.get("scanned_files") or 0)
    offender_count = int(report.get("offender_count") or 0)
    offenders = report.get("offenders") if isinstance(report.get("offenders"), list) else []
    lines = [
        f"Source health summary for {root}",
        f"Scanned {scanned_files} source files; {offender_count} exceed {threshold} lines.",
    ]
    if offender_count:
        for item in offenders:
            lines.append(f"{int(item.get('lines') or 0):>5}  {item.get('path')}")
    else:
        lines.append("No source files exceed the threshold.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root to scan")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="warning threshold in lines")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of text")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = scan_source_health(Path(args.root), threshold=max(1, int(args.threshold)))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
