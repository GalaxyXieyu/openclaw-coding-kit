# Unified Scenario Contract

统一 contract 的目标不是统一底层驱动，而是统一“场景资产”。

## 顶层结构

```json
{
  "scenario_id": "products-to-detail",
  "engine": "miniapp-devtools",
  "entry_node_id": "products",
  "target_node_id": "productdetail",
  "target": {},
  "context": {},
  "steps": [],
  "assertions": [],
  "capture": {}
}
```

## `engine`

允许值：

- `web-playwright-cli`
- `web-playwright-spec`
- `miniapp-devtools`

## `target`

Web 示例：

```json
{
  "base_url": "http://127.0.0.1:3000",
  "storage_state": ".auth/user.json"
}
```

Miniapp 示例：

```json
{
  "project_root": "/abs/path/to/project",
  "target_name": "workspace-default"
}
```

## `steps`

第一版建议只用稳定动作：

- `open`
- `tap`
- `fill`
- `relaunch`
- `navigateTo`
- `switchTab`
- `input`
- `wait`

## `assertions`

第一版建议：

- `path`
- `text`
- `selector`
- `storage`

## `capture`

```json
{
  "mode": "screenshot",
  "output": "screenshots/scenario/productdetail.png"
}
```

## Miniapp Example

```json
{
  "scenario_id": "products-to-detail",
  "engine": "miniapp-devtools",
  "entry_node_id": "products",
  "target_node_id": "productdetail",
  "target": {
    "target_name": "workspace-default"
  },
  "context": {
    "storage": [
      {
        "key": "workspace",
        "value": "{\"id\":\"w1\"}"
      }
    ],
    "notes": "首次进入前需要 workspace 上下文。"
  },
  "steps": [
    {
      "action": "relaunch",
      "target": "/pages/products/index"
    },
    {
      "action": "tap",
      "selector": "[data-testid='product-card']",
      "count": 2,
      "interval_ms": 120
    }
  ],
  "assertions": [
    {
      "type": "path",
      "value": "subpackages/workspace/pages/product-detail/index"
    },
    {
      "type": "text",
      "value": "宠物详情"
    }
  ],
  "capture": {
    "mode": "screenshot",
    "output": "screenshots/scenario/productdetail.png"
  }
}
```

补充约定：

- `capture.output` 建议写相对 `scenario.json` 的路径，例如 `../screenshots/scenario/products-to-detail.png`。
- `tap` 支持 `count` 与 `interval_ms`，可表达双击等真实手势。
