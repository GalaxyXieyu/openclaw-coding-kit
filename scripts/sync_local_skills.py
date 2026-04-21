#!/usr/bin/env python3
"""Sync repo-local skills into local Codex and OpenClaw skill directories."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

DEFAULT_CODEX_SKILLS = (
    "pm",
    "coder",
    "product-canvas",
    "interaction-board",
    "openclaw-lark-bridge",
    "project-review",
)

DEFAULT_OPENCLAW_SKILLS = (
    "pm",
    "coder",
    "product-canvas",
    "interaction-board",
)

DEFAULT_OPENCLAW_PLUGINS = (
    "acp-progress-bridge",
    "skill-router",
)

AUTO_MODES = {
    "codex": "symlink",
    "openclaw": "copy",
}

LEGACY_SKILL_NAMES = {
    "project-review": ("task-review",),
}

IGNORED_NAMES = {
    ".DS_Store",
    "__pycache__",
}

IGNORED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync repo skills into local Codex/OpenClaw skill directories.")
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]), help="Repo root path.")
    parser.add_argument("--codex-root", default="~/.codex/skills", help="Codex skills directory.")
    parser.add_argument("--openclaw-root", default="~/.openclaw/workspace/skills", help="OpenClaw skills directory.")
    parser.add_argument("--openclaw-plugin-root", default="~/.openclaw/workspace/plugins", help="OpenClaw plugins directory.")
    parser.add_argument(
        "--target",
        choices=("codex", "openclaw", "both"),
        default="both",
        help="Install destination.",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "symlink", "copy"),
        default="auto",
        help="Install mode. auto uses symlink for Codex and copy for OpenClaw.",
    )
    parser.add_argument("--skill", action="append", dest="skills", help="Specific skill name. Repeatable. Applies to selected targets.")
    parser.add_argument("--plugin", action="append", dest="plugins", help="Specific OpenClaw plugin name. Repeatable.")
    parser.add_argument("--skip-plugins", action="store_true", help="Skip syncing OpenClaw plugins.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without changing files.")
    return parser.parse_args()


def normalize_assets(repo_root: Path, subdir: str, names: Iterable[str], *, kind: str) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in names:
        name = str(raw or "").strip()
        if not name or name in seen:
            continue
        asset_path = repo_root / subdir / name
        if not asset_path.is_dir():
            raise FileNotFoundError(f"{kind} not found in repo: {asset_path}")
        seen.add(name)
        result.append(name)
    return result


def target_skills(repo_root: Path, requested: list[str] | None, *, target_name: str) -> list[str]:
    defaults = DEFAULT_CODEX_SKILLS if target_name == "codex" else DEFAULT_OPENCLAW_SKILLS
    return normalize_assets(repo_root, "skills", requested or list(defaults), kind="Skill")


def target_plugins(repo_root: Path, requested: list[str] | None) -> list[str]:
    return normalize_assets(repo_root, "plugins", requested or list(DEFAULT_OPENCLAW_PLUGINS), kind="Plugin")


def target_roots(args: argparse.Namespace) -> list[tuple[str, Path]]:
    roots: list[tuple[str, Path]] = []
    if args.target in {"codex", "both"}:
        roots.append(("codex", Path(args.codex_root).expanduser().resolve()))
    if args.target in {"openclaw", "both"}:
        roots.append(("openclaw", Path(args.openclaw_root).expanduser().resolve()))
    return roots


def backup_path(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_root = path.parent.parent / f"{path.parent.name}-backups"
    return backup_root / f"{path.name}.bak-{stamp}"


def remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    shutil.rmtree(path)


def resolve_mode(target_name: str, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode
    return AUTO_MODES.get(target_name, "copy")


def ignored_parts(parts: tuple[str, ...]) -> bool:
    return any(part in IGNORED_NAMES for part in parts)


def iter_asset_files(path: Path) -> Iterable[tuple[Path, Path]]:
    for child in sorted(path.rglob("*")):
        rel = child.relative_to(path)
        if ignored_parts(rel.parts):
            continue
        if child.is_dir():
            continue
        if child.suffix in IGNORED_SUFFIXES:
            continue
        yield rel, child


def tree_fingerprint(path: Path) -> str:
    if not path.exists() and not path.is_symlink():
        return ""

    hasher = hashlib.sha256()
    if path.is_symlink():
        hasher.update(b"symlink\0")
        hasher.update(os.readlink(path).encode("utf-8"))
        return hasher.hexdigest()

    if path.is_file():
        hasher.update(b"file\0")
        hasher.update(path.read_bytes())
        return hasher.hexdigest()

    for rel, child in iter_asset_files(path):
        hasher.update(rel.as_posix().encode("utf-8"))
        hasher.update(b"\0")
        if child.is_symlink():
            hasher.update(b"symlink\0")
            hasher.update(os.readlink(child).encode("utf-8"))
        else:
            hasher.update(b"file\0")
            hasher.update(child.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def archive_legacy_skills(root: Path, skill: str, *, dry_run: bool) -> list[str]:
    archived: list[str] = []
    for legacy_name in LEGACY_SKILL_NAMES.get(skill, ()):
        legacy_path = root / legacy_name
        if not legacy_path.exists() and not legacy_path.is_symlink():
            continue
        backup = backup_path(legacy_path)
        if not dry_run:
            backup.parent.mkdir(parents=True, exist_ok=True)
            legacy_path.rename(backup)
        archived.append(f"{legacy_name}->{backup}")
    return archived


def install_asset(src: Path, dest: Path, *, mode: str, dry_run: bool) -> str:
    if dest.is_symlink():
        try:
            if mode == "symlink" and dest.resolve() == src.resolve():
                return "already-linked"
        except FileNotFoundError:
            pass
    elif mode == "copy" and dest.exists() and tree_fingerprint(src) == tree_fingerprint(dest):
        return "already-synced"

    if dest.exists() or dest.is_symlink():
        backup = backup_path(dest)
        if not dry_run:
            backup.parent.mkdir(parents=True, exist_ok=True)
        if not dry_run:
            dest.rename(backup)
        backup_note = f"backup={backup}"
    else:
        backup_note = "backup=none"

    if dry_run:
        return f"would-install mode={mode} {backup_note}"

    dest.parent.mkdir(parents=True, exist_ok=True)
    if mode == "symlink":
        if dest.exists() or dest.is_symlink():
            remove_path(dest)
        os.symlink(src, dest, target_is_directory=True)
    else:
        staging_parent = dest.parent
        with tempfile.TemporaryDirectory(prefix=f".{dest.name}.sync-", dir=staging_parent) as temp_dir:
            staging_path = Path(temp_dir) / dest.name
            shutil.copytree(
                src,
                staging_path,
                ignore=shutil.ignore_patterns(*IGNORED_NAMES, *[f"*{suffix}" for suffix in IGNORED_SUFFIXES]),
            )
            if dest.exists() or dest.is_symlink():
                remove_path(dest)
            staging_path.rename(dest)
    return f"installed mode={mode} {backup_note}"


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()
    destinations = target_roots(args)

    print(f"repo_root={repo_root}")
    print(f"mode={args.mode}")
    print(f"dry_run={args.dry_run}")

    for target_name, root in destinations:
        target_mode = resolve_mode(target_name, args.mode)
        skills = target_skills(repo_root, args.skills, target_name=target_name)
        print(f"[{target_name}] root={root} mode={target_mode}")
        if not args.dry_run:
            root.mkdir(parents=True, exist_ok=True)
        for skill in skills:
            src = repo_root / "skills" / skill
            dest = root / skill
            archived = archive_legacy_skills(root, skill, dry_run=args.dry_run)
            status = install_asset(src, dest, mode=target_mode, dry_run=args.dry_run)
            if archived:
                status = f"{status} archived_legacy={','.join(archived)}"
            print(f"  - {skill}: {status}")
        if target_name != "openclaw" or args.skip_plugins:
            continue
        plugin_root = Path(args.openclaw_plugin_root).expanduser().resolve()
        plugins = target_plugins(repo_root, args.plugins)
        print(f"[openclaw-plugins] root={plugin_root} mode={target_mode}")
        if not args.dry_run:
            plugin_root.mkdir(parents=True, exist_ok=True)
        for plugin in plugins:
            src = repo_root / "plugins" / plugin
            dest = plugin_root / plugin
            status = install_asset(src, dest, mode=target_mode, dry_run=args.dry_run)
            print(f"  - {plugin}: {status}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
