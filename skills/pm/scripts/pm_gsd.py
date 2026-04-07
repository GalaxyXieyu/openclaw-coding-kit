from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import os
from pathlib import Path
from typing import Any

from pm_runtime import resolve_runtime_path

GSD_DOC_NAMES = ("PROJECT.md", "REQUIREMENTS.md", "ROADMAP.md", "STATE.md")
GSD_DOC_KEYS = {
    "PROJECT.md": "project",
    "REQUIREMENTS.md": "requirements",
    "ROADMAP.md": "roadmap",
    "STATE.md": "state",
}
GSD_TOOLS_ENV_VARS = ("GSD_TOOLS_PATH", "GSD_TOOLS_BIN")


def gsd_tools_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []
    codex_home = str(os.environ.get("CODEX_HOME") or "").strip()
    if codex_home:
        candidates.append(Path(codex_home).expanduser() / "get-shit-done" / "bin" / "gsd-tools.cjs")
    candidates.append(Path.home() / ".codex" / "get-shit-done" / "bin" / "gsd-tools.cjs")
    return tuple(candidates)


def read_text_excerpt(path: Path, *, max_chars: int = 1600) -> str:
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""
    text = raw.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n..."


def gsd_doc_candidates(root: Path, name: str) -> list[Path]:
    return [root / ".planning" / name]


def locate_gsd_doc(root: Path, name: str) -> Path | None:
    for candidate in gsd_doc_candidates(root, name):
        if candidate.exists():
            return candidate
    return None


def detect_gsd_assets(root: Path) -> dict[str, Any]:
    assets: dict[str, Any] = {
        "enabled": False,
        "docs": {},
        "research_dir": "",
        "planning_root": "",
        "detected_signals": [],
        "summaries": {},
    }
    planning_root = root / ".planning"
    if planning_root.exists():
        assets["planning_root"] = str(planning_root)
        assets["detected_signals"].append(".planning")
    for name in GSD_DOC_NAMES:
        path = locate_gsd_doc(root, name)
        if path is None:
            continue
        key = GSD_DOC_KEYS[name]
        assets["docs"][key] = str(path)
        assets["summaries"][key] = read_text_excerpt(path)
        assets["detected_signals"].append(str(path.relative_to(root)))
    research_dir = root / ".planning" / "research"
    if research_dir.exists():
        assets["research_dir"] = str(research_dir)
        assets["detected_signals"].append(".planning/research")
    assets["enabled"] = bool(assets["docs"])
    return assets


def gsd_tools_path() -> Path | None:
    return resolve_runtime_path(
        env_vars=GSD_TOOLS_ENV_VARS,
        path_lookup_names=("gsd-tools", "gsd-tools.cjs"),
        fallback_paths=gsd_tools_candidates(),
    )


def gsd_tools_command() -> list[str] | None:
    tool = gsd_tools_path()
    if tool is None:
        return None
    if tool.suffix.lower() in {".cjs", ".js", ".mjs"}:
        node = shutil.which("node")
        if not node:
            raise SystemExit("node not found; install Node.js or keep `node` available on PATH")
        return [node, str(tool)]
    return [str(tool)]


def gsd_runtime_status() -> dict[str, Any]:
    tool = gsd_tools_path()
    node = shutil.which("node")
    tool_path = str(tool) if tool is not None else ""
    uses_node = bool(tool is not None and tool.suffix.lower() in {".cjs", ".js", ".mjs"})
    issues: list[str] = []
    if tool is None:
        issues.append("gsd-tools not found")
    if uses_node and not node:
        issues.append("node not found")
    suggestions: list[str] = []
    if tool is None:
        suggestions.append("set GSD_TOOLS_PATH or install gsd-tools under CODEX_HOME/.codex")
    if uses_node and not node:
        suggestions.append("install Node.js or keep `node` available on PATH")
    return {
        "ready": not issues,
        "tool_path": tool_path,
        "node_path": str(node or ""),
        "uses_node": uses_node,
        "issues": issues,
        "suggestions": suggestions,
    }


def run_gsd_tools(root: Path, *args: str, raw: bool = True) -> dict[str, Any] | str | None:
    runtime = gsd_runtime_status()
    if not bool(runtime.get("ready")):
        return {
            "error": "; ".join(str(item) for item in (runtime.get("issues") or []) if str(item).strip()) or "gsd runtime unavailable",
            "runtime": runtime,
            "command": [],
        }
    tool_cmd = gsd_tools_command()
    if tool_cmd is None:
        return {
            "error": "gsd runtime unavailable",
            "runtime": runtime,
            "command": [],
        }
    cmd = [*tool_cmd, *args]
    if raw:
        cmd.append("--raw")
    cmd.extend(["--cwd", str(root)])
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return {
            "error": proc.stderr.strip() or proc.stdout.strip() or "gsd-tools command failed",
            "command": cmd,
        }
    output = proc.stdout.strip()
    if not output:
        return {}
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return output


def extract_plan_frontmatter(content: str) -> dict[str, Any]:
    match = re.match(r"^---\s*\n(?P<body>.*?\n)---\s*(?:\n|$)", content, flags=re.DOTALL)
    if not match:
        return {}
    lines = match.group("body").splitlines()
    data: dict[str, Any] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        key_match = re.match(r"^(?P<key>[A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(?P<value>.*)$", line)
        if not key_match:
            index += 1
            continue
        key = str(key_match.group("key") or "").strip()
        raw_value = str(key_match.group("value") or "").strip()
        if raw_value:
            data[key] = parse_frontmatter_value(raw_value)
            index += 1
            continue
        list_items: list[str] = []
        index += 1
        while index < len(lines):
            nested = lines[index]
            if re.match(r"^[A-Za-z_][A-Za-z0-9_-]*\s*:", nested):
                break
            stripped = nested.strip()
            if stripped.startswith("- "):
                list_items.append(stripped[2:].strip())
            index += 1
        data[key] = [coerce_frontmatter_scalar(item) for item in list_items] if list_items else []
    return data


def parse_frontmatter_value(value: str) -> Any:
    text = value.strip()
    if not text:
        return ""
    if text in {"[]", "[ ]"}:
        return []
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", text):
        try:
            return int(text)
        except ValueError:
            return text
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        try:
            parsed = ast.literal_eval(text)
        except (SyntaxError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            return [coerce_frontmatter_scalar(item) for item in parsed]
        return [coerce_frontmatter_scalar(part) for part in inner.split(",") if str(part).strip()]
    return coerce_frontmatter_scalar(text)


def coerce_frontmatter_scalar(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    text = str(value or "").strip()
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        text = text[1:-1].strip()
    lowered = text.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", text):
        try:
            return int(text)
        except ValueError:
            return text
    return text


def extract_plan_objective(content: str) -> str:
    match = re.search(r"<objective>\s*(?P<body>.*?)\s*</objective>", content, flags=re.DOTALL)
    if not match:
        return ""
    lines = [line.strip() for line in match.group("body").splitlines() if line.strip()]
    return "\n".join(lines).strip()


def count_plan_tasks(content: str) -> int:
    xml_tasks = re.findall(r"<task[\s>]", content, flags=re.IGNORECASE)
    markdown_tasks = re.findall(r"##\s*Task\s*\d+", content, flags=re.IGNORECASE)
    return len(xml_tasks) or len(markdown_tasks)


def gsd_phase_context_path(phase_dir: str, phase: str) -> str:
    normalized_dir = str(phase_dir or "").strip().strip("/")
    normalized_phase = str(phase or "").strip()
    if not normalized_dir or not normalized_phase:
        return ""
    return f"{normalized_dir}/{normalized_phase}-CONTEXT.md"


def existing_gsd_reads(root: Path, paths: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        path = str(raw or "").strip()
        if not path or path in seen:
            continue
        if not (root / path).exists():
            continue
        seen.add(path)
        result.append(path)
    return result


def pick_gsd_phase(root: Path, *, phase: str = "") -> str:
    selected_phase = str(phase or "").strip()
    if selected_phase:
        return selected_phase
    state_snapshot = run_gsd_tools(root, "state-snapshot")
    if isinstance(state_snapshot, dict):
        selected_phase = str(state_snapshot.get("current_phase") or "").strip()
        if selected_phase:
            return selected_phase
    roadmap_analysis = run_gsd_tools(root, "roadmap", "analyze")
    if isinstance(roadmap_analysis, dict):
        selected_phase = str(roadmap_analysis.get("current_phase") or roadmap_analysis.get("next_phase") or "").strip()
    return selected_phase


def find_gsd_phase(root: Path, phase: str) -> dict[str, Any]:
    if not str(phase or "").strip():
        return {}
    result = run_gsd_tools(root, "find-phase", phase, raw=False)
    return result if isinstance(result, dict) else {}


def list_gsd_phase_plans(root: Path, *, phase: str = "") -> dict[str, Any]:
    selected_phase = pick_gsd_phase(root, phase=phase)
    if not selected_phase:
        return {
            "phase": "",
            "phase_dir": "",
            "phase_name": "",
            "plans": [],
            "phase_lookup": {},
            "phase_index": {},
        }
    phase_lookup = find_gsd_phase(root, selected_phase)
    phase_dir_rel = str(phase_lookup.get("directory") or "").strip()
    if not phase_dir_rel:
        return {
            "phase": selected_phase,
            "phase_dir": "",
            "phase_name": "",
            "plans": [],
            "phase_lookup": phase_lookup,
            "phase_index": {},
        }
    phase_dir = root / phase_dir_rel
    phase_index = run_gsd_tools(root, "phase-plan-index", selected_phase)
    phase_index = phase_index if isinstance(phase_index, dict) else {}
    indexed_plans = {
        str(item.get("id") or ""): item
        for item in (phase_index.get("plans") or [])
        if isinstance(item, dict)
    }
    plan_records: list[dict[str, Any]] = []
    for plan_path in sorted(phase_dir.glob("*PLAN.md")):
        if not plan_path.is_file():
            continue
        content = plan_path.read_text(encoding="utf-8")
        frontmatter = extract_plan_frontmatter(content)
        plan_id = plan_path.name.replace("-PLAN.md", "")
        if plan_path.name == "PLAN.md":
            plan_id = ""
        indexed = indexed_plans.get(plan_id, {}) if plan_id in indexed_plans else {}
        summary_name = "SUMMARY.md" if plan_path.name == "PLAN.md" else plan_path.name.replace("-PLAN.md", "-SUMMARY.md")
        summary_path = phase_dir / summary_name
        files_modified = indexed.get("files_modified")
        if not isinstance(files_modified, list):
            raw_files = frontmatter.get("files_modified") or []
            files_modified = raw_files if isinstance(raw_files, list) else [raw_files]
        requirements = frontmatter.get("requirements") or []
        user_setup = frontmatter.get("user_setup") or []
        objective = str(indexed.get("objective") or extract_plan_objective(content) or "").strip()
        task_count = int(indexed.get("task_count") or count_plan_tasks(content) or 0)
        wave = int(indexed.get("wave") or frontmatter.get("wave") or 1)
        autonomous_value = indexed.get("autonomous")
        if autonomous_value is None:
            autonomous_value = frontmatter.get("autonomous")
        if autonomous_value is None:
            autonomous = True
        else:
            autonomous = bool(autonomous_value)
        plan_records.append(
            {
                "phase": str(phase_lookup.get("phase_number") or selected_phase),
                "phase_name": str(phase_lookup.get("phase_name") or ""),
                "phase_dir": phase_dir_rel,
                "plan_id": plan_id,
                "plan_key": plan_id or plan_path.stem,
                "plan_file": plan_path.name,
                "plan_path": str(plan_path.relative_to(root).as_posix()),
                "summary_path": str(summary_path.relative_to(root).as_posix()),
                "has_summary": bool(indexed.get("has_summary")) or summary_path.exists(),
                "wave": wave,
                "autonomous": autonomous,
                "files_modified": [str(item).strip() for item in files_modified if str(item).strip()],
                "requirements": [str(item).strip() for item in (requirements if isinstance(requirements, list) else [requirements]) if str(item).strip()],
                "user_setup": [str(item).strip() for item in (user_setup if isinstance(user_setup, list) else [user_setup]) if str(item).strip()],
                "task_count": task_count,
                "objective": objective,
            }
        )
    return {
        "phase": str(phase_lookup.get("phase_number") or selected_phase),
        "phase_dir": phase_dir_rel,
        "phase_name": str(phase_lookup.get("phase_name") or ""),
        "plans": plan_records,
        "phase_lookup": phase_lookup,
        "phase_index": phase_index,
    }


def build_gsd_required_reads(root: Path, plan: dict[str, Any]) -> list[str]:
    phase = str(plan.get("phase") or "").strip()
    phase_dir = str(plan.get("phase_dir") or "").strip()
    context_path = gsd_phase_context_path(phase_dir, phase)
    return existing_gsd_reads(
        root,
        [
            str(plan.get("plan_path") or ""),
            context_path,
            ".planning/STATE.md",
            ".planning/ROADMAP.md",
            ".planning/REQUIREMENTS.md",
            ".planning/PROJECT.md",
        ],
    )


def build_gsd_task_hints(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    phase = str(plan.get("phase") or "").strip()
    required_reads = build_gsd_required_reads(root, plan)
    return {
        "stage": "execute",
        "context_path": gsd_phase_context_path(str(plan.get("phase_dir") or ""), phase),
        "required_reads": required_reads,
        "recommended_skill": "none",
        "recommended_mode": "direct-plan-execution",
        "escalate_discuss": f"$gsd-discuss-phase {phase}".strip(),
        "escalate_replan": f"$gsd-plan-phase {phase} --reviews --text".strip(),
        "escalate_verify": f"$gsd-verify-work {phase}".strip(),
    }


def build_gsd_task_contract(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    hints = build_gsd_task_hints(root, plan)
    return {
        "source": "plan",
        "stage": str(hints.get("stage") or "").strip(),
        "phase": str(plan.get("phase") or "").strip(),
        "plan_id": str(plan.get("plan_id") or plan.get("plan_key") or "").strip(),
        "plan_path": str(plan.get("plan_path") or "").strip(),
        "summary_path": str(plan.get("summary_path") or "").strip(),
        "context_path": str(hints.get("context_path") or "").strip(),
        "required_reads": [str(item).strip() for item in (hints.get("required_reads") or []) if str(item).strip()],
        "recommended_skill": str(hints.get("recommended_skill") or "").strip(),
        "recommended_mode": str(hints.get("recommended_mode") or "").strip(),
        "escalate_discuss": str(hints.get("escalate_discuss") or "").strip(),
        "escalate_replan": str(hints.get("escalate_replan") or "").strip(),
        "escalate_verify": str(hints.get("escalate_verify") or "").strip(),
    }


def build_gsd_task_summary_body(plan: dict[str, Any]) -> str:
    objective = str(plan.get("objective") or "").strip()
    if objective:
        return objective
    phase = str(plan.get("phase") or "").strip()
    plan_key = str(plan.get("plan_id") or plan.get("plan_key") or "").strip()
    prefix = f"GSD Phase {phase}".strip()
    if plan_key:
        prefix = f"{prefix} Plan {plan_key}".strip()
    return prefix


def build_gsd_task_description(task_id: str, plan: dict[str, Any], *, repo_root: Path) -> str:
    contract = build_gsd_task_contract(repo_root, plan)
    lines = [
        f"任务编号：{task_id}",
        "类型：gsd-plan",
        f"Repo：{repo_root}",
        "",
        "来源：",
        "- 该任务由 GSD PLAN 自动物化生成",
        "- 计划源文件始终以 repo_root/.planning 下内容为准",
        "",
        f"GSD Source: {str(contract.get('source') or '').strip()}",
        f"GSD Stage: {str(contract.get('stage') or '').strip()}",
        f"GSD Phase: {str(contract.get('phase') or '').strip()}",
        f"GSD Plan ID: {str(contract.get('plan_id') or '').strip()}",
        f"GSD Plan Path: {str(contract.get('plan_path') or '').strip()}",
        f"GSD Summary Path: {str(contract.get('summary_path') or '').strip()}",
        f"GSD Context Path: {str(contract.get('context_path') or '').strip()}",
        f"GSD Recommended Skill: {str(contract.get('recommended_skill') or '').strip()}",
        f"GSD Recommended Mode: {str(contract.get('recommended_mode') or '').strip()}",
        f"GSD Escalate Discuss: {str(contract.get('escalate_discuss') or '').strip()}",
        f"GSD Escalate Replan: {str(contract.get('escalate_replan') or '').strip()}",
        f"GSD Escalate Verify: {str(contract.get('escalate_verify') or '').strip()}",
        "",
        "计划概览：",
        f"- Phase 目录：{str(plan.get('phase_dir') or '').strip() or '-'}",
        f"- Phase 名称：{str(plan.get('phase_name') or '').strip() or '-'}",
        f"- Plan 文件：{str(plan.get('plan_file') or '').strip() or '-'}",
        f"- Wave：{plan.get('wave') or 1}",
        f"- Autonomous：{'true' if bool(plan.get('autonomous')) else 'false'}",
        f"- 任务数：{plan.get('task_count') or 0}",
        f"- 已有 Summary：{'true' if bool(plan.get('has_summary')) else 'false'}",
        "",
        "目标：",
        str(plan.get("objective") or "").strip() or "-",
    ]
    files_modified = [str(item).strip() for item in (plan.get("files_modified") or []) if str(item).strip()]
    if files_modified:
        lines.extend(["", "涉及文件：", *[f"- {item}" for item in files_modified]])
    requirements = [str(item).strip() for item in (plan.get("requirements") or []) if str(item).strip()]
    if requirements:
        lines.extend(["", "Requirement IDs：", *[f"- {item}" for item in requirements]])
    user_setup = [str(item).strip() for item in (plan.get("user_setup") or []) if str(item).strip()]
    if user_setup:
        lines.extend(["", "人工准备项：", *[f"- {item}" for item in user_setup]])
    required_reads = [str(item).strip() for item in (contract.get("required_reads") or []) if str(item).strip()]
    if required_reads:
        lines.extend(["", "GSD Required Reads:", *[f"- {item}" for item in required_reads]])
    lines.extend(
        [
            "",
            "执行要求：",
            "- 实现前先阅读对应的 PLAN.md 与相关上下文文件",
            "- 完成后将结果回写到对应 SUMMARY.md / STATE.md / Feishu 评论",
            "- 若计划更新，重新执行 pm materialize-gsd-tasks 以同步任务描述",
        ]
    )
    return "\n".join(lines).strip()


def extract_gsd_task_binding(description: str) -> dict[str, str]:
    text = str(description or "")

    def pick(label: str) -> str:
        match = re.search(rf"^{re.escape(label)}\s*:\s*(.+)$", text, flags=re.MULTILINE)
        return str(match.group(1) or "").strip() if match else ""

    return {
        "source": pick("GSD Source"),
        "phase": pick("GSD Phase"),
        "plan_id": pick("GSD Plan ID"),
        "plan_path": pick("GSD Plan Path"),
        "summary_path": pick("GSD Summary Path"),
        "context_path": pick("GSD Context Path"),
        "recommended_mode": pick("GSD Recommended Mode"),
    }


def build_gsd_progress_snapshot(root: Path, *, phase: str = "") -> dict[str, Any]:
    assets = detect_gsd_assets(root)
    runtime = gsd_runtime_status()
    state_snapshot = run_gsd_tools(root, "state-snapshot")
    roadmap_analysis = run_gsd_tools(root, "roadmap", "analyze")

    selected_phase = str(phase or "").strip()
    if not selected_phase and isinstance(state_snapshot, dict):
        selected_phase = str(state_snapshot.get("current_phase") or "").strip()
    if not selected_phase and isinstance(roadmap_analysis, dict):
        selected_phase = str(roadmap_analysis.get("current_phase") or roadmap_analysis.get("next_phase") or "").strip()

    phase_index = run_gsd_tools(root, "phase-plan-index", selected_phase) if selected_phase else None
    phase_info: dict[str, Any] = {}
    if selected_phase and isinstance(roadmap_analysis, dict):
        for item in roadmap_analysis.get("phases") or []:
            if isinstance(item, dict) and str(item.get("number") or "") == selected_phase:
                phase_info = item
                break

    progress = (state_snapshot or {}).get("progress") if isinstance(state_snapshot, dict) else {}
    milestone = str((state_snapshot or {}).get("milestone") or "") if isinstance(state_snapshot, dict) else ""
    milestone_name = str((state_snapshot or {}).get("milestone_name") or "") if isinstance(state_snapshot, dict) else ""
    current_phase_name = str((state_snapshot or {}).get("current_phase_name") or phase_info.get("name") or "") if isinstance(state_snapshot, dict) else str(phase_info.get("name") or "")
    current_plan = str((state_snapshot or {}).get("current_plan") or "") if isinstance(state_snapshot, dict) else ""
    normalized_status = str((state_snapshot or {}).get("status") or "") if isinstance(state_snapshot, dict) else ""

    lines = [
        "## GSD Progress Snapshot",
        "",
        f"- Repo: `{root}`",
        f"- Runtime Ready: {'true' if bool(runtime.get('ready')) else 'false'}",
        f"- Milestone: {milestone} {milestone_name}".rstrip(),
        f"- Status: {normalized_status or 'unknown'}",
        f"- Current Phase: {selected_phase or '-'} {current_phase_name}".rstrip(),
        f"- Current Plan: {current_plan or '-'}",
    ]
    if not bool(runtime.get("ready")):
        lines.extend(
            [
                "",
                "### GSD Runtime Diagnostics",
                *[f"- {item}" for item in (runtime.get("issues") or []) if str(item).strip()],
                *[f"- Suggestion: {item}" for item in (runtime.get("suggestions") or []) if str(item).strip()],
            ]
        )
    if isinstance(progress, dict) and progress:
        lines.extend(
            [
                f"- Phase Progress: {progress.get('completed_phases', 0)}/{progress.get('total_phases', 0)}",
                f"- Plan Progress: {progress.get('completed_plans', 0)}/{progress.get('total_plans', 0)}",
                f"- Percent: {progress.get('percent', 0)}%",
            ]
        )
    if isinstance(roadmap_analysis, dict) and roadmap_analysis:
        lines.extend(
            [
                f"- Roadmap Current Phase: {roadmap_analysis.get('current_phase') or '-'}",
                f"- Roadmap Next Phase: {roadmap_analysis.get('next_phase') or '-'}",
            ]
        )
    if phase_info:
        lines.extend(
            [
                "",
                "### Current Phase Overview",
                f"- Goal: {phase_info.get('goal') or '-'}",
                f"- Disk Status: {phase_info.get('disk_status') or '-'}",
                f"- Plans/Summaries: {phase_info.get('summary_count', 0)}/{phase_info.get('plan_count', 0)}",
                f"- Has Context/Research: {bool(phase_info.get('has_context'))}/{bool(phase_info.get('has_research'))}",
            ]
        )
    if isinstance(phase_index, dict) and phase_index.get("plans"):
        waves = phase_index.get("waves") or {}
        incomplete = phase_index.get("incomplete") or []
        lines.extend(
            [
                "",
                "### Phase Plan Index",
                f"- Waves: {len(waves)}",
                f"- Plans: {len(phase_index.get('plans') or [])}",
                f"- Incomplete: {', '.join(str(item) for item in incomplete) if incomplete else '-'}",
            ]
        )
    if assets.get("docs"):
        lines.extend(["", "### GSD Docs"])
        for key, path in (assets.get("docs") or {}).items():
            lines.append(f"- {key.upper()}: `{path}`")

    return {
        "assets": assets,
        "runtime": runtime,
        "state_snapshot": state_snapshot,
        "roadmap_analysis": roadmap_analysis,
        "phase": selected_phase,
        "phase_info": phase_info,
        "phase_index": phase_index,
        "markdown": "\n".join(lines).strip() + "\n",
    }


def build_gsd_route(
    root: Path,
    *,
    phase: str = "",
    prefer_pm_tasks: bool = True,
    project_mode: str = "",
) -> dict[str, Any]:
    assets = detect_gsd_assets(root)
    normalized_project_mode = str(project_mode or "").strip()
    runtime = gsd_runtime_status()

    def with_runtime(payload: dict[str, Any]) -> dict[str, Any]:
        payload["runtime"] = runtime
        return payload

    if not assets.get("enabled"):
        if normalized_project_mode == "brownfield":
            return with_runtime({
                "route": "bootstrap",
                "reason": "仓库尚未初始化 .planning，brownfield 项目应先理解现有代码。",
                "project_mode": normalized_project_mode,
                "phase": "",
                "recommended_gsd_skill": "gsd-map-codebase",
                "recommended_gsd_command": "$gsd-map-codebase",
                "recommended_pm_command": "pm init --repo-root <repo>",
                "recommended_mode": "bootstrap",
            })
        return with_runtime({
            "route": "bootstrap",
            "reason": "仓库尚未初始化 .planning，greenfield 项目应先创建项目规划骨架。",
            "project_mode": normalized_project_mode,
            "phase": "",
            "recommended_gsd_skill": "gsd-new-project",
            "recommended_gsd_command": "$gsd-new-project",
            "recommended_pm_command": "pm init --repo-root <repo>",
            "recommended_mode": "bootstrap",
        })

    snapshot = build_gsd_progress_snapshot(root, phase=phase)
    roadmap_analysis = snapshot.get("roadmap_analysis") if isinstance(snapshot.get("roadmap_analysis"), dict) else {}
    selected_phase = str(snapshot.get("phase") or phase or roadmap_analysis.get("current_phase") or roadmap_analysis.get("next_phase") or "").strip()
    phase_info = snapshot.get("phase_info") if isinstance(snapshot.get("phase_info"), dict) else {}
    phase_payload = list_gsd_phase_plans(root, phase=selected_phase) if selected_phase else {}
    plans = [item for item in (phase_payload.get("plans") or []) if isinstance(item, dict)]
    plan_count = len(plans) if plans else int(phase_info.get("plan_count") or 0)
    summary_count = sum(1 for item in plans if bool(item.get("has_summary"))) if plans else int(phase_info.get("summary_count") or 0)
    phase_dir = str(phase_payload.get("phase_dir") or "")
    phase_name = str(phase_payload.get("phase_name") or phase_info.get("name") or "")
    context_path = gsd_phase_context_path(phase_dir, str(phase_payload.get("phase") or selected_phase))
    has_context = bool(context_path and (root / context_path).exists()) or bool(phase_info.get("has_context"))

    if not selected_phase:
        return with_runtime({
            "route": "inspect",
            "reason": "已存在 .planning，但没有检测到当前 phase，需要人工确认当前项目状态。",
            "project_mode": normalized_project_mode,
            "phase": "",
            "recommended_gsd_skill": "gsd-progress",
            "recommended_gsd_command": "$gsd-progress",
            "recommended_pm_command": f"pm sync-gsd-progress --repo-root {root}",
            "recommended_mode": "inspect",
        })

    if plan_count == 0:
        if has_context:
            return with_runtime({
                "route": "plan-phase",
                "reason": f"Phase {selected_phase} 已有 CONTEXT，但还没有 PLAN，适合直接进入 phase planning。",
                "project_mode": normalized_project_mode,
                "phase": selected_phase,
                "phase_name": phase_name,
                "phase_dir": phase_dir,
                "context_path": context_path,
                "recommended_gsd_skill": "gsd-plan-phase",
                "recommended_gsd_command": f"$gsd-plan-phase {selected_phase} --text",
                "recommended_pm_command": f"pm plan-phase --repo-root {root} --phase {selected_phase}",
                "recommended_mode": "planning",
            })
        return with_runtime({
            "route": "discuss-phase",
            "reason": f"Phase {selected_phase} 还没有 CONTEXT 和 PLAN，应先做需求澄清/上下文收口。",
            "project_mode": normalized_project_mode,
            "phase": selected_phase,
            "phase_name": phase_name,
            "phase_dir": phase_dir,
            "context_path": context_path,
            "recommended_gsd_skill": "gsd-discuss-phase",
            "recommended_gsd_command": f"$gsd-discuss-phase {selected_phase}",
            "recommended_pm_command": "",
            "recommended_mode": "context-gathering",
        })

    if summary_count < plan_count:
        route = "materialize-tasks" if prefer_pm_tasks else "execute-phase"
        return with_runtime({
            "route": route,
            "reason": f"Phase {selected_phase} 已有 {plan_count} 份 PLAN、{summary_count} 份 SUMMARY，说明计划已就绪但尚未全部执行完成。",
            "project_mode": normalized_project_mode,
            "phase": selected_phase,
            "phase_name": phase_name,
            "phase_dir": phase_dir,
            "context_path": context_path,
            "recommended_gsd_skill": "none" if prefer_pm_tasks else "gsd-execute-phase",
            "recommended_gsd_command": "" if prefer_pm_tasks else f"$gsd-execute-phase {selected_phase}",
            "recommended_pm_command": f"pm materialize-gsd-tasks --repo-root {root} --phase {selected_phase}",
            "recommended_mode": "task-execution-via-feishu" if prefer_pm_tasks else "phase-execution",
        })

    next_phase = str(roadmap_analysis.get("next_phase") or "").strip()
    if next_phase:
        return with_runtime({
            "route": "verify-phase",
            "reason": f"Phase {selected_phase} 的 PLAN 已全部落地为 SUMMARY，适合做验证或准备进入下一 phase。",
            "project_mode": normalized_project_mode,
            "phase": selected_phase,
            "phase_name": phase_name,
            "phase_dir": phase_dir,
            "context_path": context_path,
            "recommended_gsd_skill": "gsd-verify-work",
            "recommended_gsd_command": f"$gsd-verify-work {selected_phase}",
            "recommended_pm_command": f"pm route-gsd --repo-root {root} --phase {next_phase}",
            "recommended_mode": "verification",
        })

    return with_runtime({
        "route": "new-milestone",
        "reason": "当前 milestone 看起来已经收口，下一步更像是开启新 milestone。",
        "project_mode": normalized_project_mode,
        "phase": selected_phase,
        "phase_name": phase_name,
        "phase_dir": phase_dir,
        "context_path": context_path,
        "recommended_gsd_skill": "gsd-new-milestone",
        "recommended_gsd_command": "$gsd-new-milestone",
        "recommended_pm_command": "",
        "recommended_mode": "milestone-transition",
    })
