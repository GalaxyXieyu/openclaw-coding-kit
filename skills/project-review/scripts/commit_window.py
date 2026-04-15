#!/usr/bin/env python3
"""Detect recent git commits for project-review automation."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def build_git_log_command(repo_root: str, since: str, until: str | None = None) -> list[str]:
    command = [
        "git",
        "-C",
        str(Path(repo_root).resolve()),
        "log",
        "--date=iso-strict",
        "--pretty=format:%H%x09%ad%x09%s",
        f"--since={since}",
    ]
    if until:
        command.append(f"--until={until}")
    return command


def parse_git_log_output(output: str) -> list[dict[str, str]]:
    commits: list[dict[str, str]] = []
    for raw_line in str(output or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        commit_hash, authored_at, subject = parts
        commits.append(
            {
                "hash": commit_hash,
                "authored_at": authored_at,
                "subject": subject,
            }
        )
    return commits


def collect_recent_commits(repo_root: str, since: str, until: str | None = None) -> list[dict[str, str]]:
    command = build_git_log_command(repo_root, since, until)
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_git_log_output(completed.stdout)


def _json_output(repo_root: str, since: str, until: str | None, commits: list[dict[str, str]]) -> str:
    return json.dumps(
        {
            "repo_root": str(Path(repo_root).resolve()),
            "since": since,
            "until": until,
            "has_recent_commits": bool(commits),
            "count": len(commits),
            "commits": commits,
        },
        ensure_ascii=False,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect whether a repo has recent commits.")
    parser.add_argument("--repo-root", default=".", help="Git repository root.")
    parser.add_argument("--since", default="24 hours ago", help="Git --since value.")
    parser.add_argument("--until", default=None, help="Optional Git --until value.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    commits = collect_recent_commits(args.repo_root, args.since, args.until)
    if args.json:
        print(_json_output(args.repo_root, args.since, args.until, commits))
    else:
        print(f"recent_commits={len(commits)}")
        for item in commits:
            print(f"{item['hash']} {item['authored_at']} {item['subject']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
