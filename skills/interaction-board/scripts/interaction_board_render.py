from __future__ import annotations

import html
import json
from collections import defaultdict
from typing import Any

from interaction_board_assets import load_board_assets
from interaction_board_core import GROUP_ORDER, PACKAGE_STYLE, STATUS_BADGE, screenshot_status, slugify

def render_inventory_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Interaction Board Inventory",
        "",
        f"- 生成时间：`{manifest['generated_at']}`",
        f"- 项目：`{manifest['project']['name']}`",
        f"- 已注册页面：`{manifest['summary']['registered_count']}`",
        f"- 候选页面：`{manifest['summary']['candidate_count']}`",
        f"- 草稿节点：`{manifest['summary'].get('draft_count', 0)}`",
        f"- 关系边：`{manifest['summary']['edge_count']}`",
        f"- 冲突项：`{manifest['summary']['conflict_count']}`",
        f"- 有截图页面：`{manifest['summary'].get('nodes_with_screenshots', 0)}`",
        f"- 截图快照：`{manifest['summary'].get('attached_screenshot_count', 0)}`",
        f"- 绑定场景节点：`{manifest['summary'].get('nodes_with_scenarios', 0)}`",
        f"- 场景引用：`{manifest['summary'].get('attached_scenario_count', 0)}`",
        "",
        "## 页面矩阵",
        "",
        "| 状态 | 标题 | 路由 | 分组 | 包 | 截图 | 场景 | 组件 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for node in manifest["nodes"]:
        scenario_ids = ", ".join(ref["scenario_id"] for ref in node.get("card", {}).get("scenario_refs", [])) or "n/a"
        lines.append(
            f"| {STATUS_BADGE.get(node['status'], node['status'])} | {node['title']} | `{node['route']}` | {node['group']} | {node['package']} | {screenshot_status(node)} | {scenario_ids} | `{node['screen_component']}` |"
        )

    lines.extend(["", "## 主要关系", "", "| From | To | 类型 | 触发 |", "|---|---|---|---|"])
    title_map = {node["node_id"]: node["title"] for node in manifest["nodes"]}
    for edge in manifest["edges"]:
        lines.append(f"| {title_map.get(edge['from'], edge['from'])} | {title_map.get(edge['to'], edge['to'])} | {edge['kind']} | {edge['trigger']} |")

    lines.extend(["", "## 冲突清单", ""])
    if manifest["conflicts"]:
        for conflict in manifest["conflicts"]:
            lines.append(f"- [{conflict['severity']}] `{conflict['kind']}` {conflict['subject']}：{conflict['summary']}")
    else:
        lines.append("- 当前未发现冲突。")
    lines.append("")
    return "\n".join(lines)


def render_screenshot_gallery(node: dict[str, Any]) -> str:
    items: list[str] = []
    for ref in node.get("screenshot_refs", []):
        label = html.escape(str(ref.get("label", "current")))
        path = html.escape(str(ref.get("path", "")))
        source_path = html.escape(str(ref.get("source_path", "")))
        matched_by = html.escape(str(ref.get("matched_by", "")))
        if ref.get("exists", False):
            title_attr = source_path or path
            meta = f"<p><span>{label}</span><code>{path}</code></p>"
            if matched_by:
                meta = f"{meta}<p class=\"shot-match\">{matched_by}</p>"
            items.append(
                f"""
                <a class="shot-card" href="{path}" target="_blank" rel="noreferrer" title="{title_attr}">
                  <img src="{path}" alt="{html.escape(node['title'])} - {label}" loading="lazy" />
                  {meta}
                </a>
                """
            )
        else:
            items.append(
                f"""
                <div class="shot-card placeholder">
                  <strong>{label}</strong>
                  <code>{path}</code>
                </div>
                """
            )
    return f"<div class=\"shot-grid\">{''.join(items)}</div>"


def render_html_board(manifest: dict[str, Any], title: str | None = None) -> str:
    board_title = title or f"{manifest['project']['name']} Interaction Board"
    payload = json.dumps(manifest, ensure_ascii=False).replace("</", "<\\/")
    group_order_json = json.dumps(GROUP_ORDER, ensure_ascii=False)
    candidate_titles = ", ".join(node["title"] for node in manifest["nodes"] if node["status"] == "candidate") or "无"
    missing_titles = ", ".join(node["title"] for node in manifest["nodes"] if not any(ref.get("exists", False) for ref in node.get("screenshot_refs", []))) or "无"
    conflict_preview = "".join(
        f'<li><strong>{html.escape(item["severity"])}</strong> · <code>{html.escape(item["kind"])}</code> · {html.escape(item["subject"])}</li>'
        for item in manifest["conflicts"][:6]
    )
    if not conflict_preview:
        conflict_preview = "<li>当前没有冲突。</li>"

    template, css, js = load_board_assets()
    return (
        template.replace("__TITLE__", html.escape(board_title))
        .replace("__BOARD_CSS__", css)
        .replace("__BOARD_JS__", js)
        .replace("__REGISTERED__", str(manifest["summary"]["registered_count"]))
        .replace("__CANDIDATE__", str(manifest["summary"]["candidate_count"]))
        .replace("__EDGES__", str(manifest["summary"]["edge_count"]))
        .replace("__CONFLICTS__", str(manifest["summary"]["conflict_count"]))
        .replace("__NODE_SHOTS__", str(manifest["summary"].get("nodes_with_screenshots", 0)))
        .replace("__SHOT_COUNT__", str(manifest["summary"].get("attached_screenshot_count", 0)))
        .replace("__CANDIDATE_TITLES__", html.escape(candidate_titles))
        .replace("__MISSING_TITLES__", html.escape(missing_titles))
        .replace("__CONFLICT_PREVIEW__", conflict_preview)
        .replace("__DATA__", payload)
        .replace("__GROUP_ORDER__", group_order_json)
    )


def xml_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_drawio_board(manifest: dict[str, Any], title: str | None = None) -> str:
    board_title = title or f"{manifest['project']['name']} Miniapp Board"
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for node in manifest["nodes"]:
        groups[node["group"]].append(node)

    cells: list[str] = ['<mxCell id="0" />', '<mxCell id="1" parent="0" />']
    node_ids: dict[str, str] = {}
    x_gap = 300
    y_gap = 110
    group_header_height = 40
    base_x = 40
    base_y = 90
    next_id = 2

    title_id = str(next_id)
    next_id += 1
    cells.append(
        f'<mxCell id="{title_id}" value="{xml_escape(board_title)}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1;fontSize=18;" vertex="1" parent="1"><mxGeometry x="40" y="20" width="560" height="44" as="geometry" /></mxCell>'
    )

    for group_index, group in enumerate(sorted(groups, key=lambda item: GROUP_ORDER.get(item, 99))):
        group_x = base_x + group_index * x_gap
        header_id = str(next_id)
        next_id += 1
        cells.append(
            f'<mxCell id="{header_id}" value="{xml_escape(group)}" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;fontStyle=1;" vertex="1" parent="1"><mxGeometry x="{group_x}" y="{base_y}" width="240" height="{group_header_height}" as="geometry" /></mxCell>'
        )
        for node_index, node in enumerate(groups[group]):
            fill, stroke = PACKAGE_STYLE.get(node["package"], PACKAGE_STYLE["unknown"])
            if node["status"] == "candidate":
                fill, stroke = "#ffe6cc", "#d79b00"
            cell_id = str(next_id)
            next_id += 1
            node_ids[node["node_id"]] = cell_id
            value = f"{node['title']}&#10;{node['route']}"
            cells.append(
                f'<mxCell id="{cell_id}" value="{xml_escape(value)}" style="rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};fontSize=12;" vertex="1" parent="1"><mxGeometry x="{group_x}" y="{base_y + group_header_height + 18 + node_index * y_gap}" width="240" height="82" as="geometry" /></mxCell>'
            )

    for edge in manifest["edges"]:
        source_id = node_ids.get(edge["from"])
        target_id = node_ids.get(edge["to"])
        if not source_id or not target_id:
            continue
        edge_id = str(next_id)
        next_id += 1
        cells.append(
            f'<mxCell id="{edge_id}" value="{xml_escape(edge["kind"])}" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;strokeWidth=2;" edge="1" parent="1" source="{source_id}" target="{target_id}"><mxGeometry relative="1" as="geometry" /></mxCell>'
        )

    return f"""<mxfile host="app.diagrams.net" modified="{xml_escape(manifest['generated_at'])}" agent="interaction-board" version="26.2.15">
  <diagram id="{slugify(board_title)}" name="Interaction Board">
    <mxGraphModel dx="1600" dy="1200" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="1800" pageHeight="1200" math="0" shadow="0">
      <root>{"".join(cells)}</root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""
