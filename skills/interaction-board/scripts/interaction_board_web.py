from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from interaction_board_core import (
    planned_screenshot_ref,
    refresh_manifest_summary,
    repo_now_iso,
    slugify,
    write_text,
)
from interaction_board_scenarios import write_playwright_spec


@dataclass(frozen=True)
class RouteFile:
    route: str
    page_path: Path
    relative_page_path: str
    node_id: str
    route_key: str
    group: str


@dataclass(frozen=True)
class RouteRef:
    route: str
    line: int
    trigger: str
    kind: str
    label: str


WEB_GROUP_ORDER = {
    "entry": 0,
    "admin": 1,
    "users": 2,
    "commerce": 3,
    "settings": 4,
    "other": 9,
}

NEXTJS_NAV_EDGE_SOURCES = (
    ("dashboard", "components/dashboard/nav-config.ts", "sidebar"),
    ("dashboard", "components/dashboard/dashboard-top-tabs.tsx", "top-tabs"),
    ("dashboard/commerce", "components/dashboard/dashboard-commerce-tabs.tsx", "commerce-tabs"),
    ("dashboard/settings", "components/dashboard/dashboard-settings-tabs.tsx", "settings-tabs"),
)

ROUTE_LABEL_OVERRIDES = {
    "": "后台根入口",
    "login": "后台登录",
    "dashboard": "平台概况",
    "dashboard/tenant-management": "平台用户",
    "dashboard/tenants/[tenantId]": "用户详情",
    "dashboard/tenants/[tenantId]/livestock": "宠物档案摘要",
    "dashboard/analytics": "活跃度看板",
    "dashboard/analytics/activity": "活跃度看板",
    "dashboard/analytics/revenue": "付费看板",
    "dashboard/usage": "用量看板",
    "dashboard/audit-logs": "治理记录",
    "dashboard/billing": "账单跳转",
    "dashboard/guiquan-management": "社区入口",
    "dashboard/memberships": "会员入口",
    "dashboard/commerce": "经营入口",
    "dashboard/commerce/catalog": "商品目录",
    "dashboard/commerce/catalog/new": "新建商品",
    "dashboard/commerce/catalog/[productId]": "商品详情",
    "dashboard/commerce/community": "社区治理",
    "dashboard/commerce/community/new": "新建帖子",
    "dashboard/commerce/community/[postId]": "帖子详情",
    "dashboard/commerce/marketplace": "二级市场",
    "dashboard/commerce/marketplace/[listingId]": "挂牌详情",
    "dashboard/commerce/orders": "订单管理",
    "dashboard/commerce/support": "售后客服",
    "dashboard/commerce/fulfillment": "发货履约",
    "dashboard/settings": "设置入口",
    "dashboard/settings/pricing": "套餐定价",
    "dashboard/settings/platform-branding": "平台品牌",
    "dashboard/settings/tenant-branding": "租户品牌",
    "dashboard/settings/market-intelligence": "行情参考",
    "dashboard/settings/footprint-achievements": "徽章素材",
    "dashboard/settings/audit-logs": "审计记录",
    "dashboard/settings/notifications": "通知健康",
    "dashboard/settings/supply": "供给入口",
}

SCENARIO_SKIP_SEGMENTS = {"api"}
TEXT_LITERAL_RE = re.compile(r"'([^'\\]*(?:\\.[^'\\]*)*)'|\"([^\"\\]*(?:\\.[^\"\\]*)*)\"")
ITEM_BLOCK_RE = re.compile(
    r"\{(?P<body>[^{}]*?href:\s*['\"](?P<href>/[^'\"]*)['\"][^{}]*?label:\s*\{\s*zh:\s*['\"](?P<label>[^'\"]+)['\"])",
    re.S,
)
STATIC_ROUTE_RE = re.compile(r"(?<![\w/])(?:/dashboard(?:/[A-Za-z0-9\-\[\]]+)*)|/login\b")
TEMPLATE_ROUTE_RE = re.compile(r"`(/dashboard[^`]*|/login[^`]*)`")
LOCALE_IMPORT_RE = re.compile(
    r"import\s*\{(?P<names>[^}]+)\}\s*from\s*['\"]@/lib/locales/[^'\"]+['\"]",
    re.S,
)
IMPORT_SOURCE_RE = re.compile(r"import\s+(?:type\s+)?(?:[^;]+?)\s+from\s*['\"]([^'\"]+)['\"]")
HTML_ID_RE = re.compile(r"\bid=['\"]([^'\"]+)['\"]")
FORM_CLASS_RE = re.compile(r"<form[^>]*className=['\"]([^'\"]+)['\"]", re.S)
HEADING_LITERAL_RE = re.compile(r"<h[1-4][^>]*>\s*([^<{][^<]{0,80})\s*</h[1-4]>", re.S)
GENERIC_SELECTOR_TOKENS = {
    "app",
    "body",
    "content",
    "container",
    "error",
    "form",
    "layout",
    "main",
    "muted",
    "page",
    "panel",
    "root",
    "row",
    "section",
    "secondary",
    "stack",
    "success",
    "wrapper",
}


def route_to_path(route: str) -> str:
    return "/" if not route else f"/{route.lstrip('/')}"


def route_to_node_id(route: str, app_kind: str) -> str:
    prefix = "admin" if "admin" in app_kind else slugify(app_kind or "web")
    if not route:
        return f"{prefix}-root"
    return f"{prefix}-{slugify(route)}"


def route_to_route_key(route: str, app_kind: str) -> str:
    base = "root" if not route else re.sub(r"[^a-zA-Z0-9]+", " ", route).title().replace(" ", "")
    prefix = "Admin" if "admin" in app_kind else "Web"
    return f"{prefix}{base}"


def route_group(route: str) -> str:
    normalized = route.strip("/")
    if normalized in {"", "login"}:
        return "entry"
    if normalized.startswith("dashboard/settings"):
        return "settings"
    if normalized.startswith("dashboard/commerce"):
        return "commerce"
    if normalized.startswith("dashboard/tenant") or normalized.startswith("dashboard/tenants") or normalized.startswith("dashboard/memberships"):
        return "users"
    if normalized.startswith("dashboard"):
        return "admin"
    return "other"


def route_sort_key(route: str) -> tuple[int, int, str]:
    group = route_group(route)
    return (WEB_GROUP_ORDER.get(group, 99), route.count("/"), route)


def route_match_key(route: str) -> str:
    normalized = str(route).split("?", 1)[0].strip().lstrip("/")
    normalized = re.sub(r"\$\{[^}]+\}", "[]", normalized)
    normalized = re.sub(r"\[[^/\]]+\]", "[]", normalized)
    normalized = re.sub(r"/+", "/", normalized).strip("/")
    return normalized


def humanize_route(route: str) -> str:
    if route in ROUTE_LABEL_OVERRIDES:
        return ROUTE_LABEL_OVERRIDES[route]
    tail = route.strip("/").split("/")[-1] if route else "root"
    if tail.startswith("[") and tail.endswith("]"):
        tail = tail[1:-1]
    tail = tail.replace("-", " ").replace("_", " ").strip() or "page"
    return " ".join(part.capitalize() for part in tail.split())


def derive_route_from_page(page_path: Path, app_root: Path) -> str:
    relative = page_path.relative_to(app_root / "app")
    segments = relative.parts[:-1]
    return "/".join(segments)


def line_number_for(content: str, needle: str) -> int:
    index = content.find(needle)
    if index < 0:
        return 1
    return content[:index].count("\n") + 1


def relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def parse_locale_title_index(locale_root: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    if not locale_root.exists():
        return index

    for locale_file in sorted(locale_root.rglob("*.ts")):
        text = locale_file.read_text(encoding="utf-8")
        matches = list(re.finditer(r"export const ([A-Z0-9_]+)\s*=", text))
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            block = text[start:end]
            title_match = re.search(r"zh:\s*\{.*?title:\s*'([^']+)'", block, re.S)
            if title_match:
                index[match.group(1)] = title_match.group(1).strip()
    return index


def parse_title_from_nav_source(text: str, route: str) -> str:
    target = route_to_path(route)
    for match in ITEM_BLOCK_RE.finditer(text):
        if match.group("href").strip() == target:
            return match.group("label").strip()
    return ""


def derive_route_title(
    route: str,
    page_text: str,
    locale_index: dict[str, str],
    nav_title_index: dict[str, str],
) -> tuple[str, int]:
    for match in re.finditer(r"title:\s*'([^']+)'", page_text):
        value = match.group(1).strip()
        if value and not value.startswith("http"):
            return value, line_number_for(page_text, match.group(0))

    for import_match in LOCALE_IMPORT_RE.finditer(page_text):
        raw_names = import_match.group("names")
        names = [item.strip() for item in raw_names.split(",") if item.strip()]
        for name in names:
            title = locale_index.get(name)
            if title:
                return title, line_number_for(page_text, name)

    if route in nav_title_index:
        return nav_title_index[route], 1

    return humanize_route(route), 1


def derive_regions(title: str, page_text: str) -> list[str]:
    regions: list[str] = []
    seen = {title}
    if title:
        regions.append(title)

    for match in TEXT_LITERAL_RE.finditer(page_text):
        value = (match.group(1) or match.group(2) or "").strip()
        if not value:
            continue
        if value in seen:
            continue
        if value.startswith("/") or value.startswith("http") or len(value) > 40:
            continue
        if re.search(r"[{}$<>]", value):
            continue
        if not re.search(r"[\u4e00-\u9fffA-Za-z]", value):
            continue
        if value.lower() in {"zh", "en", "get", "post", "login"}:
            continue
        regions.append(value)
        seen.add(value)
        if len(regions) >= 4:
            break

    return regions


def resolve_import_path(import_path: str, source_path: Path, app_root: Path | None) -> Path | None:
    normalized = import_path.strip()
    if not normalized:
        return None

    if normalized.startswith("@/"):
        if not app_root:
            return None
        base = (app_root / normalized[2:]).resolve()
    elif normalized.startswith("."):
        base = (source_path.parent / normalized).resolve()
    else:
        return None

    candidates: list[Path] = []
    if base.suffix:
        candidates.append(base)
    else:
        candidates.extend(
            [
                base.with_suffix(".tsx"),
                base.with_suffix(".ts"),
                base.with_suffix(".jsx"),
                base.with_suffix(".js"),
                base / "index.tsx",
                base / "index.ts",
                base / "index.jsx",
                base / "index.js",
            ]
        )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate.resolve()
    return None


def collect_assertion_source_texts(page_path: Path, app_root: Path | None = None) -> list[tuple[Path, str]]:
    queue: list[tuple[Path, int]] = [(page_path.resolve(), 0)]
    visited: set[Path] = set()
    collected: list[tuple[Path, str]] = []

    while queue and len(collected) < 6:
        current_path, depth = queue.pop(0)
        if current_path in visited or not current_path.exists() or not current_path.is_file():
            continue
        visited.add(current_path)
        try:
            text = current_path.read_text(encoding="utf-8")
        except OSError:
            continue

        collected.append((current_path, text))
        if depth >= 1:
            continue

        for import_match in IMPORT_SOURCE_RE.finditer(text):
            resolved = resolve_import_path(import_match.group(1), current_path, app_root)
            if resolved and resolved not in visited:
                queue.append((resolved, depth + 1))

    return collected


def is_stable_selector_token(token: str) -> bool:
    normalized = slugify(token)
    if not normalized:
        return False
    if normalized in GENERIC_SELECTOR_TOKENS:
        return False
    if normalized.startswith(("text-", "bg-", "border-", "mt-", "mb-", "ml-", "mr-", "px-", "py-")):
        return False
    return len(normalized) >= 6 and ("-" in normalized or "_" in normalized or len(normalized) >= 12)


def dedupe_assertions(assertions: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in assertions:
        assertion_type = str(item.get("type", "")).strip()
        if assertion_type == "selector":
            value = str(item.get("selector", "")).strip()
        else:
            value = str(item.get("value", "")).strip()
        if not assertion_type or not value:
            continue
        key = (assertion_type, value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def derive_web_assertions(node: dict[str, Any], app_root: Path | None = None) -> list[dict[str, str]]:
    source_refs = node.get("source_refs") if isinstance(node.get("source_refs"), list) else []
    page_path = None
    for ref in source_refs:
        if not isinstance(ref, dict):
            continue
        ref_path = str(ref.get("path", "")).strip()
        if ref_path:
            candidate = Path(ref_path).resolve()
            if candidate.exists():
                page_path = candidate
                break

    assertions: list[dict[str, str]] = []
    if page_path:
        for _, text in collect_assertion_source_texts(page_path, app_root):
            for match in HTML_ID_RE.finditer(text):
                element_id = match.group(1).strip()
                if is_stable_selector_token(element_id):
                    assertions.append({"type": "selector", "selector": f"#{element_id}"})

            for match in FORM_CLASS_RE.finditer(text):
                for token in match.group(1).split():
                    if is_stable_selector_token(token):
                        assertions.append({"type": "selector", "selector": f"form.{token}"})
                        break

            for match in HEADING_LITERAL_RE.finditer(text):
                heading = match.group(1).strip()
                if heading and len(heading) <= 40 and re.search(r"[\u4e00-\u9fffA-Za-z]", heading):
                    assertions.append({"type": "text", "value": heading})

    assertions = dedupe_assertions(assertions)
    if assertions:
        return assertions[:2]

    title = str(node.get("title", "")).strip()
    return [{"type": "text", "value": title}] if title else []


def infer_redirect_target(page_text: str) -> str:
    match = re.search(r"redirect\(\s*['\"]([^'\"]+)['\"]\s*\)", page_text)
    return match.group(1).strip() if match else ""


def infer_route_mode(page_text: str) -> str:
    redirect_target = infer_redirect_target(page_text)
    if redirect_target and "return (" not in page_text and "return<" not in page_text.replace(" ", ""):
        return "redirect"
    return "screen"


def default_batch_capture(route: str, route_mode: str) -> tuple[bool, str]:
    if route_mode == "redirect":
        return False, "redirect-only"
    if not route or route == "login":
        return False, "entry-auth-page"
    if "[" in route and "]" in route:
        return False, "dynamic-route"
    return True, ""


def build_route_files(repo_root: Path, app_dir: Path, app_kind: str) -> list[RouteFile]:
    app_root = repo_root / app_dir
    pages = sorted((app_root / "app").rglob("page.tsx"))
    route_files: list[RouteFile] = []
    for page_path in pages:
        route = derive_route_from_page(page_path, app_root)
        route_files.append(
            RouteFile(
                route=route,
                page_path=page_path,
                relative_page_path=relative_posix(page_path, repo_root),
                node_id=route_to_node_id(route, app_kind),
                route_key=route_to_route_key(route, app_kind),
                group=route_group(route),
            )
        )
    return sorted(route_files, key=lambda item: route_sort_key(item.route))


def collect_nav_title_index(app_root: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    nav_files = [
        app_root / "components/dashboard/nav-config.ts",
        app_root / "components/dashboard/dashboard-top-tabs.tsx",
        app_root / "components/dashboard/dashboard-commerce-tabs.tsx",
        app_root / "components/dashboard/dashboard-settings-tabs.tsx",
    ]
    for file_path in nav_files:
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        for match in ITEM_BLOCK_RE.finditer(text):
            route = match.group("href").strip().lstrip("/")
            label = match.group("label").strip()
            current = mapping.get(route, "")
            if not current or len(label) > len(current):
                mapping[route] = label
    return mapping


def collect_static_route_refs(text: str, trigger_prefix: str) -> list[RouteRef]:
    refs: list[RouteRef] = []
    seen: set[tuple[str, int, str]] = set()

    for match in re.finditer(r"redirect\(\s*['\"]([^'\"]+)['\"]\s*\)", text):
        route = match.group(1).strip()
        key = (route, match.start(), "redirect")
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            RouteRef(
                route=route,
                line=line_number_for(text, match.group(0)),
                trigger=f"{trigger_prefix}:redirect",
                kind="redirect",
                label="代码重定向",
            )
        )

    for match in re.finditer(r"router\.(push|replace)\(\s*['\"]([^'\"]+)['\"]\s*\)", text):
        route = match.group(2).strip()
        action = match.group(1)
        key = (route, match.start(), action)
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            RouteRef(
                route=route,
                line=line_number_for(text, match.group(0)),
                trigger=f"{trigger_prefix}:router.{action}",
                kind="navigateTo",
                label="路由跳转",
            )
        )

    for match in re.finditer(r"href=\s*['\"]([^'\"]+)['\"]", text):
        route = match.group(1).strip()
        key = (route, match.start(), "href")
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            RouteRef(
                route=route,
                line=line_number_for(text, match.group(0)),
                trigger=f"{trigger_prefix}:href",
                kind="navigateTo",
                label="链接入口",
            )
        )

    for match in re.finditer(r"router\.(push|replace)\(\s*`([^`]+)`\s*\)", text):
        route = match.group(2).strip()
        action = match.group(1)
        key = (route, match.start(), f"template-{action}")
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            RouteRef(
                route=route,
                line=line_number_for(text, match.group(0)),
                trigger=f"{trigger_prefix}:router.{action}.template",
                kind="navigateTo",
                label="模板跳转",
            )
        )

    for match in re.finditer(r"href=\s*\{`([^`]+)`\}", text):
        route = match.group(1).strip()
        key = (route, match.start(), "template-href")
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            RouteRef(
                route=route,
                line=line_number_for(text, match.group(0)),
                trigger=f"{trigger_prefix}:href.template",
                kind="navigateTo",
                label="模板链接",
            )
        )

    for match in re.finditer(r"href:\s*['\"]([^'\"]+)['\"]", text):
        route = match.group(1).strip()
        key = (route, match.start(), "object-href")
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            RouteRef(
                route=route,
                line=line_number_for(text, match.group(0)),
                trigger=f"{trigger_prefix}:config",
                kind="navigateTo",
                label="导航配置",
            )
        )

    return refs


def resolve_route_node(route: str, route_index: dict[str, RouteFile]) -> RouteFile | None:
    normalized = route_match_key(route)
    if normalized in route_index:
        return route_index[normalized]
    if normalized.startswith("/"):
        return route_index.get(normalized.lstrip("/"))
    return None


def add_edge(
    edges: list[dict[str, Any]],
    seen: set[tuple[str, str, str, str]],
    source_node: RouteFile,
    target_node: RouteFile,
    ref: RouteRef,
    source_path: Path,
) -> None:
    if source_node.node_id == target_node.node_id and ref.kind == "navigateTo":
        return
    dedupe_key = (source_node.node_id, target_node.node_id, ref.kind, ref.trigger)
    if dedupe_key in seen:
        return
    seen.add(dedupe_key)
    edges.append(
        {
            "edge_id": f"{source_node.node_id}-{target_node.node_id}-{slugify(ref.trigger)}",
            "from": source_node.node_id,
            "to": target_node.node_id,
            "trigger": ref.trigger,
            "kind": ref.kind,
            "source_refs": [{"path": str(source_path.resolve()), "line": ref.line}],
            "label": ref.label,
        }
    )


def build_nextjs_node(
    route_file: RouteFile,
    *,
    locale_index: dict[str, str],
    nav_title_index: dict[str, str],
    app_kind: str,
) -> dict[str, Any]:
    page_text = route_file.page_path.read_text(encoding="utf-8")
    title, title_line = derive_route_title(route_file.route, page_text, locale_index, nav_title_index)
    route_alias = route_file.route or "root"
    route_mode = infer_route_mode(page_text)
    redirect_target = infer_redirect_target(page_text)
    batch_capture_enabled, batch_capture_reason = default_batch_capture(route_file.route, route_mode)
    return {
        "node_id": route_file.node_id,
        "route_key": route_file.route_key,
        "title": title,
        "route": route_file.route,
        "aliases": sorted(
            {
                route_alias,
                route_to_path(route_file.route),
                route_file.node_id,
                slugify(title),
                slugify(route_file.route.replace("/", "-")) if route_file.route else "root",
            }
        ),
        "package": "main",
        "group": route_file.group,
        "status": "registered",
        "screen_component": route_file.relative_page_path,
        "page_file": route_file.relative_page_path,
        "config_file": "",
        "regions": derive_regions(title, page_text),
        "screenshot_refs": [planned_screenshot_ref(route_file.node_id)],
        "source_refs": [{"path": str(route_file.page_path.resolve()), "line": title_line}],
        "board_meta": {
            "note": "",
            "tags": [app_kind, route_file.group],
            "route_mode": route_mode,
            "redirect_target": redirect_target,
            "requires_parameters": bool("[" in route_file.route and "]" in route_file.route),
            "batch_capture_default": batch_capture_enabled,
            "batch_capture_skip_reason": batch_capture_reason,
        },
    }


def build_nextjs_nodes(
    route_files: list[RouteFile],
    *,
    locale_index: dict[str, str],
    nav_title_index: dict[str, str],
    app_kind: str,
) -> list[dict[str, Any]]:
    return [
        build_nextjs_node(
            route_file,
            locale_index=locale_index,
            nav_title_index=nav_title_index,
            app_kind=app_kind,
        )
        for route_file in route_files
    ]


def collect_nextjs_page_edges(
    route_files: list[RouteFile],
    *,
    route_index: dict[str, RouteFile],
) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str, str]] = set()
    for route_file in route_files:
        page_text = route_file.page_path.read_text(encoding="utf-8")
        refs = collect_static_route_refs(page_text, route_file.relative_page_path)
        for ref in refs:
            target_node = resolve_route_node(ref.route, route_index)
            if not target_node:
                continue
            add_edge(edges, seen_edges, route_file, target_node, ref, route_file.page_path)
    return edges


def collect_nextjs_nav_edges(
    repo_root: Path,
    app_root: Path,
    *,
    route_index: dict[str, RouteFile],
    edges: list[dict[str, Any]],
) -> None:
    seen = {
        (
            str(item.get("from") or ""),
            str(item.get("to") or ""),
            str(item.get("kind") or ""),
            str(item.get("trigger") or ""),
        )
        for item in edges
    }
    for source_route, relative_path, trigger in NEXTJS_NAV_EDGE_SOURCES:
        source_node = resolve_route_node(source_route, route_index)
        file_path = app_root / relative_path
        if not source_node or not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        refs = collect_static_route_refs(text, file_path.relative_to(repo_root).as_posix())
        for ref in refs:
            target_node = resolve_route_node(ref.route, route_index)
            if not target_node:
                continue
            nav_ref = RouteRef(
                route=ref.route,
                line=ref.line,
                trigger=f"{trigger}:{ref.trigger.split(':')[-1]}",
                kind="navigateTo",
                label="导航入口",
            )
            add_edge(edges, seen, source_node, target_node, nav_ref, file_path)


def collect_nextjs_middleware_edges(
    app_root: Path,
    route_files: list[RouteFile],
    *,
    route_index: dict[str, RouteFile],
    edges: list[dict[str, Any]],
) -> None:
    middleware_path = app_root / "middleware.ts"
    login_node = resolve_route_node("login", route_index)
    if not middleware_path.exists() or not login_node:
        return
    middleware_text = middleware_path.read_text(encoding="utf-8")
    line = line_number_for(middleware_text, "redirect(loginUrl)")
    seen = {
        (
            str(item.get("from") or ""),
            str(item.get("to") or ""),
            str(item.get("kind") or ""),
            str(item.get("trigger") or ""),
        )
        for item in edges
    }
    for route_file in route_files:
        if not route_file.route.startswith("dashboard"):
            continue
        add_edge(
            edges,
            seen,
            route_file,
            login_node,
            RouteRef(
                route="/login",
                line=line,
                trigger="middleware:missing-session",
                kind="redirect",
                label="未登录跳转登录页",
            ),
            middleware_path,
        )


def build_nextjs_manifest_payload(
    repo_root: Path,
    app_dir_path: Path,
    app_root: Path,
    *,
    app_kind: str,
    app_name: str | None,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "generated_at": repo_now_iso(),
        "project": {
            "name": app_name or app_root.name,
            "repo_root": str(repo_root),
            "app_kind": app_kind,
        },
        "sources": {
            "extractor": "nextjs-route-first",
            "app_dir": app_dir_path.as_posix(),
            "app_root": str(app_root),
        },
        "summary": {},
        "nodes": sorted(nodes, key=lambda item: route_sort_key(str(item.get("route", "")))),
        "edges": edges,
        "conflicts": [],
    }


def extract_nextjs_manifest(
    repo_root: Path,
    app_dir: str = "apps/admin",
    *,
    app_kind: str = "web-admin",
    app_name: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    app_dir_path = Path(app_dir)
    app_root = (repo_root / app_dir_path).resolve()
    locale_index = parse_locale_title_index(app_root / "lib/locales")
    nav_title_index = collect_nav_title_index(app_root)
    route_files = build_route_files(repo_root, app_dir_path, app_kind)
    route_index = {route_match_key(item.route): item for item in route_files}
    nodes = build_nextjs_nodes(
        route_files,
        locale_index=locale_index,
        nav_title_index=nav_title_index,
        app_kind=app_kind,
    )
    edges = collect_nextjs_page_edges(route_files, route_index=route_index)
    collect_nextjs_nav_edges(repo_root, app_root, route_index=route_index, edges=edges)
    collect_nextjs_middleware_edges(app_root, route_files, route_index=route_index, edges=edges)
    manifest = build_nextjs_manifest_payload(
        repo_root,
        app_dir_path,
        app_root,
        app_kind=app_kind,
        app_name=app_name,
        nodes=nodes,
        edges=edges,
    )
    return refresh_manifest_summary(manifest)


def scenario_filename(scenario_id: str) -> str:
    return f"{scenario_id}.json"


def build_scenario_payload(
    node: dict[str, Any],
    *,
    app_root: Path | None,
    base_url: str,
    auth_surface: str,
    auth_profile: str,
    browser_channel: str,
    viewport_size: str,
    full_page: bool,
    entry_node_id: str,
    scenario_prefix: str,
) -> dict[str, Any]:
    node_id = str(node["node_id"])
    route = str(node.get("route", ""))
    board_meta = node.get("board_meta") if isinstance(node.get("board_meta"), dict) else {}
    scenario_id = f"{scenario_prefix}-{slugify(node_id)}" if scenario_prefix else slugify(node_id)
    url_target = route_to_path(route)
    dynamic_segments = re.findall(r"\[([^\]]+)\]", url_target)
    for segment in dynamic_segments:
        url_target = url_target.replace(f"[{segment}]", f"__AUTO_{segment.upper()}__")

    notes: list[str] = []
    if dynamic_segments:
        notes.append(f"执行前需要把 {', '.join(dynamic_segments)} 占位符替换成真实值。")
    if route.startswith("dashboard") and auth_profile:
        notes.append("默认复用持久化登录态直接打开目标页。")
    if str(board_meta.get("route_mode", "")).strip() == "redirect":
        redirect_target = str(board_meta.get("redirect_target", "")).strip()
        if redirect_target:
            notes.append(f"当前节点是跳转页，打开后会落到 {redirect_target}。")
    if board_meta.get("batch_capture_default") is False:
        reason = str(board_meta.get("batch_capture_skip_reason", "")).strip()
        if reason:
            notes.append(f"默认批量回放会跳过该场景：{reason}。")

    payload: dict[str, Any] = {
        "scenario_id": scenario_id,
        "engine": "web-playwright-cli",
        "entry_node_id": entry_node_id,
        "target_node_id": node_id,
        "target": {
            "base_url": base_url,
            "auth_surface": auth_surface,
            "auth_profile": auth_profile,
            "browser_channel": browser_channel,
            "viewport_size": viewport_size,
            "full_page": full_page,
        },
        "context": {
            "notes": " ".join(note for note in notes if note).strip(),
        },
        "steps": [
            {
                "action": "open",
                "target": url_target,
            },
            {
                "action": "wait",
                "ms": 1200,
            },
        ],
        "assertions": [],
        "capture": {
            "mode": "screenshot",
            "output": f"../screenshots/{scenario_id}.png",
        },
    }

    payload["assertions"].extend(derive_web_assertions(node, app_root))
    if dynamic_segments:
        payload["context"]["notes"] = (payload["context"]["notes"] + " 当前生成的是 stub，默认不会自动填参。").strip()
    return payload


def scaffold_manifest_scenarios(
    manifest: dict[str, Any],
    scenario_dir: Path,
    *,
    base_url: str,
    auth_surface: str = "admin",
    auth_profile: str = "",
    browser_channel: str = "chrome",
    viewport_size: str = "1440,1000",
    full_page: bool = True,
    scenario_prefix: str = "",
    write_specs: bool = False,
    force: bool = False,
) -> dict[str, Any]:
    scenario_dir = scenario_dir.resolve()
    scenario_dir.mkdir(parents=True, exist_ok=True)
    app_root_raw = str((manifest.get("sources") or {}).get("app_root", "")).strip()
    app_root = Path(app_root_raw).resolve() if app_root_raw else None
    login_node_id = next((str(node["node_id"]) for node in manifest.get("nodes", []) if str(node.get("route", "")) == "login"), "")
    created: list[dict[str, Any]] = []

    for node in manifest.get("nodes", []):
        route = str(node.get("route", ""))
        if any(route.startswith(segment) for segment in SCENARIO_SKIP_SEGMENTS):
            continue
        entry_node_id = login_node_id if route.startswith("dashboard") and login_node_id else str(node["node_id"])
        payload = build_scenario_payload(
            node,
            app_root=app_root,
            base_url=base_url,
            auth_surface=auth_surface,
            auth_profile=auth_profile,
            browser_channel=browser_channel,
            viewport_size=viewport_size,
            full_page=full_page,
            entry_node_id=entry_node_id,
            scenario_prefix=scenario_prefix,
        )
        scenario_path = scenario_dir / scenario_filename(str(payload["scenario_id"]))
        if force or not scenario_path.exists():
            write_text(scenario_path, json.dumps(payload, ensure_ascii=False, indent=2))
        spec_path = scenario_path.with_suffix(".spec.ts")
        if write_specs and (force or not spec_path.exists()):
            write_playwright_spec(scenario_path, spec_path)
        created.append(
            {
                "scenario_id": payload["scenario_id"],
                "scenario_path": str(scenario_path),
                "spec_path": str(spec_path) if write_specs else "",
                "target_node_id": node["node_id"],
            }
        )

    return {
        "scenario_dir": str(scenario_dir),
        "scenario_count": len(created),
        "scenarios": created,
    }
