# Data Contract

## Manifest Top Level

```json
{
  "schema_version": "1.0",
  "generated_at": "2026-04-14T21:00:00+08:00",
  "project": {},
  "sources": {},
  "summary": {},
  "nodes": [],
  "edges": [],
  "conflicts": []
}
```

## `node`

- `node_id`: stable identifier for the board node
- `route_key`: logical route key from route constants when available
- `title`: page title for humans
- `route`: runtime route without leading slash
- `package`: `main` / `public` / `workspace` / `unknown`
- `group`: business grouping used in HTML/draw.io layout
- `status`: `registered` / `candidate` / `draft`
- `screen_component`: resolved feature screen path when available
- `page_file`: wrapper page file path
- `config_file`: page config path
- `regions`: important sub-areas or placeholders
- `screenshot_refs`: relative paths reserved for later screenshots
- `source_refs`: file anchors proving the node exists
- `board_meta`: optional board-only metadata such as `note`, `tags`, `extends`, `origin`
- `card`: normalized review payload for UI/AI consumption

## `edge`

- `edge_id`: stable identifier
- `from`: source `node_id`
- `to`: target `node_id`
- `trigger`: user-visible or inferred trigger label
- `kind`: `navigateTo` / `switchTab` / `reLaunch` / `redirect` / `prototype`
- `source_refs`: file anchors for the inferred transition
- `label`: optional human label for overlay / manual links

## `conflict`

- `kind`: `route_constant_unregistered` / `doc_only_route`
- `subject`: route or node key
- `severity`: `medium` or `high`
- `summary`: plain-language explanation
- `source_refs`: supporting anchors

## Screenshot Policy

- Store screenshot paths only.
- Recommended layout:
  - `screenshots/<version>/<node_id>.png`
  - or `screenshots/<node_id>.png` for a single-snapshot sample
- If the file does not exist yet, keep the path as a planned reference.
- `screenshot_refs[*]` can additionally carry:
  - `exists`: whether the copied board-local screenshot file exists now
  - `label`: version/source label such as `compare` or `weapp-smoke`
  - `source_path`: original screenshot path outside the board
  - `source_root`: source root used during attachment
  - `matched_by`: how the screenshot was matched (`route-tail`, alias hit, etc.)

## `card`

`card` is the AI-friendly projection of one node. It is intended to avoid forcing models to reconstruct image paths from many raw fields.

```json
{
  "node_id": "products",
  "title": "宠物档案",
  "status": "registered",
  "group": "products",
  "note": "",
  "scenario_refs": [
    {
      "scenario_id": "products-to-detail",
      "script_path": "scenarios/products-to-detail.spec.ts",
      "script_absolute_path": "/abs/path/to/board/scenarios/products-to-detail.spec.ts",
      "scenario_path": "/abs/path/to/board/scenario.example.json",
      "capture_output": "screenshots/scenario/productdetail.png",
      "engine": "miniapp-devtools",
      "target": {
        "target_name": "workspace-default"
      },
      "assertions": [
        {
          "type": "path",
          "value": "subpackages/workspace/pages/product-detail/index"
        }
      ],
      "role": "target"
    }
  ],
  "primary_image": {
    "label": "compare",
    "relative_path": "screenshots/compare/products.png",
    "absolute_path": "/abs/path/to/board/screenshots/compare/products.png",
    "exists": true,
    "source_path": "/abs/path/to/original/products.png"
  },
  "images": []
}
```

`card.scenario_refs[*]` 使用对象而不是字符串，目的是让 AI/自动化层直接拿到可执行脚本和来源文件：

- `scenario_id`: 场景稳定 ID
- `script_path`: 相对当前 scenario 目录或 board 目录的 Playwright 脚本路径
- `script_absolute_path`: Playwright 脚本绝对路径；尚未生成时可为空字符串
- `scenario_path`: 原始 scenario JSON 的绝对路径；手工 overlay 时可为空字符串
- `capture_output`: 该场景约定的截图输出路径
- `engine`: `web-playwright-cli` / `web-playwright-spec` / `miniapp-devtools`
- `target`: 运行目标信息；phase 1 保持轻量对象
- `assertions`: 结构化断言，便于 runner/report 直接复用
- `role`: `entry` / `target` / `manual`

## Overlay Contract

Overlay is a second, lighter board layer for AI/manual planning. It is merged onto the manifest and does not replace code-extracted truth.

```json
{
  "card_patches": [
    {
      "match": "products",
      "note": "主列表后续要接分享草图"
    }
  ],
  "cards": [
    {
      "node_id": "ai-share-flow",
      "title": "分享漏斗草图",
      "group": "products",
      "status": "draft",
      "extends": "products",
      "note": "AI 先画一版"
    }
  ],
  "links": [
    {
      "from": "products",
      "to": "ai-share-flow",
      "kind": "prototype",
      "trigger": "overlay:share-funnel",
      "label": "补一条草图路径"
    }
  ]
}
```
