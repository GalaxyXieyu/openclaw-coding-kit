#!/usr/bin/env python3
"""Local review state store for project-review idempotency and callback tracking."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_REVIEW_STATE_FILENAME = "project-review-state.json"
LEGACY_PROJECT_REVIEW_STATE_FILENAME = "task-review-state.json"


def default_state_path(repo_root: str = ".") -> Path:
    return Path(repo_root).resolve() / ".pm" / PROJECT_REVIEW_STATE_FILENAME


def _resolve_read_path(path: str | Path) -> Path:
    state_path = Path(path)
    if state_path.exists():
        return state_path
    if state_path.name == PROJECT_REVIEW_STATE_FILENAME:
        legacy_path = state_path.with_name(LEGACY_PROJECT_REVIEW_STATE_FILENAME)
        if legacy_path.exists():
            return legacy_path
    return state_path


def _empty_state() -> dict[str, Any]:
    return {"reviews": []}


def stable_json_hash(payload: Any) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_state(path: str | Path) -> dict[str, Any]:
    state_path = _resolve_read_path(path)
    if not state_path.exists():
        return _empty_state()
    with state_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or not isinstance(data.get("reviews"), list):
        return _empty_state()
    return data


def save_state(path: str | Path, state: dict[str, Any]) -> dict[str, Any]:
    state_path = Path(path)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with state_path.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2)
    return state


def get_review_by_id(state: dict[str, Any], review_id: str) -> dict[str, Any] | None:
    for item in state.get("reviews") or []:
        if isinstance(item, dict) and str(item.get("review_id") or "") == str(review_id):
            return item
    return None


def get_review_by_dedupe_key(state: dict[str, Any], dedupe_key: str) -> dict[str, Any] | None:
    for item in state.get("reviews") or []:
        if isinstance(item, dict) and str(item.get("dedupe_key") or "") == str(dedupe_key):
            return item
    return None


def upsert_review_record(path: str | Path, record: dict[str, Any]) -> dict[str, Any]:
    review_id = str(record.get("review_id") or "").strip()
    if not review_id:
        raise ValueError("review_id is required")
    state = load_state(path)
    current = get_review_by_id(state, review_id)
    if current is None:
        state["reviews"].append(record)
        save_state(path, state)
        return record
    current.update(record)
    save_state(path, state)
    return current


def append_history(path: str | Path, review_id: str, event: dict[str, Any]) -> dict[str, Any]:
    state = load_state(path)
    current = get_review_by_id(state, review_id)
    if current is None:
        raise KeyError(f"review_id not found: {review_id}")
    history = current.get("history")
    if not isinstance(history, list):
        history = []
        current["history"] = history
    history.append(event)
    save_state(path, state)
    return current


def update_review_status(path: str | Path, review_id: str, *, status: str, updated_at: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    state = load_state(path)
    current = get_review_by_id(state, review_id)
    if current is None:
        raise KeyError(f"review_id not found: {review_id}")
    current["status"] = status
    current["updated_at"] = updated_at
    if extra:
        current.update(extra)
    history = current.get("history")
    if not isinstance(history, list):
        history = []
        current["history"] = history
    history.append({"event": "status_updated", "status": status, "at": updated_at})
    save_state(path, state)
    return current


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read or update project-review local state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    show_parser = subparsers.add_parser("show", help="Print current state.")
    show_parser.add_argument("--path", required=True, help="State file path.")

    upsert_parser = subparsers.add_parser("upsert", help="Upsert one review record.")
    upsert_parser.add_argument("--path", required=True, help="State file path.")
    upsert_parser.add_argument("--record", required=True, help="JSON record or @path")
    return parser


def _load_json(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if text.startswith("@"):
        with open(text[1:], "r", encoding="utf-8") as handle:
            return json.load(handle)
    return json.loads(text)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "show":
        print(json.dumps(load_state(args.path), ensure_ascii=False))
        return 0
    if args.command == "upsert":
        record = _load_json(args.record)
        print(json.dumps(upsert_review_record(args.path, record), ensure_ascii=False))
        return 0
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    sys.exit(main())
