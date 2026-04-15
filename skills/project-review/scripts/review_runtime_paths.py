#!/usr/bin/env python3
"""Runtime path discovery for project-review global review workflows."""

from __future__ import annotations

import os
from pathlib import Path

from review_state_store import PROJECT_REVIEW_STATE_FILENAME


MAIN_REVIEW_CONFIG_FILENAME = "main_review_sources.json"
LEGACY_MAIN_DIGEST_CONFIG_FILENAME = "main_digest_sources.json"
MAIN_REVIEW_CONFIG_ENV_VARS = (
    "PROJECT_REVIEW_MAIN_REVIEW_CONFIG",
    "OPENCLAW_PROJECT_REVIEW_MAIN_REVIEW_CONFIG",
    "PROJECT_REVIEW_MAIN_DIGEST_CONFIG",
    "OPENCLAW_PROJECT_REVIEW_MAIN_DIGEST_CONFIG",
    "OPENCLAW_PROJECT_REVIEW_CONFIG",
)
MAIN_REVIEW_STATE_ENV_VARS = (
    "PROJECT_REVIEW_MAIN_REVIEW_STATE",
    "OPENCLAW_PROJECT_REVIEW_MAIN_REVIEW_STATE",
    "PROJECT_REVIEW_MAIN_DIGEST_STATE",
    "OPENCLAW_PROJECT_REVIEW_STATE",
)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    ordered: list[Path] = []
    seen: set[str] = set()
    for item in paths:
        key = str(item)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(item)
    return ordered


def _existing_path_from_env(env_names: tuple[str, ...]) -> Path | None:
    for env_name in env_names:
        raw = str(os.environ.get(env_name) or "").strip()
        if not raw:
            continue
        return Path(raw).expanduser()
    return None


def bundled_main_review_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / MAIN_REVIEW_CONFIG_FILENAME


def bundled_main_digest_config_path() -> Path:
    legacy = Path(__file__).resolve().parents[1] / "config" / LEGACY_MAIN_DIGEST_CONFIG_FILENAME
    if legacy.exists():
        return legacy
    return bundled_main_review_config_path()


def _openclaw_config_candidates(start: str | Path = ".") -> list[Path]:
    start_path = Path(start).expanduser().resolve()
    home = Path.home()
    candidates: list[Path] = []

    for env_name in ("OPENCLAW_CONFIG", "OPENCLAW_CONFIG_PATH"):
        explicit_config = str(os.environ.get(env_name) or "").strip()
        if explicit_config:
            candidates.append(Path(explicit_config).expanduser())

    for parent in [start_path, *start_path.parents]:
        candidates.append(parent / "openclaw.json")
        candidates.append(parent / ".openclaw" / "openclaw.json")

    for env_name in ("OPENCLAW_HOME", "OPENCLAW_STATE_DIR"):
        openclaw_home = str(os.environ.get(env_name) or "").strip()
        if openclaw_home:
            candidates.append(Path(openclaw_home).expanduser() / "openclaw.json")

    xdg_config_home = str(os.environ.get("XDG_CONFIG_HOME") or "").strip()
    if xdg_config_home:
        candidates.extend(
            [
                Path(xdg_config_home) / "openclaw" / "openclaw.json",
                Path(xdg_config_home) / "OpenClaw" / "openclaw.json",
            ]
        )

    for env_name in ("APPDATA", "LOCALAPPDATA"):
        base = str(os.environ.get(env_name) or "").strip()
        if not base:
            continue
        candidates.extend(
            [
                Path(base) / "openclaw" / "openclaw.json",
                Path(base) / "OpenClaw" / "openclaw.json",
            ]
        )

    candidates.extend(
        [
            home / ".config" / "openclaw" / "openclaw.json",
            home / ".config" / "OpenClaw" / "openclaw.json",
            home / ".openclaw" / "openclaw.json",
        ]
    )
    return _dedupe_paths(candidates)


def find_openclaw_config_path(start: str | Path = ".") -> Path | None:
    for candidate in _openclaw_config_candidates(start):
        expanded = candidate.expanduser()
        if expanded.exists():
            return expanded.resolve()
    return None


def openclaw_runtime_dir(start: str | Path = ".") -> Path | None:
    config_path = find_openclaw_config_path(start)
    if config_path is None:
        return None
    return config_path.parent.resolve()


def _runtime_config_candidates(start: str | Path = ".") -> list[Path]:
    candidates: list[Path] = []
    runtime_dir = openclaw_runtime_dir(start)
    if runtime_dir is not None:
        candidates.extend(
            [
                runtime_dir / "project-review" / MAIN_REVIEW_CONFIG_FILENAME,
                runtime_dir / "project-review" / LEGACY_MAIN_DIGEST_CONFIG_FILENAME,
                runtime_dir / ".pm" / "project-review" / MAIN_REVIEW_CONFIG_FILENAME,
                runtime_dir / ".pm" / "project-review" / LEGACY_MAIN_DIGEST_CONFIG_FILENAME,
            ]
        )
    return _dedupe_paths(candidates)


def resolve_main_review_config_path(explicit: str | Path | None = None, *, start: str | Path = ".") -> Path:
    if explicit:
        return Path(explicit).expanduser()

    env_path = _existing_path_from_env(MAIN_REVIEW_CONFIG_ENV_VARS)
    if env_path is not None:
        return env_path

    for candidate in _runtime_config_candidates(start):
        if candidate.exists():
            return candidate.resolve()

    return bundled_main_review_config_path()


def resolve_main_digest_config_path(explicit: str | Path | None = None, *, start: str | Path = ".") -> Path:
    return resolve_main_review_config_path(explicit, start=start)


def resolve_main_review_state_path(
    explicit: str | Path | None = None,
    *,
    config_path: str | Path | None = None,
    start: str | Path = ".",
) -> Path:
    if explicit:
        return Path(explicit).expanduser()

    env_path = _existing_path_from_env(MAIN_REVIEW_STATE_ENV_VARS)
    if env_path is not None:
        return env_path

    if config_path:
        candidate = Path(config_path).expanduser()
        bundled = bundled_main_review_config_path()
        try:
            if candidate.resolve() != bundled.resolve():
                return candidate.parent / PROJECT_REVIEW_STATE_FILENAME
        except FileNotFoundError:
            return candidate.parent / PROJECT_REVIEW_STATE_FILENAME

    runtime_dir = openclaw_runtime_dir(start)
    if runtime_dir is not None:
        return runtime_dir / "project-review" / PROJECT_REVIEW_STATE_FILENAME

    return Path(start).expanduser().resolve() / ".pm" / PROJECT_REVIEW_STATE_FILENAME


def resolve_main_digest_state_path(
    explicit: str | Path | None = None,
    *,
    config_path: str | Path | None = None,
    start: str | Path = ".",
) -> Path:
    return resolve_main_review_state_path(explicit, config_path=config_path, start=start)
