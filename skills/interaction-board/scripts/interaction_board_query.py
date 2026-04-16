from __future__ import annotations

import re
from typing import Any


def normalize_query_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def node_query_values(node: dict[str, Any]) -> list[str]:
    aliases = node.get("aliases") or []
    board_meta = node.get("board_meta") or {}
    tags = board_meta.get("tags") or []
    refs = node.get("source_refs") or []
    values = [
        node.get("node_id", ""),
        node.get("route_key", ""),
        node.get("title", ""),
        node.get("route", ""),
        node.get("group", ""),
        node.get("package", ""),
        node.get("screen_component", ""),
        node.get("page_file", ""),
        node.get("config_file", ""),
        *(str(item) for item in aliases),
        *(str(item) for item in tags),
        *(f"{ref.get('path', '')}:{ref.get('line', '')}" for ref in refs if isinstance(ref, dict)),
    ]
    return [item for item in values if item]


def node_query_blob(node: dict[str, Any]) -> str:
    return " ".join(normalize_query_text(item) for item in node_query_values(node))


def score_node_match(node: dict[str, Any], query: str, *, exact: bool = False) -> tuple[int, list[str]] | None:
    normalized_query = normalize_query_text(query)
    if not normalized_query:
        return None

    title = normalize_query_text(node.get("title", ""))
    node_id = normalize_query_text(node.get("node_id", ""))
    route_key = normalize_query_text(node.get("route_key", ""))
    route = normalize_query_text(node.get("route", ""))
    aliases = {normalize_query_text(item) for item in (node.get("aliases") or []) if str(item).strip()}
    exact_values = {title, node_id, route_key, route, *aliases}
    reasons: list[str] = []

    if normalized_query in exact_values:
        if normalized_query == title:
            return 5200, ["title:exact"]
        if normalized_query == node_id:
            return 5180, ["node_id:exact"]
        if normalized_query == route_key:
            return 5160, ["route_key:exact"]
        if normalized_query == route:
            return 5140, ["route:exact"]
        return 5120, ["alias:exact"]

    if exact:
        return None

    score = 0
    blob = node_query_blob(node)
    if normalized_query in title:
        score += 820
        reasons.append("title:contains")
    if normalized_query in node_id:
        score += 780
        reasons.append("node_id:contains")
    if normalized_query in route_key:
        score += 720
        reasons.append("route_key:contains")
    if normalized_query in route:
        score += 700
        reasons.append("route:contains")
    if any(normalized_query in alias for alias in aliases):
        score += 660
        reasons.append("alias:contains")

    query_tokens = [token for token in normalized_query.split(" ") if token]
    if query_tokens and all(token in blob for token in query_tokens):
        score += 180 + len(query_tokens) * 12
        reasons.append("tokens:all")

    if score <= 0:
        return None
    return score, reasons


def node_images(node: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    card = node.get("card") or {}
    images = list(card.get("images") or node.get("screenshot_refs") or [])
    primary = dict(card.get("primary_image") or {})
    if not primary and images:
        primary = dict(images[0])
    return primary, images


def build_node_query_result(node: dict[str, Any], score: int, reasons: list[str]) -> dict[str, Any]:
    primary, images = node_images(node)
    scenarios = list((node.get("card") or {}).get("scenario_refs") or (node.get("board_meta") or {}).get("scenario_refs") or [])
    return {
        "node_id": node.get("node_id", ""),
        "route_key": node.get("route_key", ""),
        "title": node.get("title", ""),
        "route": node.get("route", ""),
        "status": node.get("status", ""),
        "group": node.get("group", ""),
        "package": node.get("package", ""),
        "match_score": score,
        "match_reasons": reasons,
        "code": {
            "screen_component": node.get("screen_component", ""),
            "page_file": node.get("page_file", ""),
            "config_file": node.get("config_file", ""),
            "source_refs": list(node.get("source_refs") or []),
        },
        "images": {
            "primary": primary,
            "versions": images,
            "version_count": len(images),
            "existing_version_count": sum(1 for item in images if item.get("exists", False)),
        },
        "scenarios": scenarios,
        "regions": list(node.get("regions") or []),
        "note": str((node.get("board_meta") or {}).get("note", "")),
    }


def compact_image_ref(image: dict[str, Any]) -> dict[str, Any]:
    if not image:
        return {}
    return {
        "label": image.get("label", ""),
        "relative_path": image.get("relative_path") or image.get("path", ""),
        "absolute_path": image.get("absolute_path", ""),
        "exists": bool(image.get("exists", False)),
    }


def compact_scenario_ref(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": scenario.get("scenario_id", ""),
        "scenario_path": scenario.get("scenario_path", ""),
        "script_path": scenario.get("script_path", ""),
        "engine": scenario.get("engine", ""),
        "role": scenario.get("role", ""),
        "capture_output": scenario.get("capture_output", ""),
    }


def compact_node_query_result(result: dict[str, Any]) -> dict[str, Any]:
    images = result.get("images") or {}
    versions = [compact_image_ref(item) for item in (images.get("versions") or [])]
    return {
        "node_id": result.get("node_id", ""),
        "route_key": result.get("route_key", ""),
        "title": result.get("title", ""),
        "route": result.get("route", ""),
        "status": result.get("status", ""),
        "group": result.get("group", ""),
        "package": result.get("package", ""),
        "match_score": result.get("match_score", 0),
        "match_reasons": list(result.get("match_reasons") or []),
        "code": {
            "screen_component": ((result.get("code") or {}).get("screen_component", "")),
            "page_file": ((result.get("code") or {}).get("page_file", "")),
            "config_file": ((result.get("code") or {}).get("config_file", "")),
        },
        "images": {
            "primary": compact_image_ref(images.get("primary") or {}),
            "versions": versions,
            "version_count": images.get("version_count", len(versions)),
            "existing_version_count": images.get(
                "existing_version_count",
                sum(1 for item in versions if item.get("exists", False)),
            ),
        },
        "scenarios": [compact_scenario_ref(item) for item in (result.get("scenarios") or [])],
        "regions": list(result.get("regions") or []),
        "note": result.get("note", ""),
    }


def paths_only_node_query_result(result: dict[str, Any]) -> dict[str, Any]:
    images = result.get("images") or {}
    versions = [compact_image_ref(item) for item in (images.get("versions") or [])]
    return {
        "node_id": result.get("node_id", ""),
        "title": result.get("title", ""),
        "route": result.get("route", ""),
        "code": {
            "screen_component": ((result.get("code") or {}).get("screen_component", "")),
            "page_file": ((result.get("code") or {}).get("page_file", "")),
            "config_file": ((result.get("code") or {}).get("config_file", "")),
        },
        "images": {
            "primary": compact_image_ref(images.get("primary") or {}),
            "versions": versions,
            "existing_version_count": images.get(
                "existing_version_count",
                sum(1 for item in versions if item.get("exists", False)),
            ),
        },
    }


def query_manifest_nodes(
    manifest: dict[str, Any],
    query: str,
    *,
    limit: int = 5,
    exact: bool = False,
    compact: bool = False,
    paths_only: bool = False,
) -> list[dict[str, Any]]:
    bounded = max(0, int(limit))
    normalized_query = normalize_query_text(query)
    if not normalized_query:
        nodes = [
            build_node_query_result(node, 0, ["list:all"])
            for node in manifest.get("nodes", [])
        ]
        if paths_only:
            nodes = [paths_only_node_query_result(node) for node in nodes]
            return nodes[:bounded] if bounded else nodes
        if compact:
            nodes = [compact_node_query_result(node) for node in nodes]
        return nodes[:bounded] if bounded else nodes

    matches: list[tuple[int, str, dict[str, Any]]] = []
    for node in manifest.get("nodes", []):
        scored = score_node_match(node, normalized_query, exact=exact)
        if not scored:
            continue
        score, reasons = scored
        matches.append((score, str(node.get("title", "")), build_node_query_result(node, score, reasons)))

    matches.sort(key=lambda item: (-item[0], item[1]))
    results = [item[2] for item in (matches[:bounded] if bounded else matches)]
    if paths_only:
        return [paths_only_node_query_result(item) for item in results]
    if compact:
        return [compact_node_query_result(item) for item in results]
    return results
