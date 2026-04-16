from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from interaction_board_core import (
    apply_board_overlay,
    attach_scenarios,
    attach_screenshots,
    extract_miniapp_manifest,
    hydrate_manifest_cards,
    read_text,
    refresh_manifest_summary,
    repo_now_iso,
    reset_screenshots_dir,
    write_screenshots_readme,
    write_text,
)
from interaction_board_query import query_manifest_nodes
from interaction_board_render import render_drawio_board, render_html_board, render_inventory_markdown
from interaction_board_scenarios import collect_scenario_bindings, write_playwright_spec
from interaction_board_web import extract_nextjs_manifest, scaffold_manifest_scenarios

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


def build_manual_board(
    manifest_path: Path,
    out_dir: Path,
    title: str | None = None,
    overlay_path: Path | None = None,
    scenario_dir: Path | None = None,
    *,
    replace_existing_scenarios: bool = False,
    skip_missing_scenarios: bool = False,
) -> dict[str, str]:
    manifest = load_manifest(manifest_path)
    manifest["generated_at"] = repo_now_iso()
    manifest = refresh_manifest_summary(manifest)
    manifest.setdefault("sources", {})["manifest_seed"] = str(manifest_path.resolve())
    if overlay_path:
        manifest = apply_board_overlay(manifest, load_manifest(overlay_path), str(overlay_path))
    if scenario_dir:
        manifest = attach_scenarios(
            manifest,
            collect_scenario_bindings(scenario_dir),
            replace_existing=replace_existing_scenarios,
            skip_missing_nodes=skip_missing_scenarios,
        )
    manifest = hydrate_manifest_cards(manifest, out_dir)
    manifest_path_out = out_dir / "board.manifest.json"
    drawio_path = out_dir / "board.drawio"
    html_path = out_dir / "index.html"
    inventory_path = out_dir / "inventory.md"
    screenshots_readme = out_dir / "screenshots" / "README.md"
    write_text(manifest_path_out, json.dumps(manifest, ensure_ascii=False, indent=2))
    write_text(drawio_path, render_drawio_board(manifest, title=title))
    write_text(html_path, render_html_board(manifest, title=title))
    write_text(inventory_path, render_inventory_markdown(manifest))
    write_screenshots_readme(screenshots_readme.parent, manifest)
    return {
        "manifest": str(manifest_path_out),
        "drawio": str(drawio_path),
        "html": str(html_path),
        "inventory": str(inventory_path),
        "screenshots_dir": str(screenshots_readme.parent),
    }


def build_nextjs_board(
    repo_root: Path,
    app_dir: str,
    out_dir: Path,
    *,
    title: str | None = None,
    app_name: str | None = None,
    app_kind: str = "web-admin",
    base_url: str = "",
    auth_surface: str = "admin",
    auth_profile: str = "",
    browser_channel: str = "chrome",
    viewport_size: str = "1440,1000",
    full_page: bool = True,
    scenario_prefix: str = "",
    write_specs: bool = True,
    force_scenarios: bool = False,
) -> dict[str, Any]:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = extract_nextjs_manifest(
        repo_root.resolve(),
        app_dir=app_dir,
        app_kind=app_kind,
        app_name=app_name,
    )
    seed_path = out_dir / "board.seed.json"
    write_text(seed_path, json.dumps(manifest, ensure_ascii=False, indent=2))

    scenario_report = scaffold_manifest_scenarios(
        manifest,
        out_dir / "scenarios",
        base_url=base_url,
        auth_surface=auth_surface,
        auth_profile=auth_profile,
        browser_channel=browser_channel,
        viewport_size=viewport_size,
        full_page=full_page,
        scenario_prefix=scenario_prefix,
        write_specs=write_specs,
        force=force_scenarios,
    )

    board_outputs = build_manual_board(
        seed_path,
        out_dir,
        title=title,
        scenario_dir=Path(scenario_report["scenario_dir"]),
        replace_existing_scenarios=True,
        skip_missing_scenarios=True,
    )

    return {
        "seed_manifest": str(seed_path),
        **board_outputs,
        "scenario_dir": str(scenario_report["scenario_dir"]),
        "scenario_count": scenario_report["scenario_count"],
    }


def _add_extract_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    extract = subparsers.add_parser("extract-miniapp", help="Extract a miniapp manifest from repo code.")
    extract.add_argument("--repo-root", required=True, help="Target repo root.")
    extract.add_argument("--output", required=True, help="Output manifest path.")

    extract_nextjs = subparsers.add_parser("extract-nextjs", help="Extract a Next.js Web/Admin manifest from app routes.")
    extract_nextjs.add_argument("--repo-root", required=True, help="Target repo root.")
    extract_nextjs.add_argument("--app-dir", default="apps/admin", help="Next.js app directory relative to repo root.")
    extract_nextjs.add_argument("--output", required=True, help="Output manifest path.")
    extract_nextjs.add_argument("--app-kind", default="web-admin", help="Manifest project app kind.")
    extract_nextjs.add_argument("--app-name", default="", help="Optional project/app name override.")


def _add_render_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
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

    scenario = subparsers.add_parser("render-scenario-spec", help="Render a Playwright spec from scenario JSON.")
    scenario.add_argument("--scenario", required=True, help="Scenario JSON path.")
    scenario.add_argument("--output", required=True, help="Output Playwright spec path.")


def _add_manifest_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
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
    attach_scenario.add_argument(
        "--skip-missing-nodes",
        action="store_true",
        help="Ignore scenario bindings whose entry/target nodes do not exist in the manifest.",
    )

    attach = subparsers.add_parser("attach-screenshots", help="Attach screenshots to an existing manifest.")
    attach.add_argument("--manifest", required=True, help="Manifest JSON path.")
    attach.add_argument("--source", action="append", required=True, help="Screenshot source in LABEL=PATH or PATH format.")
    attach.add_argument("--board-dir", default="", help="Board directory; defaults to the manifest parent.")
    attach.add_argument("--output", default="", help="Output manifest path; defaults to in-place update.")

    query = subparsers.add_parser("query-node", help="Query node code paths and version screenshots from a manifest.")
    query.add_argument("--manifest", required=True, help="Manifest JSON path.")
    query.add_argument("--query", default="", help="Search text: title, route, node_id, route_key or alias. Leave empty to list all nodes.")
    query.add_argument("--limit", type=int, default=0, help="Maximum number of matches to return. 0 means no limit.")
    query.add_argument("--exact", action="store_true", help="Require exact match against title / route / node_id / aliases.")
    query.add_argument(
        "--compact",
        action="store_true",
        help="Return a lightweight node view with code entry files and image paths only.",
    )
    query.add_argument(
        "--paths-only",
        action="store_true",
        help="Return the thinnest node view with page code paths and version image paths only.",
    )


def _add_scenario_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    scaffold = subparsers.add_parser("scaffold-scenarios", help="Generate one scenario stub per manifest node.")
    scaffold.add_argument("--manifest", required=True, help="Manifest JSON path.")
    scaffold.add_argument("--scenario-dir", required=True, help="Output scenario directory.")
    scaffold.add_argument("--base-url", required=True, help="Base URL used by generated Web scenarios.")
    scaffold.add_argument("--auth-surface", default="admin", help="Auth surface written into target.")
    scaffold.add_argument("--auth-profile", default="", help="Auth profile written into target.")
    scaffold.add_argument("--browser-channel", default="chrome", help="Browser channel written into target.")
    scaffold.add_argument("--viewport-size", default="1440,1000", help="Viewport written into target.")
    scaffold.add_argument("--scenario-prefix", default="", help="Optional scenario ID prefix.")
    scaffold.add_argument("--no-full-page", action="store_true", help="Disable full page screenshots in generated target config.")
    scaffold.add_argument("--write-specs", action="store_true", help="Also generate Playwright specs for each scenario.")
    scaffold.add_argument("--force", action="store_true", help="Overwrite existing scenario/spec files.")


def _add_build_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    manual = subparsers.add_parser(
        "build-manual-board",
        help="Build manifest + drawio + html + inventory from a manual/seed manifest.",
    )
    manual.add_argument("--manifest", required=True, help="Seed manifest JSON path.")
    manual.add_argument("--out-dir", required=True, help="Output board directory.")
    manual.add_argument("--title", default="", help="Optional board title override.")
    manual.add_argument("--overlay", default="", help="Optional board overlay JSON path.")
    manual.add_argument("--scenario-dir", default="", help="Optional scenario JSON directory.")
    manual.add_argument(
        "--replace-existing-scenarios",
        action="store_true",
        help="Clear existing scenario refs before attaching new bindings.",
    )
    manual.add_argument(
        "--skip-missing-scenarios",
        action="store_true",
        help="Ignore scenario bindings whose entry/target nodes are absent from the seed manifest.",
    )

    sample = subparsers.add_parser("build-miniapp-sample", help="Build manifest + drawio + html + inventory.")
    sample.add_argument("--repo-root", required=True, help="Target repo root.")
    sample.add_argument("--out-dir", required=True, help="Output directory.")
    sample.add_argument("--title", default="", help="Optional board title override.")
    sample.add_argument("--source", action="append", default=[], help="Optional screenshot source in LABEL=PATH or PATH format.")
    sample.add_argument("--overlay", default="", help="Optional board overlay JSON path.")
    sample.add_argument("--scenario-dir", default="", help="Optional scenario JSON directory.")

    web_board = subparsers.add_parser("build-nextjs-board", help="Route-first Next.js board build with scenario scaffolding.")
    web_board.add_argument("--repo-root", required=True, help="Target repo root.")
    web_board.add_argument("--app-dir", default="apps/admin", help="Next.js app directory relative to repo root.")
    web_board.add_argument("--out-dir", required=True, help="Output board directory.")
    web_board.add_argument("--title", default="", help="Optional board title override.")
    web_board.add_argument("--app-kind", default="web-admin", help="Manifest project app kind.")
    web_board.add_argument("--app-name", default="", help="Optional project/app name override.")
    web_board.add_argument("--base-url", required=True, help="Base URL written into generated scenarios.")
    web_board.add_argument("--auth-surface", default="admin", help="Auth surface written into generated scenarios.")
    web_board.add_argument("--auth-profile", default="", help="Auth profile written into generated scenarios.")
    web_board.add_argument("--browser-channel", default="chrome", help="Browser channel written into generated scenarios.")
    web_board.add_argument("--viewport-size", default="1440,1000", help="Viewport written into generated scenarios.")
    web_board.add_argument("--scenario-prefix", default="", help="Optional scenario ID prefix.")
    web_board.add_argument("--no-full-page", action="store_true", help="Disable full page screenshots in generated target config.")
    web_board.add_argument("--no-specs", action="store_true", help="Skip Playwright spec generation.")
    web_board.add_argument("--force-scenarios", action="store_true", help="Overwrite existing scenario/spec files.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build interaction board artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_extract_commands(subparsers)
    _add_render_commands(subparsers)
    _add_manifest_commands(subparsers)
    _add_scenario_commands(subparsers)
    _add_build_commands(subparsers)
    return parser


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def _emit(payload: dict[str, Any], *, indent: int | None = None) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=indent))
    return 0


def _write_manifest_output(output_path: Path, manifest: dict[str, Any]) -> int:
    write_text(output_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    return _emit({"manifest": str(output_path), "summary": manifest["summary"]})


def _resolve_optional_path(value: str) -> Path | None:
    return Path(value).resolve() if value else None


def _handle_extract_miniapp(args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    manifest = extract_miniapp_manifest(Path(args.repo_root).resolve())
    manifest = hydrate_manifest_cards(manifest, output_path.parent)
    return _write_manifest_output(output_path, manifest)


def _handle_extract_nextjs(args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    manifest = extract_nextjs_manifest(
        Path(args.repo_root).resolve(),
        app_dir=args.app_dir,
        app_kind=args.app_kind,
        app_name=args.app_name or None,
    )
    manifest = hydrate_manifest_cards(manifest, output_path.parent)
    return _write_manifest_output(output_path, manifest)


def _handle_render_drawio(args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    manifest = load_manifest(Path(args.manifest).resolve())
    write_text(output_path, render_drawio_board(manifest, title=args.title or None))
    return _emit({"drawio": str(output_path)})


def _handle_render_html(args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    manifest = load_manifest(Path(args.manifest).resolve())
    write_text(output_path, render_html_board(manifest, title=args.title or None))
    return _emit({"html": str(output_path)})


def _handle_render_inventory(args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    manifest = load_manifest(Path(args.manifest).resolve())
    write_text(output_path, render_inventory_markdown(manifest))
    return _emit({"inventory": str(output_path)})


def _handle_apply_overlay(args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    manifest = apply_board_overlay(
        load_manifest(Path(args.manifest).resolve()),
        load_manifest(Path(args.overlay).resolve()),
        str(Path(args.overlay).resolve()),
    )
    manifest = hydrate_manifest_cards(manifest, output_path.parent)
    return _write_manifest_output(output_path, manifest)


def _handle_attach_scenarios(args: argparse.Namespace) -> int:
    output_path = Path(args.output).resolve()
    manifest = attach_scenarios(
        load_manifest(Path(args.manifest).resolve()),
        collect_scenario_bindings(Path(args.scenario_dir).resolve()),
        replace_existing=args.replace_existing,
        skip_missing_nodes=args.skip_missing_nodes,
    )
    manifest = hydrate_manifest_cards(manifest, output_path.parent)
    return _write_manifest_output(output_path, manifest)


def _handle_render_scenario_spec(args: argparse.Namespace) -> int:
    result = write_playwright_spec(Path(args.scenario).resolve(), Path(args.output).resolve())
    return _emit(result)


def _handle_scaffold_scenarios(args: argparse.Namespace) -> int:
    report = scaffold_manifest_scenarios(
        load_manifest(Path(args.manifest).resolve()),
        Path(args.scenario_dir).resolve(),
        base_url=args.base_url,
        auth_surface=args.auth_surface,
        auth_profile=args.auth_profile,
        browser_channel=args.browser_channel,
        viewport_size=args.viewport_size,
        full_page=not args.no_full_page,
        scenario_prefix=args.scenario_prefix,
        write_specs=args.write_specs,
        force=args.force,
    )
    return _emit(report, indent=2)


def _handle_attach_screenshots(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    board_dir = Path(args.board_dir).resolve() if args.board_dir else manifest_path.parent
    output_path = Path(args.output).resolve() if args.output else manifest_path
    reset_screenshots_dir(board_dir / "screenshots")
    manifest = attach_screenshots(load_manifest(manifest_path), args.source, board_dir)
    manifest = hydrate_manifest_cards(manifest, board_dir)
    write_text(output_path, json.dumps(manifest, ensure_ascii=False, indent=2))
    write_screenshots_readme(board_dir / "screenshots", manifest)
    return _emit({"manifest": str(output_path), "summary": manifest["summary"]})


def _handle_query_node(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest).resolve()
    matches = query_manifest_nodes(
        load_manifest(manifest_path),
        args.query,
        limit=args.limit,
        exact=args.exact,
        compact=args.compact,
        paths_only=args.paths_only,
    )
    payload = {
        "manifest": str(manifest_path),
        "query": args.query,
        "exact": bool(args.exact),
        "compact": bool(args.compact),
        "paths_only": bool(args.paths_only),
        "match_count": len(matches),
        "matches": matches,
    }
    return _emit(payload, indent=2)


def _handle_build_miniapp_sample(args: argparse.Namespace) -> int:
    outputs = build_sample(
        Path(args.repo_root).resolve(),
        Path(args.out_dir).resolve(),
        title=args.title or None,
        screenshot_sources=args.source,
        overlay_path=_resolve_optional_path(args.overlay),
        scenario_dir=_resolve_optional_path(args.scenario_dir),
    )
    return _emit(outputs)


def _handle_build_manual_board(args: argparse.Namespace) -> int:
    outputs = build_manual_board(
        Path(args.manifest).resolve(),
        Path(args.out_dir).resolve(),
        title=args.title or None,
        overlay_path=_resolve_optional_path(args.overlay),
        scenario_dir=_resolve_optional_path(args.scenario_dir),
        replace_existing_scenarios=args.replace_existing_scenarios,
        skip_missing_scenarios=args.skip_missing_scenarios,
    )
    return _emit(outputs)


def _handle_build_nextjs_board(args: argparse.Namespace) -> int:
    outputs = build_nextjs_board(
        Path(args.repo_root).resolve(),
        args.app_dir,
        Path(args.out_dir).resolve(),
        title=args.title or None,
        app_name=args.app_name or None,
        app_kind=args.app_kind,
        base_url=args.base_url,
        auth_surface=args.auth_surface,
        auth_profile=args.auth_profile,
        browser_channel=args.browser_channel,
        viewport_size=args.viewport_size,
        full_page=not args.no_full_page,
        scenario_prefix=args.scenario_prefix,
        write_specs=not args.no_specs,
        force_scenarios=args.force_scenarios,
    )
    return _emit(outputs)


def _command_handlers() -> dict[str, Callable[[argparse.Namespace], int]]:
    return {
        "extract-miniapp": _handle_extract_miniapp,
        "extract-nextjs": _handle_extract_nextjs,
        "render-drawio": _handle_render_drawio,
        "render-html": _handle_render_html,
        "render-inventory": _handle_render_inventory,
        "apply-overlay": _handle_apply_overlay,
        "attach-scenarios": _handle_attach_scenarios,
        "render-scenario-spec": _handle_render_scenario_spec,
        "scaffold-scenarios": _handle_scaffold_scenarios,
        "attach-screenshots": _handle_attach_screenshots,
        "query-node": _handle_query_node,
        "build-miniapp-sample": _handle_build_miniapp_sample,
        "build-manual-board": _handle_build_manual_board,
        "build-nextjs-board": _handle_build_nextjs_board,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler = _command_handlers().get(args.command)
    if handler is None:
        raise SystemExit(f"unknown command: {args.command}")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
