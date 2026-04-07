#!/usr/bin/env python3
"""Read lightweight ACP session status from local OpenClaw state."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OPENCLAW_CONFIG_ENV_VARS = ("OPENCLAW_CONFIG",)
OPENCLAW_HOME_ENV_VARS = ("OPENCLAW_STATE_DIR", "OPENCLAW_HOME")


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        key = str(expanded)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(expanded)
    return ordered


def _candidate_openclaw_homes() -> list[Path]:
    candidates: list[Path] = []
    for env_name in OPENCLAW_HOME_ENV_VARS:
        raw = str(os.environ.get(env_name) or "").strip()
        if raw:
            candidates.append(Path(raw).expanduser())
    for env_name in OPENCLAW_CONFIG_ENV_VARS:
        raw = str(os.environ.get(env_name) or "").strip()
        if raw:
            candidates.append(Path(raw).expanduser().parent)
    xdg_config_home = str(os.environ.get("XDG_CONFIG_HOME") or "").strip()
    if xdg_config_home:
        candidates.extend(
            [
                Path(xdg_config_home) / "openclaw",
                Path(xdg_config_home) / "OpenClaw",
            ]
        )
    for env_name in ("APPDATA", "LOCALAPPDATA"):
        base = str(os.environ.get(env_name) or "").strip()
        if not base:
            continue
        candidates.extend(
            [
                Path(base) / "openclaw",
                Path(base) / "OpenClaw",
            ]
        )
    candidates.extend(
        [
            Path.home() / ".config" / "openclaw",
            Path.home() / ".config" / "OpenClaw",
            Path.home() / ".openclaw",
        ]
    )
    return _dedupe_paths(candidates)


def openclaw_home() -> Path:
    for candidate in _candidate_openclaw_homes():
        if candidate.exists():
            return candidate
    candidates = _candidate_openclaw_homes()
    return candidates[0] if candidates else Path.home() / ".openclaw"


def agents_home() -> Path:
    return openclaw_home() / "agents"


def iso_from_ms(value: int | float | None) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc).isoformat()


def now_epoch_ms() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_default_agent() -> str:
    config_path = openclaw_home() / "openclaw.json"
    if not config_path.exists():
        return "codex"
    try:
        payload = read_json(config_path)
    except Exception:
        return "codex"
    acp = payload.get("acp")
    if isinstance(acp, dict):
        raw = str(acp.get("defaultAgent") or "").strip()
        if raw:
            return raw
    return "codex"


def agent_order(requested: str) -> list[str]:
    raw = (requested or "auto").strip().lower()
    if raw and raw != "auto":
        return [raw]
    preferred = load_default_agent()
    order = [preferred]
    for fallback in ("codex", "claude", "pi", "opencode", "gemini"):
        if fallback not in order:
            order.append(fallback)
    return order


def load_sessions(agent: str) -> dict[str, dict[str, Any]]:
    path = agents_home() / agent / "sessions" / "sessions.json"
    if not path.exists():
        return {}
    payload = read_json(path)
    if not isinstance(payload, dict):
        return {}
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def session_matches_key(session_key: str, target: str) -> bool:
    target = target.strip()
    return session_key == target or session_key.endswith(target)


@dataclass
class Candidate:
    agent: str
    session_key: str
    record: dict[str, Any]

    @property
    def updated_at(self) -> int:
        return int(self.record.get("updatedAt") or 0)

    @property
    def label(self) -> str:
        return str(self.record.get("label") or self.record.get("origin", {}).get("label") or "").strip()


def find_candidate(agent: str, sessions: dict[str, dict[str, Any]], session_key: str, label: str) -> Candidate | None:
    if session_key:
        for key, record in sessions.items():
            if session_matches_key(key, session_key):
                return Candidate(agent=agent, session_key=key, record=record)
        return None
    label_query = label.strip().lower()
    rows = [Candidate(agent=agent, session_key=key, record=record) for key, record in sessions.items()]
    if label_query:
        rows = [row for row in rows if label_query in row.label.lower()]
    if not rows:
        return None
    rows.sort(key=lambda row: row.updated_at, reverse=True)
    return rows[0]


def session_paths(candidate: Candidate) -> tuple[Path | None, Path | None]:
    sessions_dir = agents_home() / candidate.agent / "sessions"
    session_id = str(candidate.record.get("sessionId") or "").strip()
    transcript = None
    stream = None
    session_file = str(candidate.record.get("sessionFile") or "").strip()
    if session_file:
        transcript = Path(session_file)
    elif session_id:
        transcript = sessions_dir / f"{session_id}.jsonl"
    if session_id:
        stream = sessions_dir / f"{session_id}.acp-stream.jsonl"
    return transcript, stream


def read_jsonl_tail(path: Path | None, limit: int) -> list[dict[str, Any]]:
    if not path or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def flatten_message_content(message: Any) -> str:
    if isinstance(message, str):
        return message.strip()
    if isinstance(message, list):
        parts: list[str] = []
        for item in message:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text") or "").strip()
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    if isinstance(message, dict):
        return flatten_message_content(message.get("content"))
    return ""


def summarize_transcript(rows: list[dict[str, Any]], max_items: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for row in reversed(rows):
        if row.get("type") != "message":
            continue
        message = row.get("message")
        if not isinstance(message, dict):
            continue
        role = str(message.get("role") or "").strip()
        if role not in {"assistant", "user"}:
            continue
        text = flatten_message_content(message.get("content"))
        if not text:
            continue
        items.append(
            {
                "role": role,
                "timestamp": str(row.get("timestamp") or ""),
                "text": text[:600],
            }
        )
        if len(items) >= max_items:
            break
    items.reverse()
    return items


def summarize_stream(rows: list[dict[str, Any]]) -> dict[str, Any]:
    assistant_chunks: list[str] = []
    progress_events: list[str] = []
    lifecycle: list[dict[str, Any]] = []
    for row in rows:
        kind = str(row.get("kind") or "").strip()
        if kind == "assistant_delta":
            delta = str(row.get("delta") or "")
            if delta:
                assistant_chunks.append(delta)
        elif kind == "system_event":
            text = str(row.get("text") or "").strip()
            if text:
                progress_events.append(text)
        elif kind == "lifecycle":
            lifecycle.append(
                {
                    "phase": str(row.get("phase") or ""),
                    "ts": str(row.get("ts") or ""),
                    "epoch_ms": int(row.get("epochMs") or 0),
                }
            )
    assistant_text = "".join(assistant_chunks).strip()
    return {
        "assistant_tail": assistant_text[-600:],
        "last_progress": progress_events[-1] if progress_events else "",
        "lifecycle": lifecycle,
    }


def derive_status(candidate: Candidate, stream_summary: dict[str, Any]) -> tuple[str, bool]:
    acp = candidate.record.get("acp")
    if isinstance(acp, dict):
        state = str(acp.get("state") or "").strip().lower()
        if state == "running":
            return "running", True
        if state == "idle":
            return "idle", False
        if state:
            return state, state in {"running", "starting"}
    lifecycle = stream_summary.get("lifecycle") or []
    if lifecycle:
        last = lifecycle[-1]
        phase = str(last.get("phase") or "").strip().lower()
        if phase == "start":
            return "running", True
        if phase == "end":
            return "completed", False
    recent_ms = max(
        int(candidate.record.get("updatedAt") or 0),
        int(candidate.record.get("acp", {}).get("lastActivityAt") or 0) if isinstance(candidate.record.get("acp"), dict) else 0,
    )
    if recent_ms and now_epoch_ms() - recent_ms < 2 * 60 * 1000:
        return "active_recently", True
    return "unknown", False


def observe(agent: str, session_key: str, label: str, tail: int, transcript_items: int) -> dict[str, Any]:
    for item in agent_order(agent):
        sessions = load_sessions(item)
        candidate = find_candidate(item, sessions, session_key, label)
        if not candidate:
            continue
        transcript_path, stream_path = session_paths(candidate)
        transcript_rows = read_jsonl_tail(transcript_path, tail)
        stream_rows = read_jsonl_tail(stream_path, tail)
        stream_summary = summarize_stream(stream_rows)
        status, running = derive_status(candidate, stream_summary)
        acp = candidate.record.get("acp") if isinstance(candidate.record.get("acp"), dict) else {}
        return {
            "ok": True,
            "agent": candidate.agent,
            "session_key": candidate.session_key,
            "session_id": str(candidate.record.get("sessionId") or ""),
            "label": candidate.label,
            "status": status,
            "running": running,
            "updated_at": iso_from_ms(int(candidate.record.get("updatedAt") or 0)),
            "last_activity_at": iso_from_ms(int(acp.get("lastActivityAt") or 0)),
            "cwd": str(acp.get("cwd") or acp.get("runtimeOptions", {}).get("cwd") or ""),
            "mode": str(acp.get("mode") or ""),
            "observer": {
                "stream_file": str(stream_path) if stream_path and stream_path.exists() else "",
                "transcript_file": str(transcript_path) if transcript_path and transcript_path.exists() else "",
            },
            "recent_activity": {
                "last_progress": stream_summary.get("last_progress") or "",
                "assistant_tail": stream_summary.get("assistant_tail") or "",
                "messages": summarize_transcript(transcript_rows, transcript_items),
            },
        }
    return {
        "ok": False,
        "error": "session not found",
        "agent": agent,
        "session_key": session_key,
        "label": label,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe ACP session status from local OpenClaw state")
    parser.add_argument("--agent", default="auto", help="Agent id or auto")
    parser.add_argument("--session-key", default="", help="Exact session key or trailing session id")
    parser.add_argument("--label", default="", help="Session label substring")
    parser.add_argument("--tail", type=int, default=80, help="How many jsonl rows to inspect per file")
    parser.add_argument("--transcript-items", type=int, default=3, help="How many recent user/assistant messages to include")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = observe(args.agent, args.session_key.strip(), args.label.strip(), args.tail, args.transcript_items)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
