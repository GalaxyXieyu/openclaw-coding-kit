from __future__ import annotations

import copy
import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from PIL import Image, ImageStat
except ImportError:  # pragma: no cover - optional dependency
    Image = None
    ImageStat = None

MINIAPP_PAGE_PATHS_FILE = Path("apps/miniapp/src/runtime/page-paths.ts")
MINIAPP_ROUTES_FILE = Path("apps/miniapp/src/runtime/routes.ts")
MINIAPP_APP_CONFIG_FILE = Path("apps/miniapp/src/app.config.ts")
MINIAPP_RUNBOOK_FILE = Path("docs/miniapp-runbook.md")

GROUP_ORDER = {
    "entry": 0,
    "guiquan": 1,
    "products": 2,
    "footprint": 3,
    "account": 4,
    "public": 5,
    "candidate": 6,
    "other": 7,
}

PACKAGE_STYLE = {
    "main": ("#dae8fc", "#6c8ebf"),
    "public": ("#d5e8d4", "#82b366"),
    "workspace": ("#fff2cc", "#d6b656"),
    "unknown": ("#f5f5f5", "#666666"),
}

STATUS_BADGE = {
    "registered": "已注册",
    "candidate": "候选页",
    "draft": "草稿页",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SCRIPT_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
GENERIC_SOURCE_DIR_NAMES = {"screenshots", "artifacts", "images"}
STOP_ALIAS_TOKENS = {"pages", "page", "subpackages", "workspace", "public", "index", "screen", "src", "features", "detail", "list"}
SOURCE_PRIORITY = {
    "scenario": 220,
    "preview": 170,
    "weapp-fidelity": 165,
    "weapp-smoke": 150,
    "ui-ux-smoke": 145,
    "share-dialog": 142,
    "gq-detail": 140,
    "gq-compose": 138,
    "guiquan": 135,
    "public-smoke": 134,
    "public-smoke2": 133,
    "style-pass2": 128,
    "fix": 122,
    "compare": 110,
    "style-pass3": 92,
    "planned": -999,
}

NODE_SCREENSHOT_ALIASES = {
    "guiquan": ["guiquan-direct-entry", "community", "ledger", "breeding"],
    "guiquancommunitycompose": ["guiquan-compose", "community-compose", "compose-filled", "t166-guiquan-compose-preview"],
    "guiquancommunitydetail": ["guiquan-community-detail", "community-detail", "publish-detail"],
    "guiquansupplydetail": ["guiquan-supply-detail", "supply-detail"],
    "productdetail": ["product-detail"],
    "producteditor": ["product-editor"],
    "quickrecord": ["quick-record"],
    "shareconfig": ["share-config", "share-dialog"],
    "footprint": ["series"],
    "breederdetail": ["breeder-detail", "breeders-detail"],
    "footprintbadges": ["footprint-badges"],
    "seriesmanage": ["series-manage"],
    "accountcertificates": ["account-certificates", "certificate"],
    "accountreferral": ["account-referral", "referral", "invite"],
    "publicshare": ["share", "share-preview", "products-share-preview", "public-share", "tenant-public-feed", "public-feed"],
    "publicsharedetail": ["share-detail", "public-share-detail", "tenant-public-detail", "public-detail"],
}

EGGTURTLE_REGION_HINTS = {
    "workspaceEntry": ["租户恢复", "空间切换", "登录回流"],
    "guiquan": ["社区", "繁育", "账本", "补给入口"],
    "products": ["筛选区", "宠物卡片", "编辑入口", "分享入口"],
    "series": ["陪伴总卡", "勋章柜", "系列成册", "里程碑"],
    "me": ["身份卡", "账号区", "数据区", "邀请区"],
    "publicShare": ["公开列表", "筛选", "转化入口"],
    "publicShareDetail": ["公开详情", "事件区", "回流入口"],
    "productDetail": ["头图", "详情信息", "分享配置入口"],
    "productEditor": ["基础资料", "图片上传", "保存动作"],
    "quickRecord": ["记录表单", "跳转编辑", "提交结果"],
    "shareConfig": ["封面设置", "水印设置", "公开预览"],
    "breederDetail": ["家谱", "繁育事件", "配对历史"],
    "footprintBadges": ["勋章概览", "成长反馈"],
    "seriesManage": ["系列列表", "系列编辑"],
    "accountCertificates": ["证书中心", "证书内容"],
    "accountReferral": ["邀请信息", "奖励说明"],
    "guiquanCompose": ["发帖表单", "发布动作"],
    "guiquanCommunityDetail": ["帖子内容", "评论区", "关联档案"],
    "guiquanSupplyDetail": ["商品信息", "订单动作", "地址摘要"],
    "guiquanMarketplace": ["列表页", "竞拍入口", "卖家信息"],
    "guiquanMarketplaceDetail": ["详情区", "出价区", "联系入口"],
}


@dataclass(frozen=True)
class SourceRef:
    path: str
    line: int

    def as_dict(self) -> dict[str, Any]:
        return {"path": self.path, "line": self.line}


@dataclass(frozen=True)
class ScreenshotSource:
    label: str
    dir_name: str
    root: Path


@dataclass(frozen=True)
class ScreenshotCandidate:
    source_label: str
    source_dir_name: str
    source_root: Path
    path: Path
    stem_slug: str
    aliases: tuple[str, ...]
    route: str
    route_tail: str
    metadata_slug: str


def repo_now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return text or "board"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def normalize_route_tail(route: str) -> str:
    text = route.lstrip("/")
    marker = text.find("pages/")
    return text[marker:] if marker >= 0 else text


def route_slug(route: str) -> str:
    return slugify(normalize_route_tail(route).removesuffix("/index").replace("/", "-"))


def planned_screenshot_ref(node_id: str) -> dict[str, Any]:
    return {"label": "planned", "path": f"screenshots/{node_id}.png", "exists": False}


def expand_slug_variants(value: str) -> set[str]:
    normalized = slugify(value)
    if not normalized:
        return set()
    tokens = [token for token in normalized.split("-") if token]
    variants = {normalized}
    for start in range(len(tokens)):
        for end in range(start + 1, len(tokens) + 1):
            piece = "-".join(tokens[start:end])
            if piece:
                variants.add(piece)
    trimmed = list(tokens)
    while trimmed and (trimmed[-1] in {"preview", "runtime", "current", "light", "dark", "mobile", "desktop", "prod"} or re.fullmatch(r"(?:v\d+|pass\d+|\d{6,})", trimmed[-1])):
        trimmed.pop()
        if trimmed:
            variants.add("-".join(trimmed))
    return {item for item in variants if item and item not in STOP_ALIAS_TOKENS}


def default_source_label(path: Path) -> str:
    label_source = path
    if path.name in GENERIC_SOURCE_DIR_NAMES and path.parent.name:
        label_source = path.parent
    return slugify(label_source.name)


def parse_source_spec(spec: str) -> ScreenshotSource:
    label_part, sep, path_part = spec.partition("=")
    if sep:
        label = label_part.strip() or "snapshot"
        root = Path(path_part.strip()).resolve()
    else:
        root = Path(spec.strip()).resolve()
        label = default_source_label(root)
    return ScreenshotSource(label=label, dir_name=slugify(label), root=root)


def parse_route_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    route = parsed.fragment or parsed.path
    route = route.split("?", 1)[0].lstrip("/")
    return route


def parse_routes_sidecars(root: Path) -> dict[Path, dict[str, Any]]:
    entries: dict[Path, dict[str, Any]] = {}
    for routes_path in root.rglob("routes.json"):
        try:
            payload = json.loads(read_text(routes_path))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, list):
            continue
        for item in payload:
            if not isinstance(item, dict) or not item.get("screenshot"):
                continue
            screenshot_path = Path(str(item["screenshot"]))
            if not screenshot_path.is_absolute():
                screenshot_path = (routes_path.parent / screenshot_path).resolve()
            route = parse_route_from_url(str(item.get("url", "")))
            aliases = set()
            if item.get("slug"):
                aliases.update(expand_slug_variants(str(item["slug"])))
            if route:
                aliases.update(expand_slug_variants(route_slug(route)))
            meta = entries.setdefault(screenshot_path.resolve(), {"route": "", "aliases": set(), "slug": ""})
            if route and not meta["route"]:
                meta["route"] = route
            if item.get("slug") and not meta["slug"]:
                meta["slug"] = str(item["slug"])
            meta["aliases"].update(aliases)
    return entries


def iter_screenshot_candidates(source: ScreenshotSource) -> list[ScreenshotCandidate]:
    sidecars = parse_routes_sidecars(source.root)
    candidates: list[ScreenshotCandidate] = []
    for path in sorted(source.root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue
        resolved = path.resolve()
        sidecar = sidecars.get(resolved, {"route": "", "aliases": set(), "slug": ""})
        aliases = set()
        aliases.update(expand_slug_variants(path.stem))
        relative_stem = str(path.relative_to(source.root).with_suffix("")).replace("/", "-")
        aliases.update(expand_slug_variants(relative_stem))
        aliases.update(sidecar["aliases"])
        route = str(sidecar.get("route", ""))
        if route:
            aliases.update(expand_slug_variants(route_slug(route)))
        candidates.append(
            ScreenshotCandidate(
                source_label=source.label,
                source_dir_name=source.dir_name,
                source_root=source.root,
                path=resolved,
                stem_slug=slugify(path.stem),
                aliases=tuple(sorted(aliases)),
                route=route,
                route_tail=normalize_route_tail(route) if route else "",
                metadata_slug=str(sidecar.get("slug", "")),
            )
        )
    return candidates


def build_node_screenshot_aliases(node: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    for value in [node["node_id"], node["route_key"], *node.get("aliases", [])]:
        aliases.update(expand_slug_variants(str(value)))

    node_route_tail = normalize_route_tail(node["route"]).removesuffix("/index")
    aliases.update(expand_slug_variants(node_route_tail.replace("/", "-")))

    route_suffix = node_route_tail.split("pages/", 1)[-1]
    aliases.update(expand_slug_variants(route_suffix.replace("/", "-")))

    if route_suffix:
        last_segment = route_suffix.split("/")[-1]
        aliases.update(expand_slug_variants(last_segment))

    screen_component = node.get("screen_component", "")
    if screen_component:
        screen_path = Path(screen_component)
        if screen_path.stem != "screen":
            aliases.update(expand_slug_variants(screen_path.stem))
        parent_name = screen_path.parent.name
        if parent_name not in {"src", "features"}:
            aliases.update(expand_slug_variants(parent_name))

    for hint in NODE_SCREENSHOT_ALIASES.get(node["node_id"], []):
        aliases.update(expand_slug_variants(hint))

    return {item for item in aliases if item}


def score_screenshot_candidate(node: dict[str, Any], candidate: ScreenshotCandidate) -> tuple[int, str]:
    node_aliases = build_node_screenshot_aliases(node)
    candidate_aliases = set(candidate.aliases)
    node_route_tail = normalize_route_tail(node["route"])
    score = 0
    reasons: list[str] = []

    if candidate.route_tail and candidate.route_tail == node_route_tail:
        score += 240
        reasons.append("route-tail")
    elif candidate.route and route_slug(candidate.route) == route_slug(node["route"]):
        score += 200
        reasons.append("route-slug")

    overlap = node_aliases & candidate_aliases
    if overlap:
        best_alias = max(overlap, key=lambda item: (len(item), item))
        score += 120 + min(len(best_alias), 40)
        reasons.append(f"alias:{best_alias}")
    else:
        for alias in sorted(node_aliases, key=len, reverse=True):
            if len(alias) < 4:
                continue
            if any(alias in item or item in alias for item in candidate_aliases):
                score += 60 + min(len(alias), 30)
                reasons.append(f"partial:{alias}")
                break

    if node["node_id"] == "publicshare" and "share-preview" in candidate_aliases:
        score += 20
        reasons.append("share-preview")
    if node["node_id"] == "shareconfig" and "share-dialog" in candidate_aliases:
        score += 30
        reasons.append("share-dialog")

    marker_rules = {
        "detail": {"detail"},
        "compose": {"compose"},
        "marketplace": {"marketplace"},
        "supply": {"supply"},
        "addresses": {"address", "addresses"},
        "cart": {"cart"},
        "orders": {"order", "orders"},
        "seller": {"seller"},
        "config": {"config", "dialog"},
        "quick-record": {"quick", "record"},
        "certificates": {"certificate", "certificates"},
        "referral": {"referral", "invite"},
        "badges": {"badge", "badges"},
        "manage": {"manage"},
    }
    if candidate.route_tail != node_route_tail:
        for marker, expected_tokens in marker_rules.items():
            has_expected = any(any(token in alias for token in expected_tokens) for alias in candidate_aliases)
            if marker in node_route_tail and not has_expected:
                score -= 60

    if node["node_id"] == "workspaceentry" and {"home", "dashboard"} & candidate_aliases:
        score -= 120
    if node["node_id"] == "footprint" and "home" in candidate_aliases and "series" not in candidate_aliases:
        score -= 80
    if node["node_id"] not in {"publicshare", "publicsharedetail", "shareconfig"} and "share" in candidate_aliases and score < 200:
        score -= 40

    return score, ", ".join(reasons) if reasons else "unmatched"


def refresh_manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    nodes = manifest.get("nodes", [])
    summary = manifest.setdefault("summary", {})
    summary["registered_count"] = sum(1 for node in nodes if node["status"] == "registered")
    summary["candidate_count"] = sum(1 for node in nodes if node["status"] == "candidate")
    summary["draft_count"] = sum(1 for node in nodes if node["status"] == "draft")
    summary["edge_count"] = len(manifest.get("edges", []))
    summary["conflict_count"] = len(manifest.get("conflicts", []))
    summary["nodes_with_screenshots"] = sum(
        1 for node in nodes if any(ref.get("exists", False) for ref in node.get("screenshot_refs", []))
    )
    summary["attached_screenshot_count"] = sum(
        1
        for node in nodes
        for ref in node.get("screenshot_refs", [])
        if ref.get("exists", False)
    )
    summary["nodes_with_scenarios"] = sum(1 for node in nodes if (node.get("board_meta") or {}).get("scenario_refs"))
    summary["attached_scenario_count"] = sum(len((node.get("board_meta") or {}).get("scenario_refs", [])) for node in nodes)
    return manifest


@lru_cache(maxsize=512)
def inspect_image_signal(path_str: str) -> tuple[float, float] | None:
    if Image is None or ImageStat is None or not path_str:
        return None
    path = Path(path_str)
    if not path.exists() or not path.is_file():
        return None
    try:
        image = Image.open(path).convert("RGB")
        stat = ImageStat.Stat(image)
        mean = float(sum(stat.mean) / 3)
        stddev = float(sum(stat.stddev) / 3)
        return mean, stddev
    except Exception:
        return None


def screenshot_priority(label: str) -> int:
    return SOURCE_PRIORITY.get(slugify(label), 100)


def enrich_card_ref(ref: dict[str, Any], board_root: Path | None = None) -> dict[str, Any]:
    relative_path = str(ref.get("path", ""))
    absolute_path = ""
    if board_root and relative_path:
        absolute_path = str((board_root / relative_path).resolve())
    elif ref.get("absolute_path"):
        absolute_path = str(ref.get("absolute_path", ""))

    exists = bool(ref.get("exists", False))
    signal = inspect_image_signal(absolute_path) if exists and absolute_path else None
    return {
        "label": str(ref.get("label", "planned")),
        "relative_path": relative_path,
        "absolute_path": absolute_path,
        "exists": exists,
        "source_path": str(ref.get("source_path", "")),
        "matched_by": str(ref.get("matched_by", "")),
        "image_mean": signal[0] if signal else None,
        "image_stddev": signal[1] if signal else None,
    }


def resolve_scenario_capture_refs(node: dict[str, Any], board_root: Path | None = None) -> list[dict[str, Any]]:
    if not board_root:
        return []

    refs: list[dict[str, Any]] = []
    for scenario_ref in normalize_scenario_refs((node.get("board_meta") or {}).get("scenario_refs", [])):
        capture_output = str(scenario_ref.get("capture_output", "")).strip()
        scenario_path = str(scenario_ref.get("scenario_path", "")).strip()
        if not capture_output or not scenario_path:
            continue
        absolute_capture = (Path(scenario_path).resolve().parent / capture_output).resolve()
        if not absolute_capture.exists():
            continue
        try:
            relative_capture = absolute_capture.relative_to(board_root.resolve()).as_posix()
        except ValueError:
            continue
        refs.append(
            {
                "label": f"scenario:{scenario_ref.get('scenario_id') or 'capture'}",
                "path": relative_capture,
                "absolute_path": str(absolute_capture),
                "exists": True,
                "source_path": str(absolute_capture),
                "matched_by": f"scenario:{scenario_ref.get('role', 'manual')}",
            }
        )
    return refs


def score_card_ref(ref: dict[str, Any]) -> tuple[int, int, int]:
    if not ref.get("exists", False):
        return (-10_000, -10_000, -10_000)

    priority = screenshot_priority(str(ref.get("label", "")))
    brightness = ref.get("image_mean")
    contrast = ref.get("image_stddev")
    quality = 0
    if isinstance(brightness, (int, float)):
        if brightness < 38:
            quality -= 220
        elif brightness < 60:
            quality -= 110
        elif brightness > 250:
            quality -= 120
        else:
            quality += 30
    if isinstance(contrast, (int, float)):
        if contrast < 16:
            quality -= 140
        elif contrast < 24:
            quality -= 70
        else:
            quality += min(int(contrast), 40)

    absolute_path = str(ref.get("absolute_path", "") or ref.get("source_path", "") or "")
    mtime = 0
    try:
        if absolute_path:
            mtime = int(Path(absolute_path).stat().st_mtime)
    except OSError:
        mtime = 0
    return (priority + quality, mtime, len(str(ref.get("matched_by", ""))))


def build_card_images(node: dict[str, Any], board_root: Path | None = None) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for ref in [*node.get("screenshot_refs", []), *resolve_scenario_capture_refs(node, board_root)]:
        enriched = enrich_card_ref(ref, board_root)
        key = enriched["relative_path"] or enriched["absolute_path"] or enriched["label"]
        current = merged.get(key)
        if current is None or score_card_ref(enriched) > score_card_ref(current):
            merged[key] = enriched

    if not merged:
        return [enrich_card_ref(planned_screenshot_ref(node["node_id"]), board_root)]

    return sorted(merged.values(), key=lambda item: score_card_ref(item), reverse=True)


def primary_screenshot_ref(node: dict[str, Any], board_root: Path | None = None) -> dict[str, Any]:
    images = build_card_images(node, board_root)
    return images[0] if images else enrich_card_ref(planned_screenshot_ref(node["node_id"]), board_root)


def normalize_scenario_refs(raw_refs: list[Any] | None) -> list[dict[str, Any]]:
    if not raw_refs:
        return []

    normalized: list[dict[str, Any]] = []
    for item in raw_refs:
        if isinstance(item, str):
            normalized.append(
                {
                    "scenario_id": Path(item).stem.replace(".spec", ""),
                    "script_path": item,
                    "script_absolute_path": "",
                    "scenario_path": "",
                    "capture_output": "",
                    "engine": "",
                    "target": {},
                    "assertions": [],
                    "role": "manual",
                }
            )
        elif isinstance(item, dict):
            normalized.append(
                {
                    "scenario_id": str(item.get("scenario_id", "")),
                    "script_path": str(item.get("script_path", "")),
                    "script_absolute_path": str(item.get("script_absolute_path", "")),
                    "scenario_path": str(item.get("scenario_path", "")),
                    "capture_output": str(item.get("capture_output", "")),
                    "engine": str(item.get("engine", "")),
                    "target": item.get("target") if isinstance(item.get("target"), dict) else {},
                    "assertions": item.get("assertions") if isinstance(item.get("assertions"), list) else [],
                    "role": str(item.get("role", "manual")),
                }
            )
    return normalized


def hydrate_manifest_cards(manifest: dict[str, Any], board_root: Path | None = None) -> dict[str, Any]:
    for node in manifest.get("nodes", []):
        primary = primary_screenshot_ref(node, board_root)
        images = build_card_images(node, board_root)

        node["card"] = {
            "node_id": node["node_id"],
            "title": node["title"],
            "status": node["status"],
            "group": node["group"],
            "note": str((node.get("board_meta") or {}).get("note", "")),
            "scenario_refs": normalize_scenario_refs((node.get("board_meta") or {}).get("scenario_refs", [])),
            "primary_image": {
                "label": str(primary.get("label", "planned")),
                "relative_path": str(primary.get("relative_path", "")),
                "absolute_path": str(primary.get("absolute_path", "")),
                "exists": bool(primary.get("exists", False)),
                "source_path": str(primary.get("source_path", "")),
                "matched_by": str(primary.get("matched_by", "")),
            },
            "images": images,
        }

    manifest.setdefault("sources", {})["board_root"] = str(board_root.resolve()) if board_root else ""
    return manifest


def overlay_source_ref(overlay_path: str) -> dict[str, Any]:
    return {"path": overlay_path, "line": 1}


def node_matches_reference(node: dict[str, Any], reference: str) -> bool:
    ref = reference.strip()
    if not ref:
        return False
    aliases = {node.get("node_id", ""), node.get("route_key", ""), node.get("route", ""), *node.get("aliases", [])}
    return ref in {item for item in aliases if item}


def resolve_node_reference(nodes: list[dict[str, Any]], reference: str) -> dict[str, Any]:
    for node in nodes:
        if node_matches_reference(node, reference):
            return node
    raise ValueError(f"overlay node reference not found: {reference}")


def normalize_overlay_screenshot_refs(node_id: str, refs: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not refs:
        return [planned_screenshot_ref(node_id)]

    normalized: list[dict[str, Any]] = []
    for index, ref in enumerate(refs, start=1):
        path = str(ref.get("path") or f"screenshots/{node_id}-{index}.png")
        item = {
            "label": str(ref.get("label") or f"overlay-{index}"),
            "path": path,
            "exists": bool(ref.get("exists", False)),
        }
        for key in ("source_path", "matched_by", "source_root"):
            if ref.get(key):
                item[key] = str(ref[key])
        normalized.append(item)
    return normalized or [planned_screenshot_ref(node_id)]


def apply_overlay_patch(node: dict[str, Any], patch: dict[str, Any], source_ref: dict[str, Any]) -> None:
    for key in ("title", "route", "group", "package", "status", "screen_component", "page_file", "config_file"):
        if key in patch:
            node[key] = patch[key]

    if "route_key" in patch:
        node["route_key"] = patch["route_key"]

    if "aliases" in patch:
        node["aliases"] = sorted({*node.get("aliases", []), *(patch.get("aliases") or [])})

    if "regions" in patch:
        node["regions"] = list(patch.get("regions") or [])

    if "screenshot_refs" in patch:
        node["screenshot_refs"] = normalize_overlay_screenshot_refs(node["node_id"], patch.get("screenshot_refs"))

    board_meta = dict(node.get("board_meta") or {})
    if patch.get("note"):
        board_meta["note"] = str(patch["note"])
    if "tags" in patch:
        board_meta["tags"] = list(patch.get("tags") or [])
    if "scenario_refs" in patch:
        board_meta["scenario_refs"] = normalize_scenario_refs(patch.get("scenario_refs") or [])
    if board_meta:
        node["board_meta"] = board_meta

    node["source_refs"] = [*node.get("source_refs", []), source_ref]


def build_overlay_card(
    manifest: dict[str, Any],
    card: dict[str, Any],
    source_ref: dict[str, Any],
) -> dict[str, Any]:
    base: dict[str, Any] = {}
    extends = str(card.get("extends", "")).strip()
    if extends:
        base = copy.deepcopy(resolve_node_reference(manifest["nodes"], extends))

    node_id = slugify(str(card.get("node_id") or card.get("title") or base.get("node_id") or "draft-card"))
    title = str(card.get("title") or base.get("title") or node_id.replace("-", " ").title())
    route = str(card.get("route") or f"overlay/{node_id}")
    aliases = sorted(
        {
            *base.get("aliases", []),
            *(card.get("aliases") or []),
            node_id,
            str(card.get("route_key") or node_id),
        }
    )

    board_meta: dict[str, Any] = {"origin": "overlay-card"}
    if extends:
        board_meta["extends"] = extends
    if card.get("note"):
        board_meta["note"] = str(card["note"])
    if card.get("tags"):
        board_meta["tags"] = list(card["tags"])
    if card.get("scenario_refs"):
        board_meta["scenario_refs"] = normalize_scenario_refs(card["scenario_refs"])

    base_refs = list(base.get("source_refs", [])[:1]) if base else []
    return {
        "node_id": node_id,
        "route_key": str(card.get("route_key") or node_id),
        "title": title,
        "route": route,
        "aliases": aliases,
        "package": str(card.get("package") or (base.get("package") if base else "overlay")),
        "group": str(card.get("group") or (base.get("group") if base else "other")),
        "status": str(card.get("status") or "draft"),
        "screen_component": str(card.get("screen_component") or ""),
        "page_file": str(card.get("page_file") or ""),
        "config_file": str(card.get("config_file") or ""),
        "regions": list(card.get("regions") or base.get("regions") or ["待补区域备注"]),
        "screenshot_refs": normalize_overlay_screenshot_refs(node_id, card.get("screenshot_refs")),
        "source_refs": [*base_refs, source_ref],
        "board_meta": board_meta,
    }


def build_overlay_link(
    manifest: dict[str, Any],
    link: dict[str, Any],
    source_ref: dict[str, Any],
) -> dict[str, Any]:
    from_node = resolve_node_reference(manifest["nodes"], str(link["from"]))
    to_node = resolve_node_reference(manifest["nodes"], str(link["to"]))
    kind = str(link.get("kind") or "prototype")
    trigger = str(link.get("trigger") or "overlay-link")
    edge_id = slugify(str(link.get("edge_id") or f"{from_node['node_id']}-{to_node['node_id']}-{kind}-{trigger}"))
    edge = {
        "edge_id": edge_id,
        "from": from_node["node_id"],
        "to": to_node["node_id"],
        "trigger": trigger,
        "kind": kind,
        "source_refs": [source_ref],
    }
    if link.get("label"):
        edge["label"] = str(link["label"])
    return edge


def apply_board_overlay(
    manifest: dict[str, Any],
    overlay: dict[str, Any],
    overlay_path: str = "board.overlay.json",
) -> dict[str, Any]:
    merged = copy.deepcopy(manifest)
    source_ref = overlay_source_ref(overlay_path)
    seen_ids = {node["node_id"] for node in merged["nodes"]}

    for patch in overlay.get("card_patches", []):
        match = str(patch.get("match") or patch.get("node_id") or "")
        node = resolve_node_reference(merged["nodes"], match)
        apply_overlay_patch(node, patch, source_ref)

    for card in overlay.get("cards", []):
        new_node = build_overlay_card(merged, card, source_ref)
        if new_node["node_id"] in seen_ids:
            raise ValueError(f"overlay card node_id already exists: {new_node['node_id']}")
        merged["nodes"].append(new_node)
        seen_ids.add(new_node["node_id"])

    existing_edges = {(edge["from"], edge["to"], edge["kind"], edge.get("trigger", "")) for edge in merged.get("edges", [])}
    for link in overlay.get("links", []):
        edge = build_overlay_link(merged, link, source_ref)
        key = (edge["from"], edge["to"], edge["kind"], edge.get("trigger", ""))
        if key in existing_edges:
            continue
        merged.setdefault("edges", []).append(edge)
        existing_edges.add(key)

    merged["nodes"].sort(key=lambda item: (GROUP_ORDER.get(item["group"], 99), item["package"], item["route"], item["title"]))
    merged.setdefault("sources", {})["board_overlay"] = overlay_path
    merged["generated_at"] = repo_now_iso()
    return refresh_manifest_summary(merged)


def attach_scenarios(
    manifest: dict[str, Any],
    scenario_bindings: list[dict[str, Any]],
    *,
    replace_existing: bool = False,
) -> dict[str, Any]:
    merged = copy.deepcopy(manifest)
    if replace_existing:
        for node in merged["nodes"]:
            board_meta = dict(node.get("board_meta") or {})
            if "scenario_refs" in board_meta:
                board_meta["scenario_refs"] = []
                node["board_meta"] = board_meta
    for binding in scenario_bindings:
        node = resolve_node_reference(merged["nodes"], str(binding["node_ref"]))
        board_meta = dict(node.get("board_meta") or {})
        refs = normalize_scenario_refs(board_meta.get("scenario_refs") or [])
        candidate = normalize_scenario_refs([binding])[0]
        duplicated = any(ref["scenario_id"] == candidate["scenario_id"] and ref["role"] == candidate["role"] for ref in refs)
        if not duplicated:
            refs.append(candidate)
        board_meta["scenario_refs"] = refs
        node["board_meta"] = board_meta
    merged["generated_at"] = repo_now_iso()
    return refresh_manifest_summary(merged)


def attach_screenshots(manifest: dict[str, Any], source_specs: list[str], board_root: Path) -> dict[str, Any]:
    sources = [parse_source_spec(spec) for spec in source_specs]
    candidates_by_source = {source.dir_name: iter_screenshot_candidates(source) for source in sources}
    refs_by_node: dict[str, list[dict[str, Any]]] = {node["node_id"]: [] for node in manifest["nodes"]}

    for source in sources:
        best_by_node: dict[str, tuple[int, str, ScreenshotCandidate]] = {}
        for candidate in candidates_by_source[source.dir_name]:
            best_node: dict[str, Any] | None = None
            best_score = 0
            best_reason = ""
            for node in manifest["nodes"]:
                score, reason = score_screenshot_candidate(node, candidate)
                node_rank = (score, len(reason), -len(node["node_id"]))
                best_rank = (best_score, len(best_reason), 0)
                if score >= 120 and node_rank > best_rank:
                    best_node = node
                    best_score = score
                    best_reason = reason
            if not best_node:
                continue

            current = best_by_node.get(best_node["node_id"])
            candidate_rank = (best_score, int(candidate.path.stat().st_mtime), -len(candidate.path.name))
            current_rank = (
                current[0],
                int(current[2].path.stat().st_mtime),
                -len(current[2].path.name),
            ) if current else (-1, -1, 0)
            if candidate_rank > current_rank:
                best_by_node[best_node["node_id"]] = (best_score, best_reason, candidate)

        for node in manifest["nodes"]:
            if node["node_id"] not in best_by_node:
                continue
            _, matched_reason, matched_candidate = best_by_node[node["node_id"]]
            target_rel = Path("screenshots") / source.dir_name / f"{node['node_id']}{matched_candidate.path.suffix.lower()}"
            target_abs = board_root / target_rel
            target_abs.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(matched_candidate.path, target_abs)
            refs_by_node[node["node_id"]].append(
                {
                    "label": source.label,
                    "path": target_rel.as_posix(),
                    "exists": True,
                    "source_path": str(matched_candidate.path),
                    "source_root": str(source.root),
                    "matched_by": matched_reason,
                }
            )

    for node in manifest["nodes"]:
        node["screenshot_refs"] = refs_by_node[node["node_id"]] or [planned_screenshot_ref(node["node_id"])]

    manifest["generated_at"] = repo_now_iso()
    manifest.setdefault("sources", {})["screenshot_roots"] = [
        {"label": source.label, "root": str(source.root)} for source in sources
    ]
    return refresh_manifest_summary(manifest)


def screenshot_status(node: dict[str, Any]) -> str:
    attached = [ref["label"] for ref in node.get("screenshot_refs", []) if ref.get("exists", False)]
    return ", ".join(attached) if attached else "planned"


def write_screenshots_readme(screenshots_dir: Path, manifest: dict[str, Any]) -> None:
    summary = manifest.get("summary", {})
    labels = sorted(
        {
            ref["label"]
            for node in manifest.get("nodes", [])
            for ref in node.get("screenshot_refs", [])
            if ref.get("exists", False)
        }
    )
    lines = ["# Screenshots", ""]
    if summary.get("attached_screenshot_count", 0):
        lines.extend(
            [
                f"- 已挂载截图：`{summary['attached_screenshot_count']}`",
                f"- 覆盖页面：`{summary['nodes_with_screenshots']}`",
                f"- 版本标签：`{', '.join(labels)}`" if labels else "- 版本标签：`n/a`",
                "",
                "真实截图以复制后的 board 本地文件为准，原始来源路径记录在 `board.manifest.json` 的 `screenshot_refs[*].source_path`。",
            ]
        )
    else:
        lines.append("当前样板只生成截图位路径，后续可由 miniapp automation / Playwright CI 把真实截图写入本目录。")
    lines.append("")
    write_text(screenshots_dir / "README.md", "\n".join(lines))


def reset_screenshots_dir(screenshots_dir: Path) -> None:
    if screenshots_dir.exists():
        shutil.rmtree(screenshots_dir)
    screenshots_dir.mkdir(parents=True, exist_ok=True)


def parse_page_paths(path: Path) -> dict[str, dict[str, Any]]:
    text = read_text(path)
    result: dict[str, dict[str, Any]] = {}
    for match in re.finditer(r"^\s*([A-Za-z0-9_]+):\s*'([^']+?/index)'", text, flags=re.MULTILINE):
        key = match.group(1)
        route = match.group(2).lstrip("/")
        line = text[: match.start()].count("\n") + 1
        result[key] = {
            "key": key,
            "route": route,
            "source_ref": SourceRef(str(path), line).as_dict(),
        }
    return result


def parse_app_config(path: Path, page_paths: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    text = read_text(path)
    registered: dict[str, dict[str, Any]] = {}

    page_order_match = re.search(r"const\s+pageOrder\s*=\s*\[(.*?)\]", text, flags=re.DOTALL)
    if page_order_match:
        body = page_order_match.group(1)
        body_offset = page_order_match.start(1)
        for match in re.finditer(r"MINIAPP_PAGE_PATHS\.([A-Za-z0-9_]+)", body):
            key = match.group(1)
            if key not in page_paths:
                continue
            line = text[: body_offset + match.start()].count("\n") + 1
            registered[key] = {
                "route": page_paths[key]["route"],
                "package": "main",
                "source_ref": SourceRef(str(path), line).as_dict(),
            }

    for block in re.finditer(r"root:\s*'([^']+)'\s*,\s*pages:\s*\[((?:.|\n)*?)\]", text):
        root = block.group(1)
        body = block.group(2)
        package_name = root.split("/")[-1]
        block_start = block.start(2)
        for page_match in re.finditer(r"'([^']+?/index)'", body):
            relative_page = page_match.group(1)
            route = f"{root}/{relative_page}".lstrip("/")
            line = text[: block_start + page_match.start()].count("\n") + 1
            route_key = next((key for key, item in page_paths.items() if item["route"] == route), route)
            registered[route_key] = {
                "route": route,
                "package": package_name,
                "source_ref": SourceRef(str(path), line).as_dict(),
            }
    return registered


def page_wrapper_for_route(repo_root: Path, route: str) -> tuple[Path, Path]:
    base = repo_root / "apps/miniapp/src" / route
    return base.with_name("index.tsx"), base.with_name("index.config.ts")


def resolve_screen_component(repo_root: Path, export_target: str) -> str:
    target = export_target.strip()
    if target.startswith("@/"):
        candidate = repo_root / "apps/miniapp/src" / target[2:]
        candidates = [
            candidate.with_suffix(".tsx"),
            candidate.with_suffix(".ts"),
            candidate / "index.tsx",
            candidate / "index.ts",
        ]
        for path in candidates:
            if path.exists():
                try:
                    return str(path.relative_to(repo_root))
                except ValueError:
                    return str(path)
    return target


def parse_page_wrapper(repo_root: Path, route: str) -> dict[str, Any]:
    wrapper_path, config_path = page_wrapper_for_route(repo_root, route)
    screen_component = ""
    page_ref = SourceRef(str(wrapper_path), 1).as_dict()
    config_ref = SourceRef(str(config_path), 1).as_dict()
    title = route.split("/")[-2].replace("-", " ").title()

    if wrapper_path.exists():
        text = read_text(wrapper_path)
        match = re.search(r"export\s+\{\s*default\s*\}\s+from\s+(['\"])(.+?)\1", text)
        if match:
            screen_component = resolve_screen_component(repo_root, match.group(2))
            page_ref = SourceRef(str(wrapper_path), text[: match.start()].count("\n") + 1).as_dict()

    if config_path.exists():
        text = read_text(config_path)
        match = re.search(r"navigationBarTitleText:\s*'([^']+)'", text)
        if match:
            title = match.group(1)
            config_ref = SourceRef(str(config_path), text[: match.start()].count("\n") + 1).as_dict()

    return {
        "page_file": str(wrapper_path.relative_to(repo_root)) if wrapper_path.exists() else "",
        "config_file": str(config_path.relative_to(repo_root)) if config_path.exists() else "",
        "screen_component": screen_component,
        "page_ref": page_ref,
        "config_ref": config_ref,
        "title": title,
    }


def infer_group(route_key: str, route: str) -> str:
    if route_key in {"workspaceEntry", "login", "home"} or "workspace-entry" in route or "/login/" in route:
        return "entry"
    if route_key.startswith("guiquan") or "guiquan" in route:
        return "guiquan"
    if route_key.startswith("product") or route_key == "products" or "share-config" in route or "quick-record" in route:
        return "products"
    if route_key in {"series", "footprint"} or "series" in route or "footprint" in route or "breeders" in route:
        return "footprint"
    if route_key.startswith("account") or route_key == "me" or "/me/" in route:
        return "account"
    if "subpackages/public" in route or "/share" in route:
        return "public"
    return "other"


def region_hints(route_key: str) -> list[str]:
    if route_key in EGGTURTLE_REGION_HINTS:
        return list(EGGTURTLE_REGION_HINTS[route_key])
    return ["待补区域备注"]


def parse_doc_routes(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    text = read_text(path)
    result: dict[str, dict[str, Any]] = {}
    for match in re.finditer(r"^\|\s*`?(/[^|`]+?/index)`?\s*\|", text, flags=re.MULTILINE):
        route = match.group(1).strip().lstrip("/")
        result[route] = {
            "route": route,
            "source_ref": SourceRef(str(path), text[: match.start()].count("\n") + 1).as_dict(),
        }
    return result


def parse_route_targets(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    text = read_text(path)
    result: dict[str, str] = {}
    for match in re.finditer(r"'([^']+)':\s*MINIAPP_PAGE_PATHS\.([A-Za-z0-9_]+)", text):
        result[match.group(1)] = match.group(2)
    return result


def rel_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def edge_kind_from_line(line: str) -> str:
    if "switchTab" in line:
        return "switchTab"
    if "reLaunch" in line or "relaunchTo" in line:
        return "reLaunch"
    if "redirectToTarget" in line or "redirectTo" in line:
        return "redirect"
    return "navigateTo"


def infer_edges(
    repo_root: Path,
    nodes: list[dict[str, Any]],
    page_paths: dict[str, dict[str, Any]],
    route_targets: dict[str, str],
) -> list[dict[str, Any]]:
    route_to_node = {node["route"]: node["node_id"] for node in nodes}
    screen_to_node = {node["screen_component"]: node for node in nodes if node.get("screen_component")}
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    def related_source_files(screen_path: Path) -> list[Path]:
        if not screen_path.exists():
            return []

        files: list[Path] = [screen_path]
        parent = screen_path.parent
        if screen_path.name.startswith("screen."):
            for helper in ("controller.ts", "controller.tsx", "model.ts", "model.tsx", "actions.ts", "actions.tsx"):
                helper_path = parent / helper
                if helper_path.exists():
                    files.append(helper_path)
            for folder_name in ("tabs", "sheets", "sheet", "sections"):
                folder = parent / folder_name
                if not folder.exists():
                    continue
                files.extend(
                    path
                    for path in sorted(folder.rglob("*"))
                    if path.is_file() and path.suffix.lower() in SCRIPT_EXTENSIONS
                )
        else:
            controller_path = parent / "controller.ts"
            if controller_path.exists():
                files.append(controller_path)

        deduped: list[Path] = []
        seen_paths: set[Path] = set()
        for path in files:
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            deduped.append(resolved)
        return deduped

    for screen_component, node in screen_to_node.items():
        screen_path = (repo_root / screen_component).resolve()
        source_files = related_source_files(screen_path)
        if not source_files:
            continue

        def push_edge(target_route: str, source_path: Path, line_index: int, kind: str, trigger: str) -> None:
            if target_route not in route_to_node:
                return
            key = (node["node_id"], route_to_node[target_route], kind, trigger)
            if key in seen:
                return
            seen.add(key)
            results.append(
                {
                    "edge_id": slugify(f"{node['node_id']}-{route_to_node[target_route]}-{kind}"),
                    "from": node["node_id"],
                    "to": route_to_node[target_route],
                    "trigger": trigger,
                    "kind": kind,
                    "source_refs": [{"path": rel_path(source_path, repo_root), "line": line_index}],
                }
            )

        for source_path in source_files:
            text = read_text(source_path)
            lines = text.splitlines()
            for idx, line in enumerate(lines, start=1):
                for match in re.finditer(r"MINIAPP_PAGE_PATHS\.([A-Za-z0-9_]+)", line):
                    key = match.group(1)
                    if key in page_paths:
                        push_edge(page_paths[key]["route"], source_path, idx, edge_kind_from_line(line), f"MINIAPP_PAGE_PATHS.{key}")
                for match in re.finditer(r"buildMiniappRoute\(\s*'([^']+)'", line):
                    target_name = match.group(1)
                    route_key = route_targets.get(target_name, target_name)
                    if route_key in page_paths:
                        push_edge(page_paths[route_key]["route"], source_path, idx, edge_kind_from_line(line), f"buildMiniappRoute:{target_name}")
                for match in re.finditer(r"redirectToTarget\(\s*'([^']+)'", line):
                    route_key = match.group(1)
                    if route_key in page_paths:
                        push_edge(page_paths[route_key]["route"], source_path, idx, "redirect", f"redirectToTarget:{route_key}")
    return results


def route_alias_penalty(route_key: str) -> int:
    penalties = {
        "defaultPrivateLanding": 20,
        "home": 15,
        "login": 15,
        "series": 10,
    }
    return penalties.get(route_key, 0)


def choose_canonical_key(route: str, route_keys: list[str], registered_map: dict[str, dict[str, Any]]) -> str:
    registered_keys = [key for key in route_keys if key in registered_map and registered_map[key]["route"] == route]
    pool = registered_keys or route_keys
    return sorted(pool, key=lambda key: (route_alias_penalty(key), len(key), key))[0]


def extract_miniapp_manifest(repo_root: Path) -> dict[str, Any]:
    page_paths_path = repo_root / MINIAPP_PAGE_PATHS_FILE
    routes_path = repo_root / MINIAPP_ROUTES_FILE
    app_config_path = repo_root / MINIAPP_APP_CONFIG_FILE
    runbook_path = repo_root / MINIAPP_RUNBOOK_FILE

    page_paths = parse_page_paths(page_paths_path)
    registered_map = parse_app_config(app_config_path, page_paths)
    doc_routes = parse_doc_routes(runbook_path)
    route_targets = parse_route_targets(routes_path)

    registered_routes = {item["route"] for item in registered_map.values()}
    grouped_routes: dict[str, list[str]] = defaultdict(list)
    for route_key, route_info in page_paths.items():
        grouped_routes[route_info["route"]].append(route_key)
    nodes: list[dict[str, Any]] = []

    for route, route_keys in grouped_routes.items():
        route_key = choose_canonical_key(route, route_keys, registered_map)
        route_info = page_paths[route_key]
        status = "registered" if route in registered_routes else "candidate"
        package_info = next(
            (value for value in registered_map.values() if value["route"] == route),
            {"package": "unknown", "source_ref": route_info["source_ref"]},
        )
        wrapper_info = parse_page_wrapper(repo_root, route)
        node_id = slugify(route_key)
        nodes.append(
            {
                "node_id": node_id,
                "route_key": route_key,
                "title": wrapper_info["title"],
                "route": route,
                "aliases": sorted(route_keys),
                "package": package_info["package"],
                "group": infer_group(route_key, route),
                "status": status,
                "screen_component": wrapper_info["screen_component"],
                "page_file": wrapper_info["page_file"],
                "config_file": wrapper_info["config_file"],
                "regions": region_hints(route_key),
                "screenshot_refs": [planned_screenshot_ref(node_id)],
                "source_refs": [page_paths[key]["source_ref"] for key in route_keys] + [package_info["source_ref"], wrapper_info["page_ref"], wrapper_info["config_ref"]],
            }
        )

    nodes.sort(key=lambda item: (GROUP_ORDER.get(item["group"], 99), item["package"], item["route"]))

    conflicts: list[dict[str, Any]] = []
    for node in nodes:
        if node["status"] == "candidate":
            conflicts.append(
                {
                    "kind": "route_constant_unregistered",
                    "subject": node["route"],
                    "severity": "high",
                    "summary": f"{node['title']} 在路由常量和页面文件中存在，但未注册到 app.config.ts。",
                    "source_refs": node["source_refs"][:2],
                }
            )

    code_routes = {node["route"] for node in nodes}
    for route, info in sorted(doc_routes.items()):
        if route in code_routes:
            continue
        conflicts.append(
            {
                "kind": "doc_only_route",
                "subject": route,
                "severity": "medium",
                "summary": "文档记录了这个 miniapp 路由，但当前代码页面矩阵中没有找到同路径注册。",
                "source_refs": [info["source_ref"]],
            }
        )

    edges = infer_edges(repo_root, nodes, page_paths, route_targets)
    manifest = {
        "schema_version": "1.0",
        "generated_at": repo_now_iso(),
        "project": {
            "name": repo_root.name,
            "repo_root": str(repo_root),
            "app_kind": "miniapp",
        },
        "sources": {
            "app_config": str(app_config_path),
            "page_paths": str(page_paths_path),
            "routes_map": str(routes_path),
            "doc_runbook": str(runbook_path),
        },
        "summary": {},
        "nodes": nodes,
        "edges": edges,
        "conflicts": conflicts,
    }
    return refresh_manifest_summary(manifest)
