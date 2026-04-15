from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCENARIO_HINT_KEYS = {
    "scenario_id",
    "engine",
    "driver",
    "entry_node_id",
    "target_node_id",
    "target",
    "script_path",
    "capture",
    "context",
    "steps",
    "assertions",
}


def load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def scenario_engine(scenario: dict[str, Any]) -> str:
    return str(scenario.get("engine") or scenario.get("driver") or "").strip()


def is_web_playwright_scenario(scenario: dict[str, Any]) -> bool:
    engine = scenario_engine(scenario)
    if not engine:
        return True
    return engine.startswith("web-playwright") or engine == "playwright"


def default_script_path(scenario: dict[str, Any], scenario_id: str) -> str:
    explicit = str(scenario.get("script_path") or "").strip()
    if explicit:
        return explicit
    if is_web_playwright_scenario(scenario):
        return f"{scenario_id}.spec.ts"
    return ""


def render_storage_prelude(scenario: dict[str, Any]) -> list[str]:
    storage_items = scenario.get("context", {}).get("storage", [])
    if not storage_items:
        return []

    lines = [
        "  await page.addInitScript((entries) => {",
        "    for (const item of entries) {",
        "      window.localStorage.setItem(item.key, typeof item.value === \"string\" ? item.value : JSON.stringify(item.value));",
        "    }",
        "  }, storageEntries);",
    ]
    return lines


def render_step(step: dict[str, Any]) -> list[str]:
    action = str(step["action"])
    if action == "open":
        target = str(step["target"])
        return [f"  await page.goto(new URL({js(target)}, baseUrl).toString());"]
    if action == "tap":
        selector = str(step["selector"])
        return [f"  await page.locator({js(selector)}).click();"]
    if action in {"fill", "input"}:
        selector = str(step["selector"])
        value = str(step.get("value", ""))
        return [f"  await page.locator({js(selector)}).fill({js(value)});"]
    if action == "wait-text":
        target = str(step["target"])
        return [f"  await page.getByText({js(target)}).waitFor();"]
    if action == "wait":
        return [f"  await page.waitForTimeout({int(step.get('ms') or step.get('timeout_ms') or 1000)});"]
    if action in {"assert-route", "assert-path"}:
        target = str(step["target"])
        return [f"  await expect(page).toHaveURL(new RegExp({js(target)}));"]
    if action == "assert-text":
        target = str(step["target"])
        return [f"  await expect(page.getByText({js(target)})).toBeVisible();"]
    if action in {"screenshot", "capture"}:
        target = str(step["target"])
        return [f"  await page.screenshot({{ path: {js(target)}, fullPage: true }});"]
    raise ValueError(f"unsupported scenario action: {action}")


def render_assertion(assertion: dict[str, Any]) -> list[str]:
    assertion_type = str(assertion.get("type", "")).strip()
    if assertion_type == "path":
        value = str(assertion.get("value", ""))
        return [f"  await expect(page).toHaveURL(new RegExp({js(value)}));"]
    if assertion_type == "text":
        value = str(assertion.get("value", ""))
        return [f"  await expect(page.getByText({js(value)})).toBeVisible();"]
    if assertion_type == "selector":
        selector = str(assertion.get("selector", ""))
        min_count = int(assertion.get("min_count") or assertion.get("minCount") or 1)
        return [
            f"  expect(await page.locator({js(selector)}).count()).toBeGreaterThanOrEqual({min_count});",
        ]
    raise ValueError(f"unsupported scenario assertion: {assertion_type}")


def render_playwright_spec(scenario: dict[str, Any]) -> str:
    scenario_id = str(scenario.get("scenario_id", "board-scenario"))
    engine = scenario_engine(scenario)
    if engine and not is_web_playwright_scenario(scenario):
        raise ValueError(f"scenario engine {engine} cannot be rendered as Playwright spec")

    notes = str(scenario.get("context", {}).get("notes", "")).strip()
    storage_entries = scenario.get("context", {}).get("storage", [])
    base_url = str((scenario.get("target") or {}).get("base_url") or "http://127.0.0.1:3000")
    has_explicit_capture = any(str(step.get("action", "")) in {"screenshot", "capture"} for step in scenario.get("steps", []))
    capture_output = str((scenario.get("capture") or {}).get("output", "")).strip()

    lines = [
        'import { expect, test } from "@playwright/test";',
        "",
        f"test({js(scenario_id)}, async ({{ page }}) => {{",
        f"  const baseUrl = process.env.BOARD_BASE_URL || {js(base_url)};",
        f"  const storageEntries = {json.dumps(storage_entries, ensure_ascii=False, indent=2)};",
    ]
    if notes:
        lines.append(f"  // {notes}")
    lines.extend(render_storage_prelude(scenario))
    for step in scenario.get("steps", []):
        lines.extend(render_step(step))
    for assertion in scenario.get("assertions", []):
        lines.extend(render_assertion(assertion))
    if capture_output and not has_explicit_capture:
        lines.append(f"  await page.screenshot({{ path: {js(capture_output)}, fullPage: true }});")
    lines.append("});")
    lines.append("")
    return "\n".join(lines)


def write_playwright_spec(scenario_path: Path, output_path: Path) -> dict[str, str]:
    scenario = load_scenario(scenario_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_playwright_spec(scenario), encoding="utf-8")
    return {
        "scenario": str(scenario_path.resolve()),
        "output": str(output_path.resolve()),
        "scenario_id": str(scenario.get("scenario_id", "")),
    }


def is_scenario_contract(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if not any(key in payload for key in SCENARIO_HINT_KEYS):
        return False
    return bool(
        payload.get("entry_node_id")
        or payload.get("target_node_id")
        or payload.get("steps")
        or payload.get("script_path")
    )


def collect_scenario_bindings(scenarios_dir: Path) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    if not scenarios_dir.exists():
        return bindings

    for scenario_path in sorted(scenarios_dir.rglob("*.json")):
        scenario = load_scenario(scenario_path)
        if not is_scenario_contract(scenario):
            continue
        scenario_id = str(scenario.get("scenario_id") or scenario_path.stem)
        script_path = default_script_path(scenario, scenario_id)
        script_abs = str((scenario_path.parent / script_path).resolve()) if script_path else ""

        ref = {
            "scenario_id": scenario_id,
            "scenario_path": str(scenario_path.resolve()),
            "script_path": script_path,
            "script_absolute_path": script_abs,
            "capture_output": str((scenario.get("capture") or {}).get("output", "")),
            "engine": scenario_engine(scenario),
            "target": scenario.get("target") if isinstance(scenario.get("target"), dict) else {},
            "assertions": scenario.get("assertions") if isinstance(scenario.get("assertions"), list) else [],
        }

        target = str(scenario.get("target_node_id", "")).strip()
        if target:
            bindings.append({**ref, "node_ref": target, "role": "target"})

        entry = str(scenario.get("entry_node_id", "")).strip()
        if entry:
            bindings.append({**ref, "node_ref": entry, "role": "entry"})

    return bindings
