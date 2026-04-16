#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_PORT = 18789


def fail(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"config not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in config {path}: {exc}")


def find_config_path(explicit: Optional[str]) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_path = os.environ.get("OPENCLAW_CONFIG")
    if env_path:
        candidates.append(Path(env_path).expanduser())
    cwd_path = Path.cwd() / "openclaw.json"
    candidates.append(cwd_path)
    candidates.append(Path.home() / ".openclaw" / "openclaw.json")

    for candidate in candidates:
        if candidate.exists():
            return candidate
    fail("could not find openclaw.json; pass --config explicitly")


def trim(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def resolve_gateway_url(cfg: Dict[str, Any], explicit: Optional[str]) -> str:
    if explicit:
        return explicit.rstrip("/")
    env_url = trim(os.environ.get("OPENCLAW_GATEWAY_URL"))
    if env_url:
        return env_url.rstrip("/")

    gateway = cfg.get("gateway") or {}
    env_port = trim(os.environ.get("OPENCLAW_GATEWAY_PORT"))
    port = env_port or gateway.get("port") or DEFAULT_PORT
    return f"http://127.0.0.1:{port}"


def resolve_gateway_token(cfg: Dict[str, Any], explicit: Optional[str]) -> str:
    for value in (
        explicit,
        os.environ.get("OPENCLAW_GATEWAY_TOKEN"),
        os.environ.get("CLAWDBOT_GATEWAY_TOKEN"),
        ((cfg.get("gateway") or {}).get("auth") or {}).get("token"),
    ):
        token = trim(value)
        if token:
            return token
    fail("no gateway token found; set OPENCLAW_GATEWAY_TOKEN or gateway.auth.token")


def parse_args_json(raw: Optional[str], args_file: Optional[str]) -> Dict[str, Any]:
    if raw and args_file:
        fail("use either --args or --args-file, not both")
    if args_file:
        path = Path(args_file).expanduser()
        data = load_json(path)
    elif raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(f"invalid --args JSON: {exc}")
    else:
        data = {}

    if not isinstance(data, dict):
        fail("tool args must decode to a JSON object")
    return data


def parse_headers(items: list[str]) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    for item in items:
        if "=" not in item:
            fail(f"invalid --header value: {item!r}; expected NAME=VALUE")
        name, value = item.split("=", 1)
        name = name.strip()
        if not name:
            fail(f"invalid --header value: {item!r}; header name is empty")
        headers[name] = value
    return headers


def response_bytes(raw: str) -> int:
    return len(raw.encode("utf-8"))


def request_preview(
    body: Dict[str, Any],
    args: argparse.Namespace,
    extra_headers: Dict[str, str],
) -> Dict[str, Any]:
    preview: Dict[str, Any] = {
        "tool": body.get("tool"),
        "action": body.get("action"),
        "args": body.get("args"),
        "sessionKey": body.get("sessionKey"),
    }
    headers = {
        "message_channel": args.message_channel,
        "account_id": args.account_id,
        "message_to": args.message_to,
        "thread_id": args.thread_id,
    }
    if extra_headers:
        headers["extra"] = extra_headers
    preview["headers"] = {
        key: value for key, value in headers.items() if value not in (None, "", {})
    }
    return preview


def decode_json_response(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "error": {
                "type": "invalid_json",
                "message": f"gateway returned invalid JSON: {exc}",
                "body": raw,
            },
        }

    if isinstance(data, dict):
        return data

    return {
        "ok": False,
        "error": {
            "type": "unexpected_payload",
            "message": "gateway returned a non-object JSON payload",
            "body": data,
        },
    }


def extract_details(data: Dict[str, Any]) -> Any:
    if "details" in data:
        return data["details"]
    result = data.get("result")
    if isinstance(result, dict) and "details" in result:
        return result["details"]
    return None


def build_meta(
    *,
    gateway_url: str,
    status_code: int,
    raw: str,
    body: Dict[str, Any],
    action_mirrored: bool,
    response_content_type: Optional[str],
) -> Dict[str, Any]:
    request_args = body.get("args") if isinstance(body.get("args"), dict) else {}
    return {
        "endpoint": f"{gateway_url}/tools/invoke",
        "http_status": status_code,
        "response_bytes": response_bytes(raw),
        "response_content_type": response_content_type,
        "tool": body.get("tool"),
        "action": body.get("action"),
        "session_key": body.get("sessionKey"),
        "request_args_has_action": bool(request_args.get("action")),
        "action_mirrored_to_args": action_mirrored,
    }


def build_diagnosis(data: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    ok = data.get("ok")
    has_result = "result" in data

    if ok is True and has_result:
        return {
            "status": "ok",
            "message": "Gateway returned a result payload.",
        }

    if ok is True:
        next_steps = [
            "Verify _meta.request_args_has_action is true for feishu_task_* tools.",
            "If result is still missing, retry with --session-key main and any required headers such as --message-channel feishu --account-id cli-local.",
            "If the response still has ok=true without result, inspect the underlying tool implementation for a None/empty return.",
        ]
        if not meta.get("request_args_has_action"):
            next_steps.insert(
                0,
                "Re-run with --action <name> so the bridge can mirror action into args.action.",
            )
        return {
            "status": "missing_result",
            "message": "Gateway returned ok=true without a result payload.",
            "likely_causes": [
                "The tool accepted the request but returned no structured payload.",
                "The tool expected args.action but it was not present in the request body.",
                "Gateway/session policy allowed the call but the tool output was suppressed upstream.",
            ],
            "next_steps": next_steps,
        }

    if ok is False:
        return {
            "status": "tool_error",
            "message": "Gateway reported tool failure; inspect error/warning fields.",
        }

    return {
        "status": "unexpected_response",
        "message": "Gateway response did not match the expected {ok, result|error} envelope.",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Invoke a loaded OpenClaw tool through the local Gateway HTTP API."
    )
    parser.add_argument("--tool", required=True, help="Tool name, for example feishu_task_task")
    parser.add_argument("--action", help="Optional action field sent alongside the tool call")
    parser.add_argument("--args", help="JSON object string for tool args")
    parser.add_argument("--args-file", help="Path to a JSON file containing tool args")
    parser.add_argument("--session-key", help="Optional OpenClaw session key")
    parser.add_argument("--config", help="Path to openclaw.json")
    parser.add_argument("--gateway-url", help="Override gateway base URL, for example http://127.0.0.1:18789")
    parser.add_argument("--token", help="Override gateway token")
    parser.add_argument("--message-channel", help="Set X-OpenClaw-Message-Channel")
    parser.add_argument("--account-id", help="Set X-OpenClaw-Account-Id")
    parser.add_argument("--message-to", help="Set X-OpenClaw-Message-To")
    parser.add_argument("--thread-id", help="Set X-OpenClaw-Thread-Id")
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="Extra header as NAME=VALUE; can be used multiple times",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved request without sending it",
    )
    return parser


def mirror_action_into_args(
    tool_args: Dict[str, Any],
    action: Optional[str],
) -> tuple[Dict[str, Any], bool]:
    action_mirrored = False
    if action and "action" not in tool_args:
        tool_args["action"] = action
        action_mirrored = True
    return tool_args, action_mirrored


def build_request_body(
    args: argparse.Namespace,
    tool_args: Dict[str, Any],
) -> Dict[str, Any]:
    body: Dict[str, Any] = {"tool": args.tool, "args": tool_args}
    if args.action:
        body["action"] = args.action
    if args.session_key:
        body["sessionKey"] = args.session_key
    return body


def build_request_headers(
    args: argparse.Namespace,
    token: str,
    extra_headers: Dict[str, str],
) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if args.message_channel:
        headers["X-OpenClaw-Message-Channel"] = args.message_channel
    if args.account_id:
        headers["X-OpenClaw-Account-Id"] = args.account_id
    if args.message_to:
        headers["X-OpenClaw-Message-To"] = args.message_to
    if args.thread_id:
        headers["X-OpenClaw-Thread-Id"] = args.thread_id
    headers.update(extra_headers)
    return headers


def build_dry_run_preview(
    *,
    config_path: Path,
    gateway_url: str,
    headers: Dict[str, str],
    body: Dict[str, Any],
    args: argparse.Namespace,
    extra_headers: Dict[str, str],
    action_mirrored: bool,
) -> Dict[str, Any]:
    return {
        "config": str(config_path),
        "url": f"{gateway_url}/tools/invoke",
        "headers": {
            key: ("<redacted>" if key.lower() == "authorization" else value)
            for key, value in headers.items()
        },
        "body": body,
        "request": request_preview(body, args, extra_headers),
        "action_mirrored_to_args": action_mirrored,
    }


def build_success_payload(
    *,
    raw: str,
    response: Any,
    gateway_url: str,
    body: Dict[str, Any],
    action_mirrored: bool,
    args: argparse.Namespace,
    extra_headers: Dict[str, str],
) -> Dict[str, Any]:
    data = decode_json_response(raw)
    meta = build_meta(
        gateway_url=gateway_url,
        status_code=response.status,
        raw=raw,
        body=body,
        action_mirrored=action_mirrored,
        response_content_type=response.headers.get("Content-Type"),
    )
    if data.get("ok") is True and "result" not in data:
        data = {
            **data,
            "warning": "gateway returned ok=true without result payload; inspect _diagnosis.next_steps",
        }
    details = extract_details(data)
    if details is not None and "details" not in data:
        data["details"] = details
    data["_request"] = request_preview(body, args, extra_headers)
    data["_meta"] = meta
    data["_diagnosis"] = build_diagnosis(data, meta)
    return data


def build_http_error_payload(
    *,
    exc: urllib.error.HTTPError,
    gateway_url: str,
    body: Dict[str, Any],
    action_mirrored: bool,
    args: argparse.Namespace,
    extra_headers: Dict[str, str],
) -> Dict[str, Any]:
    body_text = exc.read().decode("utf-8", errors="replace")
    return {
        "ok": False,
        "error": {
            "type": "http_error",
            "status_code": exc.code,
            "reason": str(exc.reason),
            "body": body_text,
        },
        "_request": request_preview(body, args, extra_headers),
        "_meta": build_meta(
            gateway_url=gateway_url,
            status_code=exc.code,
            raw=body_text,
            body=body,
            action_mirrored=action_mirrored,
            response_content_type=exc.headers.get("Content-Type") if exc.headers else None,
        ),
        "_diagnosis": {
            "status": "http_error",
            "message": "Gateway returned a non-2xx HTTP response.",
            "next_steps": [
                "Check gateway auth token and local gateway status.",
                "Inspect error.body for plugin-specific failure details.",
            ],
        },
    }


def build_network_error_payload(
    *,
    exc: urllib.error.URLError,
    body: Dict[str, Any],
    args: argparse.Namespace,
    extra_headers: Dict[str, str],
) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "type": "network_error",
            "reason": str(exc.reason),
        },
        "_request": request_preview(body, args, extra_headers),
        "_diagnosis": {
            "status": "network_error",
            "message": "Gateway request failed before receiving an HTTP response.",
            "next_steps": [
                "Confirm the local OpenClaw Gateway is running.",
                "Check OPENCLAW_GATEWAY_URL / gateway.port and token settings.",
            ],
        },
    }


def prepare_gateway_request(
    args: argparse.Namespace,
) -> tuple[Path, str, Dict[str, Any], Dict[str, str], Dict[str, Any], bool]:
    config_path = find_config_path(args.config)
    cfg = load_json(config_path)
    gateway_url = resolve_gateway_url(cfg, args.gateway_url)
    token = resolve_gateway_token(cfg, args.token)
    tool_args = parse_args_json(args.args, args.args_file)
    tool_args, action_mirrored = mirror_action_into_args(tool_args, args.action)
    body = build_request_body(args, tool_args)
    extra_headers = parse_headers(args.header)
    headers = build_request_headers(args, token, extra_headers)
    return config_path, gateway_url, body, headers, extra_headers, action_mirrored


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config_path, gateway_url, body, headers, extra_headers, action_mirrored = prepare_gateway_request(args)

    if args.dry_run:
        preview = build_dry_run_preview(
            config_path=config_path,
            gateway_url=gateway_url,
            headers=headers,
            body=body,
            args=args,
            extra_headers=extra_headers,
            action_mirrored=action_mirrored,
        )
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return

    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        f"{gateway_url}/tools/invoke",
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            raw = response.read().decode("utf-8")
            payload = build_success_payload(
                raw=raw,
                response=response,
                gateway_url=gateway_url,
                body=body,
                action_mirrored=action_mirrored,
                args=args,
                extra_headers=extra_headers,
            )
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            if payload.get("ok") is False:
                raise SystemExit(1)
    except urllib.error.HTTPError as exc:
        payload = build_http_error_payload(
            exc=exc,
            gateway_url=gateway_url,
            body=body,
            action_mirrored=action_mirrored,
            args=args,
            extra_headers=extra_headers,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(exc.code)
    except urllib.error.URLError as exc:
        payload = build_network_error_payload(
            exc=exc,
            body=body,
            args=args,
            extra_headers=extra_headers,
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
