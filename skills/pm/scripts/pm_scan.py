from __future__ import annotations

from pathlib import Path
from typing import Any

from pm_config import ACTIVE_CONFIG
from pm_gsd import detect_gsd_assets


def detect_project_mode(root: Path) -> str:
    if not root.exists():
        return "greenfield"
    signals = [
        (root / ".git").exists(),
        (root / "package.json").exists(),
        (root / "pnpm-lock.yaml").exists(),
        (root / "yarn.lock").exists(),
        (root / "package-lock.json").exists(),
        (root / "pyproject.toml").exists(),
        (root / "go.mod").exists(),
        (root / "Cargo.toml").exists(),
        (root / "apps").exists(),
        (root / "packages").exists(),
        (root / "src").exists(),
        (root / "pages").exists(),
        (root / "components").exists(),
    ]
    return "brownfield" if any(signals) else "greenfield"


def build_bootstrap_info(root: Path) -> dict[str, Any]:
    mode = detect_project_mode(root)
    recommended_action = "map-codebase" if mode == "brownfield" else "new-project"
    task = ACTIVE_CONFIG.get("task") if isinstance(ACTIVE_CONFIG.get("task"), dict) else {}
    doc = ACTIVE_CONFIG.get("doc") if isinstance(ACTIVE_CONFIG.get("doc"), dict) else {}
    return {
        "project_mode": mode,
        "recommended_action": recommended_action,
        "task_backend": str(task.get("backend") or "feishu"),
        "doc_backend": str(doc.get("backend") or "feishu"),
        "doc_folder_name": str(doc.get("folder_name") or "项目文档"),
        "doc_folder_token": str(doc.get("folder_token") or ""),
        "doc_folder_url": str(doc.get("folder_url") or ""),
        "project_doc_token": str(doc.get("project_doc_token") or ""),
        "project_doc_url": str(doc.get("project_doc_url") or ""),
        "requirements_doc_token": str(doc.get("requirements_doc_token") or ""),
        "requirements_doc_url": str(doc.get("requirements_doc_url") or ""),
        "roadmap_doc_token": str(doc.get("roadmap_doc_token") or ""),
        "roadmap_doc_url": str(doc.get("roadmap_doc_url") or ""),
        "state_doc_token": str(doc.get("state_doc_token") or ""),
        "state_doc_url": str(doc.get("state_doc_url") or ""),
        "notes": [
            "brownfield 项目优先做 map-codebase，再补项目/路线图/状态文档。",
            "greenfield 项目优先做 new-project，再进入任务拆解。",
            f"当前 task backend={str(task.get('backend') or 'feishu')}，doc backend={str(doc.get('backend') or 'feishu')}。",
        ],
    }


def repo_scan(root: Path) -> dict[str, Any]:
    markers = {
        "git": (root / ".git").exists(),
        "package_json": (root / "package.json").exists(),
        "pnpm_lock": (root / "pnpm-lock.yaml").exists(),
        "yarn_lock": (root / "yarn.lock").exists(),
        "npm_lock": (root / "package-lock.json").exists(),
        "pyproject": (root / "pyproject.toml").exists(),
        "requirements_txt": (root / "requirements.txt").exists(),
        "go_mod": (root / "go.mod").exists(),
        "cargo_toml": (root / "Cargo.toml").exists(),
        "miniapp_app_json": (root / "app.json").exists(),
        "miniapp_project_config": (root / "project.config.json").exists(),
        "src_dir": (root / "src").exists(),
        "pages_dir": (root / "pages").exists(),
        "components_dir": (root / "components").exists(),
    }
    package_manager = "unknown"
    if markers["pnpm_lock"]:
        package_manager = "pnpm"
    elif markers["yarn_lock"]:
        package_manager = "yarn"
    elif markers["npm_lock"] or markers["package_json"]:
        package_manager = "npm"
    framework_hints: list[str] = []
    if markers["miniapp_app_json"] or markers["miniapp_project_config"]:
        framework_hints.append("mini-program")
    if (root / "next.config.js").exists() or (root / "next.config.mjs").exists() or (root / "next.config.ts").exists():
        framework_hints.append("nextjs")
    if (root / "vite.config.ts").exists() or (root / "vite.config.js").exists():
        framework_hints.append("vite")
    if (root / "tsconfig.json").exists():
        framework_hints.append("typescript")
    return {
        "root": str(root),
        "exists": root.exists(),
        "name": root.name,
        "markers": markers,
        "package_manager": package_manager,
        "framework_hints": framework_hints,
    }
