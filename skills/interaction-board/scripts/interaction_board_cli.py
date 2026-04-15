from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from interaction_board_core import (
    apply_board_overlay,
    attach_scenarios,
    attach_screenshots,
    extract_miniapp_manifest,
    hydrate_manifest_cards,
    read_text,
    reset_screenshots_dir,
    write_screenshots_readme,
    write_text,
)
from interaction_board_render import render_drawio_board, render_html_board, render_inventory_markdown
from interaction_board_scenarios import collect_scenario_bindings, write_playwright_spec

def build_sample(
    repo_root: Path,
    out_dir: Path,
    title: str | None = None,
    screenshot_sources: list[str] | None = None,
    overlay_path: Path | None = None,
    scenario_dir: Path | None = None,
) -> dict[str, str]:
    reset_screenshots_dir(out_dir / "screenshots")
    manifest = extract_miniapp_manifest(repo_root)
    if screenshot_sources:
        manifest = attach_screenshots(manifest, screenshot_sources, out_dir)
    if overlay_path:
        manifest = apply_board_overlay(manifest, load_manifest(overlay_path), str(overlay_path))
    if scenario_dir:
        manifest = attach_scenarios(manifest, collect_scenario_bindings(scenario_dir))
    manifest = hydrate_manifest_cards(manifest, out_dir)
    manifest_path = out_dir / "board.manifest.json"
    drawio_path = out_dir / "board.drawio"
    html_path = out_dir / "index.html"
    inventory_path = out_dir / "inventory.md"
    screenshots_readme = out_dir / "screenshots" / "README.md"
    write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    write_text(drawio_path, render_drawio_board(manifest, title=title))
    write_text(html_path, render_html_board(manifest, title=title))
    write_text(inventory_path, render_inventory_markdown(manifest))
    write_screenshots_readme(screenshots_readme.parent, manifest)
    return {
        "manifest": str(manifest_path),
        "drawio": str(drawio_path),
        "html": str(html_path),
        "inventory": str(inventory_path),
        "screenshots_dir": str(screenshots_readme.parent),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build interaction board artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract-miniapp", help="Extract a miniapp manifest from repo code.")
    extract.add_argument("--repo-root", required=True, help="Target repo root.")
    extract.add_argument("--output", required=True, help="Output manifest path.")

    render_drawio = subparsers.add_parser("render-drawio", help="Render draw.io from manifest.")
    render_drawio.add_argument("--manifest", required=True, help="Manifest JSON path.")
    render_drawio.add_argument("--output", required=True, help="Output drawio path.")
    render_drawio.add_argument("--title", default="", help="Optional board title override.")

    render_html = subparsers.add_parser("render-html", help="Render HTML board from manifest.")
    render_html.add_argument("--manifest", required=True, help="Manifest JSON path.")
    render_html.add_argument("--output", required=True, help="Output HTML path.")
    render_html.add_argument("--title", default="", help="Optional board title override.")

    render_inventory = subparsers.add_parser("render-inventory", help="Render inventory markdown from manifest.")
    render_inventory.add_argument("--manifest", required=True, help="Manifest JSON path.")
    render_inventory.add_argument("--output", required=True, help="Output markdown path.")

    apply_overlay = subparsers.add_parser("apply-overlay", help="Merge a lightweight board overlay into a manifest.")
    apply_overlay.add_argument("--manifest", required=True, help="Manifest JSON path.")
    apply_overlay.add_argument("--overlay", required=True, help="Overlay JSON path.")
    apply_overlay.add_argument("--output", required=True, help="Output manifest path.")

    attach_scenario = subparsers.add_parser("attach-scenarios", help="Attach scenario bindings into a manifest.")
    attach_scenario.add_argument("--manifest", required=True, help="Manifest JSON path.")
    attach_scenario.add_argument("--scenario-dir", required=True, help="Scenario JSON directory.")
    attach_scenario.add_argument("--output", required=True, help="Output manifest path.")
    attach_scenario.add_argument(
        "--replace-existing",
        action="store_true",
        help="Clear existing scenario refs before attaching new bindings.",
    )

    scenario = subparsers.add_parser("render-scenario-spec", help="Render a Playwright spec from scenario JSON.")
    scenario.add_argument("--scenario", required=True, help="Scenario JSON path.")
    scenario.add_argument("--output", required=True, help="Output Playwright spec path.")

    attach = subparsers.add_parser("attach-screenshots", help="Attach screenshots to an existing manifest.")
    attach.add_argument("--manifest", required=True, help="Manifest JSON path.")
    attach.add_argument("--source", action="append", required=True, help="Screenshot source in LABEL=PATH or PATH format.")
    attach.add_argument("--board-dir", default="", help="Board directory; defaults to the manifest parent.")
    attach.add_argument("--output", default="", help="Output manifest path; defaults to in-place update.")

    sample = subparsers.add_parser("build-miniapp-sample", help="Build manifest + drawio + html + inventory.")
    sample.add_argument("--repo-root", required=True, help="Target repo root.")
    sample.add_argument("--out-dir", required=True, help="Output directory.")
    sample.add_argument("--title", default="", help="Optional board title override.")
    sample.add_argument("--source", action="append", default=[], help="Optional screenshot source in LABEL=PATH or PATH format.")
    sample.add_argument("--overlay", default="", help="Optional board overlay JSON path.")
    sample.add_argument("--scenario-dir", default="", help="Optional scenario JSON directory.")
    return parser


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "extract-miniapp":
        manifest = extract_miniapp_manifest(Path(args.repo_root).resolve())
        manifest = hydrate_manifest_cards(manifest, Path(args.output).resolve().parent)
        write_text(Path(args.output).resolve(), json.dumps(manifest, ensure_ascii=False, indent=2))
        print(json.dumps({"manifest": str(Path(args.output).resolve()), "summary": manifest["summary"]}, ensure_ascii=False))
        return 0
    if args.command == "render-drawio":
        manifest = load_manifest(Path(args.manifest).resolve())
        write_text(Path(args.output).resolve(), render_drawio_board(manifest, title=args.title or None))
        print(json.dumps({"drawio": str(Path(args.output).resolve())}, ensure_ascii=False))
        return 0
    if args.command == "render-html":
        manifest = load_manifest(Path(args.manifest).resolve())
        write_text(Path(args.output).resolve(), render_html_board(manifest, title=args.title or None))
        print(json.dumps({"html": str(Path(args.output).resolve())}, ensure_ascii=False))
        return 0
    if args.command == "render-inventory":
        manifest = load_manifest(Path(args.manifest).resolve())
        write_text(Path(args.output).resolve(), render_inventory_markdown(manifest))
        print(json.dumps({"inventory": str(Path(args.output).resolve())}, ensure_ascii=False))
        return 0
    if args.command == "apply-overlay":
        manifest = apply_board_overlay(
            load_manifest(Path(args.manifest).resolve()),
            load_manifest(Path(args.overlay).resolve()),
            str(Path(args.overlay).resolve()),
        )
        manifest = hydrate_manifest_cards(manifest, Path(args.output).resolve().parent)
        write_text(Path(args.output).resolve(), json.dumps(manifest, ensure_ascii=False, indent=2))
        print(json.dumps({"manifest": str(Path(args.output).resolve()), "summary": manifest["summary"]}, ensure_ascii=False))
        return 0
    if args.command == "attach-scenarios":
        manifest = attach_scenarios(
            load_manifest(Path(args.manifest).resolve()),
            collect_scenario_bindings(Path(args.scenario_dir).resolve()),
            replace_existing=args.replace_existing,
        )
        manifest = hydrate_manifest_cards(manifest, Path(args.output).resolve().parent)
        write_text(Path(args.output).resolve(), json.dumps(manifest, ensure_ascii=False, indent=2))
        print(json.dumps({"manifest": str(Path(args.output).resolve()), "summary": manifest["summary"]}, ensure_ascii=False))
        return 0
    if args.command == "render-scenario-spec":
        result = write_playwright_spec(Path(args.scenario).resolve(), Path(args.output).resolve())
        print(json.dumps(result, ensure_ascii=False))
        return 0
    if args.command == "attach-screenshots":
        manifest_path = Path(args.manifest).resolve()
        board_dir = Path(args.board_dir).resolve() if args.board_dir else manifest_path.parent
        output_path = Path(args.output).resolve() if args.output else manifest_path
        reset_screenshots_dir(board_dir / "screenshots")
        manifest = attach_screenshots(load_manifest(manifest_path), args.source, board_dir)
        manifest = hydrate_manifest_cards(manifest, board_dir)
        write_text(output_path, json.dumps(manifest, ensure_ascii=False, indent=2))
        write_screenshots_readme(board_dir / "screenshots", manifest)
        print(json.dumps({"manifest": str(output_path), "summary": manifest["summary"]}, ensure_ascii=False))
        return 0
    if args.command == "build-miniapp-sample":
        outputs = build_sample(
            Path(args.repo_root).resolve(),
            Path(args.out_dir).resolve(),
            title=args.title or None,
            screenshot_sources=args.source,
            overlay_path=Path(args.overlay).resolve() if args.overlay else None,
            scenario_dir=Path(args.scenario_dir).resolve() if args.scenario_dir else None,
        )
        print(json.dumps(outputs, ensure_ascii=False))
        return 0
    raise SystemExit(f"unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
