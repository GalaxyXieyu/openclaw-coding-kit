#!/usr/bin/env python3
"""Thin public entrypoint for interaction-board."""

from __future__ import annotations

from interaction_board_cli import build_parser, build_sample, load_manifest, main
from interaction_board_core import (
    GROUP_ORDER,
    PACKAGE_STYLE,
    STATUS_BADGE,
    apply_board_overlay,
    attach_scenarios,
    attach_screenshots,
    extract_miniapp_manifest,
    hydrate_manifest_cards,
    planned_screenshot_ref,
    refresh_manifest_summary,
    screenshot_status,
)
from interaction_board_render import render_drawio_board, render_html_board, render_inventory_markdown
from interaction_board_scenarios import collect_scenario_bindings, load_scenario, render_playwright_spec, write_playwright_spec

__all__ = [
    "GROUP_ORDER",
    "PACKAGE_STYLE",
    "STATUS_BADGE",
    "apply_board_overlay",
    "attach_scenarios",
    "attach_screenshots",
    "build_parser",
    "build_sample",
    "extract_miniapp_manifest",
    "hydrate_manifest_cards",
    "load_manifest",
    "main",
    "planned_screenshot_ref",
    "refresh_manifest_summary",
    "render_drawio_board",
    "render_html_board",
    "render_inventory_markdown",
    "render_playwright_spec",
    "screenshot_status",
    "load_scenario",
    "write_playwright_spec",
]


if __name__ == "__main__":
    raise SystemExit(main())
    "collect_scenario_bindings",
