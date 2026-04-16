from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Sequence

OPENCLAW_BIN_ENV_VARS = ("OPENCLAW_BIN", "OPENCLAW_PATH", "OPENCLAW_CLI")
CODEX_BIN_ENV_VARS = ("CODEX_BIN", "CODEX_PATH", "CODEX_CLI")


def _dedupe_paths(paths: Sequence[Path]) -> tuple[Path, ...]:
    seen: set[str] = set()
    ordered: list[Path] = []
    for item in paths:
        expanded = item.expanduser()
        key = str(expanded)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(expanded)
    return tuple(ordered)


def _command_names(base: str) -> tuple[str, ...]:
    if os.name == "nt":
        return (f"{base}.cmd", f"{base}.exe", f"{base}.bat", base)
    return (base,)


def _standard_bin_dirs() -> tuple[Path, ...]:
    home = Path.home()
    candidates: list[Path] = []
    appdata = str(os.environ.get("APPDATA") or "").strip()
    local_appdata = str(os.environ.get("LOCALAPPDATA") or "").strip()
    if appdata:
        candidates.append(Path(appdata) / "npm")
    if local_appdata:
        candidates.append(Path(local_appdata) / "npm")
    candidates.extend(
        [
            home / ".local" / "bin",
            home / ".npm-global" / "bin",
            home / "AppData" / "Roaming" / "npm",
            home / "AppData" / "Local" / "npm",
            Path("/opt/homebrew/bin"),
            Path("/usr/local/bin"),
            Path("/usr/bin"),
        ]
    )
    return _dedupe_paths(candidates)


def _env_override_candidates(env_vars: Sequence[str], command_names: Sequence[str]) -> tuple[Path, ...]:
    candidates: list[Path] = []
    for env_name in env_vars:
        raw = str(os.environ.get(env_name) or "").strip()
        if not raw:
            continue
        path = Path(raw).expanduser()
        if path.is_dir() and command_names:
            candidates.extend(path / name for name in command_names)
            continue
        candidates.append(path)
    return _dedupe_paths(candidates)


def _path_lookup(command_names: Sequence[str]) -> Path | None:
    for name in command_names:
        resolved = shutil.which(name)
        if resolved:
            return Path(resolved)
    return None


def resolve_runtime_path(
    *,
    env_vars: Sequence[str] = (),
    path_lookup_names: Sequence[str] = (),
    fallback_paths: Sequence[Path] = (),
) -> Path | None:
    for candidate in _env_override_candidates(env_vars, path_lookup_names):
        if candidate.exists():
            return candidate
    if path_lookup_names:
        resolved = _path_lookup(path_lookup_names)
        if resolved is not None and resolved.exists():
            return resolved
    for candidate in _dedupe_paths(fallback_paths):
        if candidate.exists():
            return candidate
    return None


def _standard_command_candidates(base: str) -> tuple[Path, ...]:
    names = _command_names(base)
    return _dedupe_paths([bin_dir / name for bin_dir in _standard_bin_dirs() for name in names])


OPENCLAW_BIN_CANDIDATES = _standard_command_candidates("openclaw")
CODEX_BIN_CANDIDATES = _standard_command_candidates("codex")


def openclaw_bin_path(candidates: Sequence[Path] = OPENCLAW_BIN_CANDIDATES) -> Path:
    command_names = _command_names("openclaw")
    resolved = resolve_runtime_path(
        env_vars=OPENCLAW_BIN_ENV_VARS,
        path_lookup_names=command_names,
        fallback_paths=candidates,
    )
    if resolved is not None:
        return resolved
    raise SystemExit(
        "openclaw binary not found; set OPENCLAW_BIN, keep `openclaw` on PATH, "
        "or install it in a standard bin directory"
    )


def codex_bin_path(candidates: Sequence[Path] = CODEX_BIN_CANDIDATES) -> Path:
    command_names = _command_names("codex")
    resolved = resolve_runtime_path(
        env_vars=CODEX_BIN_ENV_VARS,
        path_lookup_names=command_names,
        fallback_paths=candidates,
    )
    if resolved is not None:
        return resolved
    raise SystemExit(
        "codex binary not found; set CODEX_BIN, keep `codex` on PATH, "
        "or install it in a standard bin directory"
    )


def openclaw_env(*, bin_path_fn=openclaw_bin_path) -> dict[str, str]:
    env = os.environ.copy()
    node_bin = str(bin_path_fn().parent)
    env["PATH"] = node_bin + os.pathsep + env.get("PATH", "")
    return env


def parse_mixed_json_output(raw: str) -> dict[str, Any]:
    text = str(raw or "").strip()
    if not text:
        raise json.JSONDecodeError("empty output", text, 0)
    decoder = json.JSONDecoder()
    for start_idx, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            payload, _end = decoder.raw_decode(text[start_idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise json.JSONDecodeError("no JSON object found in mixed output", text, 0)


def describe_openclaw_agent_failure(agent_id: str, *, stderr: str = "", stdout: str = "") -> str:
    message = str(stderr or stdout or "").strip()
    lowered = message.lower()
    if "unknown agent id" in lowered:
        return (
            f"{message}\n"
            "Hint: this usually means you passed an OpenClaw front agent id that does not exist.\n"
            "Remember that the front agent and the ACP worker can be different roles.\n"
            "Check `openclaw agents list --bindings`, or set `project.agent`, or pass `--agent <front-agent>` explicitly."
        ).strip()
    if "not found" in lowered and "openclaw" in lowered:
        return (
            f"{message}\n"
            "Hint: verify the OpenClaw CLI path discovery first. Set OPENCLAW_BIN or keep `openclaw` on PATH."
        ).strip()
    return message or f"openclaw agent failed: {agent_id}"


def run_openclaw_agent(
    *,
    agent_id: str,
    message: str,
    cwd: str = "",
    timeout_seconds: int = 900,
    thinking: str = "high",
    bin_path_fn=openclaw_bin_path,
    env_fn=openclaw_env,
) -> dict[str, Any]:
    cmd = [
        str(bin_path_fn()),
        "agent",
        "--agent",
        agent_id,
        "--message",
        message,
        "--json",
        "--timeout",
        str(timeout_seconds),
    ]
    if thinking:
        cmd.extend(["--thinking", thinking])
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env=env_fn(bin_path_fn=bin_path_fn),
        cwd=cwd or None,
    )
    if proc.returncode != 0:
        raise SystemExit(
            describe_openclaw_agent_failure(
                agent_id,
                stderr=proc.stderr,
                stdout=proc.stdout,
            )
        )
    try:
        return parse_mixed_json_output(proc.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(
            "openclaw agent returned non-JSON output: "
            + str(exc)
            + "\nSTDOUT:\n"
            + proc.stdout[:1200]
            + "\nSTDERR:\n"
            + proc.stderr[:1200]
        ) from exc


def run_codex_cli(
    *,
    agent_id: str,
    message: str,
    cwd: str = "",
    timeout_seconds: int = 900,
    thinking: str = "high",
    bin_path_fn=codex_bin_path,
) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(prefix="pm-codex-", suffix=".txt", delete=False) as handle:
        output_path = Path(handle.name)
    cmd = [
        str(bin_path_fn()),
        "exec",
        "-C",
        cwd or os.getcwd(),
        "--dangerously-bypass-approvals-and-sandbox",
        "-o",
        str(output_path),
        message,
    ]
    model = str(agent_id or "").strip()
    if model and model not in {"codex", "main"}:
        cmd[2:2] = ["-m", model]
    timeout_arg = None if int(timeout_seconds or 0) <= 0 else max(30, int(timeout_seconds))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            stdin=subprocess.DEVNULL,
            timeout=timeout_arg,
        )
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"codex exec timed out after {timeout_seconds}s") from exc
    output_text = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
    try:
        output_path.unlink(missing_ok=True)
    except OSError:
        pass
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.strip() or output_text or proc.stdout.strip() or "codex exec failed")
    return {
        "backend": "codex-cli",
        "status": "ok",
        "summary": "completed",
        "result": {
            "payloads": ([{"text": output_text, "mediaUrl": None}] if output_text else []),
            "meta": {
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
                "returncode": proc.returncode,
                "cwd": cwd or os.getcwd(),
                "thinking": thinking,
            },
        },
    }
