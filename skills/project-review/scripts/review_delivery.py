#!/usr/bin/env python3
"""Deliver project-review cards to Feishu through the OpenClaw bot channel."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from feishu_card_renderer import build_feishu_card
from review_state_store import append_history, default_state_path, get_review_by_id, load_state, update_review_status


REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_ROOT = Path(__file__).resolve().parents[2]
PM_SCRIPTS_ROOT = SKILLS_ROOT / "pm" / "scripts"
DEFAULT_OPENCLAW_BIN = "openclaw"
BRIDGE_SCRIPT_CANDIDATES = (
    SKILLS_ROOT / "openclaw-lark-bridge" / "scripts" / "invoke_openclaw_tool.py",
    Path.home() / ".codex" / "skills" / "openclaw-lark-bridge" / "scripts" / "invoke_openclaw_tool.py",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _extract_last_json_object(raw: str) -> dict[str, Any]:
    lines = str(raw or "").splitlines()
    for index in range(len(lines)):
        candidate = "\n".join(lines[index:]).strip()
        if not candidate.startswith("{"):
            continue
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("bridge output does not contain a JSON object")


def _resolve_bridge_script() -> Path | None:
    for candidate in BRIDGE_SCRIPT_CANDIDATES:
        expanded = candidate.expanduser()
        if expanded.exists():
            return expanded
    return None


def _bridge_details(payload: dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload.get("details"), dict):
        return payload["details"]
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("details"), dict):
        return result["details"]
    return {}


def _load_pm_module() -> Any:
    pm_root = str(PM_SCRIPTS_ROOT.resolve())
    if pm_root not in sys.path:
        sys.path.insert(0, pm_root)
    import pm  # type: ignore

    return pm


def _best_error_message(stdout: str, stderr: str) -> str:
    for raw in (stderr, stdout):
        if not str(raw or "").strip():
            continue
        try:
            payload = _extract_last_json_object(raw)
        except ValueError:
            payload = {}
        if payload:
            error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
            details = _bridge_details(payload)
            if isinstance(details.get("error"), str) and details.get("error").strip():
                return str(details.get("error")).strip()
            for candidate in (
                error.get("body"),
                error.get("reason"),
                error.get("message"),
                payload.get("message"),
            ):
                text = str(candidate or "").strip()
                if text:
                    return text

    combined = "\n".join(part.strip() for part in (stderr, stdout) if str(part or "").strip())
    for line in reversed(combined.splitlines()):
        stripped = line.strip()
        if stripped.startswith("Error: "):
            return stripped[len("Error: ") :].strip()

    patterns = (
        r"Bot/User can NOT be out of the chat\.",
        r"应用缺少权限\s*\[[^\]]+\][^。\n]*。?",
        r"Request failed with status code \d+",
    )
    for pattern in patterns:
        match = re.search(pattern, combined)
        if match:
            return match.group(0).strip()

    return combined.strip() or "openclaw message send failed"


def _build_send_command(chat_id: str, card: dict[str, Any], *, openclaw_bin: str) -> list[str]:
    return [
        openclaw_bin,
        "message",
        "send",
        "--channel",
        "feishu",
        "--target",
        f"chat:{chat_id}",
        "--card",
        json.dumps(card, ensure_ascii=False),
        "--json",
    ]


def _invoke_openclaw_send(
    *,
    chat_id: str,
    card: dict[str, Any],
    openclaw_bin: str = DEFAULT_OPENCLAW_BIN,
) -> dict[str, Any]:
    command = _build_send_command(chat_id, card, openclaw_bin=openclaw_bin)
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(_best_error_message(completed.stdout, completed.stderr))
    envelope = _extract_last_json_object(completed.stdout)
    delivery = envelope.get("payload") if isinstance(envelope.get("payload"), dict) else {}
    if envelope.get("action") != "send" or delivery.get("ok") is not True:
        raise RuntimeError(str(delivery or envelope))
    message_id = str(delivery.get("messageId") or "").strip()
    if not message_id:
        raise RuntimeError("openclaw message send returned no messageId")
    return {
        "tool": "openclaw.message.send",
        "chat_id": str(delivery.get("chatId") or chat_id).strip(),
        "message_id": message_id,
    }


def _invoke_lark_bridge_user_send(
    *,
    chat_id: str,
    card: dict[str, Any],
    review_id: str,
) -> dict[str, Any]:
    bridge_script = _resolve_bridge_script()
    if bridge_script is None:
        raise RuntimeError("openclaw-lark-bridge script not found")

    args = {
        "receive_id_type": "chat_id",
        "receive_id": chat_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
        "uuid": f"project-review-{review_id}",
    }
    command = [
        sys.executable,
        str(bridge_script),
        "--tool",
        "feishu_im_user_message",
        "--action",
        "send",
        "--session-key",
        "main",
        "--args",
        json.dumps(args, ensure_ascii=False),
    ]
    completed = subprocess.run(
        command,
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(_best_error_message(completed.stdout, completed.stderr))

    payload = _extract_last_json_object(completed.stdout)
    details = _bridge_details(payload)
    error_text = str(details.get("error") or "").strip()
    if error_text:
        raise RuntimeError(error_text)

    message_id = str(details.get("message_id") or "").strip()
    if not message_id:
        raise RuntimeError("openclaw-lark bridge returned no message_id")
    return {
        "tool": "openclaw-lark.feishu_im_user_message.send",
        "chat_id": str(details.get("chat_id") or chat_id).strip(),
        "message_id": message_id,
    }


def _invoke_pm_user_token_send(
    *,
    chat_id: str,
    card: dict[str, Any],
    review_id: str,
) -> dict[str, Any]:
    pm = _load_pm_module()
    token_result = pm.ensure_attachment_token(("im:message", "im:message.send_as_user", "offline_access"))
    if str(token_result.get("status") or "").strip() != "authorized":
        verification_url = str(token_result.get("verification_uri_complete") or "").strip()
        if verification_url:
            raise RuntimeError(f"需要重新完成用户授权：{verification_url}")
        raise RuntimeError(str(token_result.get("status") or "user token unavailable"))

    token_payload = token_result.get("token") if isinstance(token_result.get("token"), dict) else {}
    access_token = str(token_payload.get("access_token") or "").strip()
    if not access_token:
        raise RuntimeError("PM user token missing access_token")

    openapi_base = str(pm.feishu_credentials().get("openapi_base") or "").rstrip("/")
    if not openapi_base:
        raise RuntimeError("PM feishu credentials missing openapi_base")

    body = json.dumps(
        {
            "receive_id": chat_id,
            "msg_type": "interactive",
            "content": json.dumps(card, ensure_ascii=False),
            "uuid": f"project-review-{review_id}",
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{openapi_base}/open-apis/im/v1/messages?receive_id_type=chat_id",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = int(getattr(response, "status", 200))
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        status = int(exc.code)
        raw = exc.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"PM token直发返回非 JSON：{raw[:200]}") from exc

    if status >= 400 or int(payload.get("code") or 0) != 0:
        message = str(payload.get("msg") or raw or "PM token send failed").strip()
        raise RuntimeError(message)

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    message_id = str(data.get("message_id") or "").strip()
    if not message_id:
        raise RuntimeError("PM token直发返回缺少 message_id")
    return {
        "tool": "pm.user_token.im.message.create",
        "chat_id": str(data.get("chat_id") or chat_id).strip(),
        "message_id": message_id,
    }


def _load_review_record(state_path: str | Path, review_id: str) -> dict[str, Any]:
    state = load_state(state_path)
    record = get_review_by_id(state, review_id)
    if record is None:
        raise KeyError(f"review_id not found: {review_id}")
    return record


def send_review_card(
    review_id: str,
    *,
    state_path: str | Path | None = None,
    openclaw_bin: str = DEFAULT_OPENCLAW_BIN,
    now_iso: str | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    resolved_state_path = Path(state_path or default_state_path()).resolve()
    record = _load_review_record(resolved_state_path, review_id)
    chat_id = str(record.get("channel_id") or "").strip()
    if not chat_id:
        raise ValueError("review record is missing channel_id")
    reviewer_requests = record.get("reviewer_requests") if isinstance(record.get("reviewer_requests"), list) else []
    if (
        str(record.get("card_kind") or "").strip() == "code_health_risk_card_v1"
        and reviewer_requests
        and not bool(record.get("llm_ready"))
    ):
        raise RuntimeError("code-health review 还没完成，暂不发送卡片")

    card = build_feishu_card(record)
    existing_delivery = record.get("delivery") if isinstance(record.get("delivery"), dict) else {}
    if existing_delivery.get("message_id") and not force and not dry_run:
        return {
            "ok": True,
            "review_id": review_id,
            "chat_id": chat_id,
            "reused_existing": True,
            "delivery": existing_delivery,
            "card": card,
            "state_path": str(resolved_state_path),
        }

    if dry_run:
        return {
            "ok": True,
            "review_id": review_id,
            "chat_id": chat_id,
            "reused_existing": False,
            "delivery": {},
            "card": card,
            "state_path": str(resolved_state_path),
            "command_preview": _build_send_command(chat_id, card, openclaw_bin=openclaw_bin),
        }

    try:
        result = _invoke_openclaw_send(
            chat_id=chat_id,
            card=card,
            openclaw_bin=openclaw_bin,
        )
    except RuntimeError as direct_error:
        direct_message = str(direct_error).strip()
        should_try_bridge = "out of the chat" in direct_message.lower()
        if not should_try_bridge:
            raise
        try:
            result = _invoke_lark_bridge_user_send(
                chat_id=chat_id,
                card=card,
                review_id=review_id,
            )
        except RuntimeError as bridge_error:
            bridge_message = str(bridge_error).strip()
            try:
                result = _invoke_pm_user_token_send(
                    chat_id=chat_id,
                    card=card,
                    review_id=review_id,
                )
            except RuntimeError as pm_error:
                raise RuntimeError(
                    f"bot直发失败：{direct_message}；用户桥接补发失败：{bridge_message}；PM token直发失败：{str(pm_error).strip()}"
                ) from pm_error

    normalized_now = str(now_iso or _now_iso())
    delivery = {
        "tool": str(result.get("tool") or "openclaw.message.send"),
        "chat_id": str(result.get("chat_id") or chat_id).strip(),
        "message_id": str(result.get("message_id") or "").strip(),
        "sent_at": normalized_now,
    }

    update_review_status(
        resolved_state_path,
        review_id,
        status="sent",
        updated_at=normalized_now,
        extra={
            "sent_at": normalized_now,
            "card_sent": card,
            "delivery": delivery,
        },
    )
    append_history(
        resolved_state_path,
        review_id,
        {
            "event": "delivered",
            "at": normalized_now,
            "delivery": delivery,
        },
    )
    return {
        "ok": True,
        "review_id": review_id,
        "chat_id": delivery["chat_id"],
        "reused_existing": False,
        "delivery": delivery,
        "card": card,
        "state_path": str(resolved_state_path),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send one prepared project-review record to Feishu.")
    parser.add_argument("--review-id", required=True, help="Review record id to deliver")
    parser.add_argument("--state-path", help="Optional state file path. Defaults to .pm/project-review-state.json")
    parser.add_argument("--openclaw-bin", default=DEFAULT_OPENCLAW_BIN, help="OpenClaw CLI binary")
    parser.add_argument("--now-iso", help="Optional ISO8601 timestamp")
    parser.add_argument("--force", action="store_true", help="Resend even if this review already has a message_id")
    parser.add_argument("--dry-run", action="store_true", help="Only print the card and command preview without sending")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = send_review_card(
        args.review_id,
        state_path=args.state_path,
        openclaw_bin=args.openclaw_bin,
        now_iso=args.now_iso,
        force=args.force,
        dry_run=args.dry_run,
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
