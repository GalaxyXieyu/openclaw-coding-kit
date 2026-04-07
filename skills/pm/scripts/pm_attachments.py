from __future__ import annotations

import mimetypes
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Optional, Tuple

EnsureAttachmentTokenFn = Callable[[], dict[str, Any]]
BuildAuthLinkFn = Callable[..., dict[str, Any]]
RequestUserOAuthLinkFn = Callable[..., dict[str, Any]]
TaskIdForOutputFn = Callable[[str], str]
EnsureTaskStartedFn = Callable[[dict[str, Any]], Optional[dict[str, Any]]]
FeishuCredentialsFn = Callable[[], dict[str, str]]
RequestJsonFn = Callable[..., Tuple[int, dict[str, Any], str]]


def task_id_for_output(task_id: str, *, normalize_task_key_fn: Callable[[str], str]) -> str:
    return normalize_task_key_fn(task_id) if task_id else ""


def sanitize_filename(name: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w.\-]+", "_", (name or "").strip(), flags=re.UNICODE).strip("._")
    return cleaned or fallback


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def http_get_bytes(url: str, *, timeout: int = 60) -> Tuple[int, bytes, str]:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
            status = int(getattr(response, "status", 200))
            content_type = str(response.headers.get("Content-Type") or "")
            return status, data, content_type
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read(), str(exc.headers.get("Content-Type") or "")
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to download attachment URL: {exc.reason}") from exc


def attachment_auth_result(
    task: dict[str, Any],
    task_id: str,
    *,
    task_id_for_output_fn: TaskIdForOutputFn,
    ensure_attachment_token: EnsureAttachmentTokenFn,
    build_auth_link: BuildAuthLinkFn,
    request_user_oauth_link: RequestUserOAuthLinkFn,
) -> dict[str, Any]:
    task_guid = str(task.get("guid") or "").strip()
    scopes = ["task:task:read", "task:attachment:read", "task:attachment:write", "offline_access"]
    try:
        token = ensure_attachment_token()
        return {
            "status": "authorized",
            "task_id": task_id_for_output_fn(task_id),
            "task_guid": task_guid,
            "token": str(token.get("access_token") or "").strip(),
            "token_payload": token,
        }
    except SystemExit as exc:
        message = str(exc)
        return {
            "status": "authorization_required",
            "task_id": task_id_for_output_fn(task_id),
            "task_guid": task_guid,
            "message": message,
            "auth": build_auth_link(scopes=scopes, token_type="user"),
            "oauth": request_user_oauth_link(scopes=scopes),
        }


def resolve_upload_files(paths: list[str]) -> list[Path]:
    resolved: list[Path] = []
    for raw in paths:
        path = Path(raw).expanduser()
        if not path.exists():
            raise SystemExit(f"upload file not found: {path}")
        if not path.is_file():
            raise SystemExit(f"upload path is not a file: {path}")
        size = path.stat().st_size
        if size > 50 * 1024 * 1024:
            raise SystemExit(f"upload file exceeds 50MB limit: {path}")
        resolved.append(path)
    if not resolved:
        raise SystemExit("at least one --file is required")
    return resolved


def chunked_files(files: list[Path], size: int = 5) -> list[list[Path]]:
    return [files[index : index + size] for index in range(0, len(files), size)]


def build_multipart_body(resource_id: str, files: list[Path]) -> Tuple[bytes, str]:
    boundary = f"----CodexFeishuTaskflow{uuid.uuid4().hex}"
    chunks: list[bytes] = []

    def add_field(name: str, value: str) -> None:
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")

    add_field("resource_type", "task")
    add_field("resource_id", resource_id)
    for path in files:
        mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append((f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n' f"Content-Type: {mime_type}\r\n\r\n").encode("utf-8"))
        chunks.append(path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), boundary


def list_task_attachments(
    task: dict[str, Any],
    task_id: str,
    download_dir: str,
    *,
    task_id_for_output_fn: TaskIdForOutputFn,
    attachment_auth_result_fn: Callable[[dict[str, Any], str], dict[str, Any]],
    feishu_credentials: FeishuCredentialsFn,
    request_json: RequestJsonFn,
) -> dict[str, Any]:
    auth = attachment_auth_result_fn(task, task_id)
    if auth.get("status") != "authorized":
        return auth

    token = str(auth.get("token") or "").strip()
    task_guid = str(task.get("guid") or "").strip()
    openapi_base = feishu_credentials()["openapi_base"]
    params = urllib.parse.urlencode({"resource_id": task_guid, "resource_type": "task"})
    status, payload, raw = request_json(f"{openapi_base}/open-apis/task/v2/attachments?{params}", headers={"Authorization": f"Bearer {token}"})
    if status >= 400 or int(payload.get("code") or 0) != 0:
        raise SystemExit(f"failed to list task attachments: {raw}")

    data = payload.get("data")
    items = list((data or {}).get("items") or []) if isinstance(data, dict) else []
    downloads: list[dict[str, Any]] = []
    if download_dir:
        output_dir = Path(download_dir).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            file_name = sanitize_filename(str(item.get("name") or ""), f"attachment_{index}")
            saved_path = output_dir / file_name
            download_url = str(item.get("url") or "").strip()
            if not download_url:
                downloads.append({"index": index, "name": file_name, "saved_path": str(saved_path), "error": "missing_download_url"})
                continue
            file_status, body, content_type = http_get_bytes(download_url)
            if file_status >= 400:
                downloads.append({"index": index, "name": file_name, "saved_path": str(saved_path), "error": f"http_{file_status}", "content_type": content_type})
                continue
            saved_path = unique_path(saved_path)
            saved_path.write_bytes(body)
            downloads.append({"index": index, "name": file_name, "saved_path": str(saved_path), "size": len(body), "content_type": content_type})
    return {
        "status": "ok",
        "task_id": task_id_for_output_fn(task_id),
        "task_guid": task_guid,
        "attachment_count": len(items),
        "attachments": items,
        "downloads": downloads,
    }


def upload_task_attachments(
    task: dict[str, Any],
    task_id: str,
    file_args: list[str],
    *,
    task_id_for_output_fn: TaskIdForOutputFn,
    attachment_auth_result_fn: Callable[[dict[str, Any], str], dict[str, Any]],
    ensure_task_started_fn: EnsureTaskStartedFn,
    feishu_credentials: FeishuCredentialsFn,
    request_json: RequestJsonFn,
) -> dict[str, Any]:
    if not file_args:
        return {"status": "skipped", "task_id": task_id_for_output_fn(task_id), "task_guid": task.get("guid") or "", "uploaded_count": 0, "uploaded_files": [], "attachments": [], "auto_started": False, "start_result": None}
    auth = attachment_auth_result_fn(task, task_id)
    if auth.get("status") != "authorized":
        auth["pending_files"] = [str(Path(item).expanduser()) for item in file_args]
        return auth

    task_guid = str(task.get("guid") or "").strip()
    if not task_guid:
        raise SystemExit(f"task missing guid: {task_id}")
    files = resolve_upload_files(file_args)
    auto_started = ensure_task_started_fn(task)
    openapi_base = feishu_credentials()["openapi_base"]
    uploaded_items: list[dict[str, Any]] = []
    for batch in chunked_files(files, size=5):
        body, boundary = build_multipart_body(task_guid, batch)
        status, payload, raw = request_json(
            f"{openapi_base}/open-apis/task/v2/attachments/upload",
            method="POST",
            headers={"Authorization": f"Bearer {str(auth.get('token') or '').strip()}", "Content-Type": f"multipart/form-data; boundary={boundary}"},
            body=body,
            timeout=120,
        )
        if status >= 400 or int(payload.get("code") or 0) != 0:
            raise SystemExit(f"failed to upload task attachments: {raw}")
        data = payload.get("data")
        items = list((data or {}).get("items") or []) if isinstance(data, dict) else []
        uploaded_items.extend(item for item in items if isinstance(item, dict))
    return {
        "status": "ok",
        "task_id": task_id_for_output_fn(task_id),
        "task_guid": task_guid,
        "auto_started": bool(auto_started),
        "start_result": auto_started,
        "uploaded_count": len(uploaded_items),
        "uploaded_files": [str(path) for path in files],
        "attachments": uploaded_items,
    }
