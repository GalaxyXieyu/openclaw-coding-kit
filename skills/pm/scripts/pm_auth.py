from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional, Sequence
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Shanghai")
FindConfigFn = Callable[[], Optional[Path]]


def unix_ts() -> int:
    return int(datetime.now(TZ).timestamp())


def _ensure_state_dir(state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(state_dir, 0o700)
    except OSError:
        pass


def _load_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _save_json_file(state_dir: Path, path: Path, payload: dict[str, Any]) -> None:
    _ensure_state_dir(state_dir)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _remove_file(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def get_channel_app_info(find_openclaw_config_path: FindConfigFn) -> dict[str, str]:
    path = find_openclaw_config_path()
    if not path:
        raise SystemExit("openclaw.json not found for auth-link generation")
    payload = json.loads(path.read_text(encoding="utf-8"))
    channels = payload.get("channels") or {}
    feishu_cfg = channels.get("feishu") if isinstance(channels, dict) and isinstance(channels.get("feishu"), dict) else channels
    app_id = str((feishu_cfg or {}).get("appId") or "").strip()
    brand = str((feishu_cfg or {}).get("domain") or "feishu").strip() or "feishu"
    if not app_id:
        raise SystemExit(f"appId missing in {path}")
    open_domain = "https://open.larksuite.com" if brand == "lark" else "https://open.feishu.cn"
    return {
        "config_path": str(path),
        "app_id": app_id,
        "brand": brand,
        "open_domain": open_domain,
    }


def build_auth_link(find_openclaw_config_path: FindConfigFn, *, scopes: list[str], token_type: str = "user") -> dict[str, Any]:
    info = get_channel_app_info(find_openclaw_config_path)
    scope_q = ",".join([s for s in scopes if s])
    auth_url = f"{info['open_domain']}/app/{info['app_id']}/auth?q={urllib.parse.quote(scope_q)}&op_from=pm&token_type={token_type}"
    permission_url = f"{info['open_domain']}/app/{info['app_id']}/permission"
    return {
        **info,
        "mode": "app-scope",
        "scopes": scopes,
        "token_type": token_type,
        "auth_url": auth_url,
        "permission_url": permission_url,
    }


def request_user_oauth_link(find_openclaw_config_path: FindConfigFn, *, scopes: list[str]) -> dict[str, Any]:
    info = get_channel_app_info(find_openclaw_config_path)
    path = Path(info["config_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    channels = payload.get("channels") or {}
    feishu_cfg = channels.get("feishu") if isinstance(channels, dict) and isinstance(channels.get("feishu"), dict) else channels
    app_secret = str((feishu_cfg or {}).get("appSecret") or "").strip()
    if not app_secret:
        raise SystemExit(f"appSecret missing in {path}")
    brand = info["brand"]
    device_auth_url = "https://accounts.larksuite.com/oauth/v1/device_authorization" if brand == "lark" else "https://accounts.feishu.cn/oauth/v1/device_authorization"
    effective_scopes = list(scopes)
    if "offline_access" not in effective_scopes:
        effective_scopes.append("offline_access")
    basic_auth = base64.b64encode(f"{info['app_id']}:{app_secret}".encode("utf-8")).decode("ascii")
    body = urllib.parse.urlencode({"client_id": info["app_id"], "scope": " ".join(effective_scopes)}).encode("utf-8")
    req = urllib.request.Request(
        device_auth_url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {basic_auth}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"device authorization failed: HTTP {exc.code} {raw[:500]}") from exc
    data = json.loads(raw)
    verification_url = str(data.get("verification_uri_complete") or data.get("verification_uri") or "").strip()
    if not verification_url:
        raise SystemExit(f"device authorization returned no verification URL: {raw[:500]}")
    return {
        **info,
        "mode": "user-oauth",
        "scopes": effective_scopes,
        "device_authorization_url": device_auth_url,
        "verification_url": verification_url,
        "user_code": str(data.get("user_code") or ""),
        "expires_in": int(data.get("expires_in") or 0),
        "interval": int(data.get("interval") or 0),
    }


def openclaw_config(config_paths: Sequence[Path]) -> dict[str, Any]:
    explicit = os.environ.get("OPENCLAW_CONFIG", "").strip()
    candidates = [Path(explicit).expanduser()] if explicit else []
    explicit_home = os.environ.get("OPENCLAW_HOME", "").strip()
    if explicit_home:
        candidates.append(Path(explicit_home).expanduser() / "openclaw.json")
    candidates.extend(config_paths)
    for candidate in candidates:
        if not candidate.exists():
            continue
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    raise SystemExit(
        "openclaw.json not found; set OPENCLAW_CONFIG or OPENCLAW_HOME, "
        "or keep a config in repo-local ./openclaw.json / ./.openclaw/openclaw.json "
        "or a user-global OpenClaw config directory"
    )


def feishu_credentials(config_paths: Sequence[Path]) -> dict[str, str]:
    cfg = openclaw_config(config_paths)
    section = ((cfg.get("channels") or {}).get("feishu") or {})
    app_id = str(section.get("appId") or "").strip()
    app_secret = str(section.get("appSecret") or "").strip()
    domain = str(section.get("domain") or "feishu").strip() or "feishu"
    if not app_id or not app_secret:
        raise SystemExit("missing channels.feishu.appId/appSecret in openclaw.json")
    if domain == "lark":
        accounts_base = "https://accounts.larksuite.com"
        openapi_base = "https://open.larksuite.com"
    else:
        accounts_base = "https://accounts.feishu.cn"
        openapi_base = "https://open.feishu.cn"
    return {
        "app_id": app_id,
        "app_secret": app_secret,
        "accounts_base": accounts_base,
        "openapi_base": openapi_base,
    }


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    form: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any], str]:
    if form is not None and body is not None:
        raise SystemExit("request_json does not allow both form and raw body")
    encoded = body
    request_headers = dict(headers or {})
    if form is not None:
        encoded = urllib.parse.urlencode(form).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    request = urllib.request.Request(url, data=encoded, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            status = int(getattr(response, "status", 200))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        status = int(exc.code)
    except urllib.error.URLError as exc:
        raise SystemExit(f"request failed for {url}: {exc.reason}") from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = {}
    return status, payload if isinstance(payload, dict) else {}, raw


def _token_scope_set(payload: dict[str, Any]) -> set[str]:
    scope = str(payload.get("scope") or "").strip()
    return {item for item in scope.split() if item}


def _token_covers(payload: dict[str, Any], required_scopes: tuple[str, ...]) -> bool:
    scopes = _token_scope_set(payload)
    return all(scope in scopes for scope in required_scopes)


def _token_is_valid(payload: dict[str, Any]) -> bool:
    expires_at = int(payload.get("expires_at") or 0)
    return expires_at > (unix_ts() + 300)


def _refresh_is_valid(payload: dict[str, Any]) -> bool:
    refresh_expires_at = int(payload.get("refresh_expires_at") or 0)
    refresh_token = str(payload.get("refresh_token") or "").strip()
    return bool(refresh_token) and refresh_expires_at > (unix_ts() + 300)


def _fetch_user_identity(access_token: str, creds: dict[str, str]) -> dict[str, Any]:
    status, payload, raw = request_json(
        f"{creds['openapi_base']}/open-apis/authen/v1/user_info",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if status >= 400 or int(payload.get("code") or 0) != 0:
        raise SystemExit(f"failed to verify Feishu OAuth user identity: {raw}")
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _build_saved_token(token_payload: dict[str, Any], creds: dict[str, str]) -> dict[str, Any]:
    access_token = str(token_payload.get("access_token") or "").strip()
    refresh_token = str(token_payload.get("refresh_token") or "").strip()
    if not access_token:
        raise SystemExit("missing access_token in OAuth response")
    identity = _fetch_user_identity(access_token, creds)
    granted_at = unix_ts()
    expires_in = int(token_payload.get("expires_in") or 0)
    refresh_expires_in = int(token_payload.get("refresh_token_expires_in") or 0)
    return {
        "app_id": creds["app_id"],
        "scope": str(token_payload.get("scope") or "").strip(),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": granted_at + expires_in,
        "refresh_expires_at": granted_at + refresh_expires_in,
        "granted_at": granted_at,
        "open_id": str(identity.get("open_id") or "").strip(),
        "name": str(identity.get("name") or identity.get("en_name") or "").strip(),
    }


def _request_device_authorization(required_scopes: tuple[str, ...], creds: dict[str, str], *, state_dir: Path, pending_auth_path: Path) -> dict[str, Any]:
    auth_header = base64.b64encode(f"{creds['app_id']}:{creds['app_secret']}".encode("utf-8")).decode("utf-8")
    status, payload, raw = request_json(
        f"{creds['accounts_base']}/oauth/v1/device_authorization",
        method="POST",
        headers={"Authorization": f"Basic {auth_header}"},
        form={"client_id": creds["app_id"], "scope": " ".join(required_scopes)},
    )
    if status >= 400 or "device_code" not in payload:
        raise SystemExit(f"failed to request Feishu device authorization: {raw}")
    pending = {
        "app_id": creds["app_id"],
        "scopes": list(required_scopes),
        "device_code": str(payload.get("device_code") or "").strip(),
        "user_code": str(payload.get("user_code") or "").strip(),
        "verification_uri": str(payload.get("verification_uri") or "").strip(),
        "verification_uri_complete": str(payload.get("verification_uri_complete") or payload.get("verification_uri") or "").strip(),
        "interval": int(payload.get("interval") or 5),
        "created_at": unix_ts(),
        "expires_at": unix_ts() + int(payload.get("expires_in") or 180),
    }
    _save_json_file(state_dir, pending_auth_path, pending)
    return pending


def _refresh_access_token(saved_token: dict[str, Any], creds: dict[str, str], *, state_dir: Path, token_path: Path, pending_auth_path: Path) -> dict[str, Any] | None:
    if not _refresh_is_valid(saved_token):
        return None
    status, payload, _ = request_json(
        f"{creds['openapi_base']}/open-apis/authen/v2/oauth/token",
        method="POST",
        form={
            "grant_type": "refresh_token",
            "refresh_token": str(saved_token.get("refresh_token") or ""),
            "client_id": creds["app_id"],
            "client_secret": creds["app_secret"],
        },
    )
    if status >= 400 or "access_token" not in payload:
        return None
    refreshed = _build_saved_token(payload, creds)
    _save_json_file(state_dir, token_path, refreshed)
    _remove_file(pending_auth_path)
    return refreshed


def _poll_pending_device_authorization(pending: dict[str, Any], creds: dict[str, str], *, state_dir: Path, token_path: Path, pending_auth_path: Path) -> dict[str, Any] | None:
    if int(pending.get("expires_at") or 0) <= unix_ts():
        _remove_file(pending_auth_path)
        return None
    status, payload, _ = request_json(
        f"{creds['openapi_base']}/open-apis/authen/v2/oauth/token",
        method="POST",
        form={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": str(pending.get("device_code") or ""),
            "client_id": creds["app_id"],
            "client_secret": creds["app_secret"],
        },
    )
    if status >= 400 and "access_token" not in payload:
        error_code = str(payload.get("error") or "").strip()
        if error_code in {"authorization_pending", "slow_down"}:
            return {
                "status": "authorization_required",
                "verification_uri_complete": pending.get("verification_uri_complete") or "",
                "user_code": pending.get("user_code") or "",
                "expires_at": pending.get("expires_at") or 0,
                "scopes": pending.get("scopes") or [],
            }
        _remove_file(pending_auth_path)
        return None
    if "access_token" not in payload:
        return {
            "status": "authorization_required",
            "verification_uri_complete": pending.get("verification_uri_complete") or "",
            "user_code": pending.get("user_code") or "",
            "expires_at": pending.get("expires_at") or 0,
            "scopes": pending.get("scopes") or [],
        }
    saved = _build_saved_token(payload, creds)
    _save_json_file(state_dir, token_path, saved)
    _remove_file(pending_auth_path)
    return {"status": "authorized", "token": saved}


def ensure_attachment_token(
    *,
    state_dir: Path,
    token_path: Path,
    pending_auth_path: Path,
    required_scopes: tuple[str, ...],
    config_paths: Sequence[Path],
) -> dict[str, Any]:
    creds = feishu_credentials(config_paths)
    saved = _load_json_file(token_path)
    if isinstance(saved, dict) and str(saved.get("app_id") or "") == creds["app_id"]:
        if _token_covers(saved, required_scopes) and _token_is_valid(saved):
            return {"status": "authorized", "token": saved}
        refreshed = _refresh_access_token(saved, creds, state_dir=state_dir, token_path=token_path, pending_auth_path=pending_auth_path) if _token_covers(saved, required_scopes) else None
        if refreshed and _token_is_valid(refreshed):
            return {"status": "authorized", "token": refreshed}
    pending = _load_json_file(pending_auth_path)
    if isinstance(pending, dict) and str(pending.get("app_id") or "") == creds["app_id"]:
        pending_result = _poll_pending_device_authorization(pending, creds, state_dir=state_dir, token_path=token_path, pending_auth_path=pending_auth_path)
        if pending_result:
            return pending_result
    fresh_pending = _request_device_authorization(required_scopes, creds, state_dir=state_dir, pending_auth_path=pending_auth_path)
    return {
        "status": "authorization_required",
        "verification_uri_complete": fresh_pending.get("verification_uri_complete") or "",
        "user_code": fresh_pending.get("user_code") or "",
        "expires_at": fresh_pending.get("expires_at") or 0,
        "scopes": fresh_pending.get("scopes") or [],
    }
