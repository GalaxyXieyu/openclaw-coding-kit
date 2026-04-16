---
name: product-canvas
description: Use this skill to manage product flow boards, reusable UI scenarios, screenshot evidence, and review reports across Web and miniapp projects. Trigger when the user wants one unified product canvas for PRD-to-page flow mapping, interaction boards, screenshot versioning, scenario replay, UI/UX review, or implementation drift detection without depending on Figma first.
---

# Product Canvas

`product-canvas` is the unified entrypoint for product flow mapping, board generation, reusable scenario assets, screenshot evidence, and review reporting.

During the compatibility window:

- `interaction-board` remains the board truth/render layer
- `product-canvas` becomes the orchestration surface the agent should prefer
- old `ui-ux-test` behavior is vendored here as repo-local scripts/templates

Do not default back to agent-browser style exploration for repeatable UI work.
Prefer:

1. save one board manifest
2. save one scenario contract
3. replay through the right runner
4. attach screenshot evidence back to the board/report

## Required Decomposition

When the target is a Web/Admin app or a miniapp with many pages, do not start by manually writing a few cards or replaying one scenario first.

Use this order:

1. extract route inventory from code
2. generate the board seed from that inventory
3. scaffold one scenario contract per reachable node
4. replay scenarios page by page
5. rebuild or hydrate the board manifest after replay
6. attach latest screenshots and scenario refs back to the board UI/report

For repeatable work, treat `route inventory -> board seed -> scenario stubs -> replay -> attach back` as the default contract.
If the board does not yet contain the full node set, stop and generate inventory first.
If screenshots have already been written to disk but cards still show placeholders, assume the manifest was not hydrated yet and rebuild it before debugging the frontend.

## What This Skill Owns

- product flow canvas workflow
- unified scenario contract for Web and miniapp
- board/report orchestration
- repo-local CSV/Markdown review assets
- miniapp target resolution and scenario replay wrapper

It does not replace `pm`.
If the work is tracked, update task state through `pm`.

## Default Workflow

1. Build or refresh the board truth with route-first extraction.

For Next.js Web/Admin apps:

```bash
python3 skills/product-canvas/scripts/product_canvas.py build-nextjs-board \
  --repo-root /abs/path/to/repo \
  --app-dir apps/admin \
  --base-url https://admin.example.com \
  --auth-surface admin \
  --auth-profile prod-admin \
  --out-dir docs/interaction-board/admin-prod \
  --scenario-prefix prod-admin
```

This command should:

- scan all page routes first
- infer edges from redirect/nav files
- generate `board.seed.json`
- scaffold `scenarios/*.json` and `*.spec.ts`
- attach scenario refs back into the final board manifest

2. For miniapp or minimal samples, you can still build directly with:

```bash
python3 skills/product-canvas/scripts/product_canvas.py build-miniapp-sample \
  --repo-root /abs/path/to/repo \
  --out-dir docs/interaction-board/sample
```

3. Store reusable scenario contracts under the board docs area, for example:

- `docs/interaction-board/scenarios/*.json`
- `docs/interaction-board/scenarios/*.spec.ts`

4. If you already have a manifest and only need scenario stubs, scaffold them before replay:

```bash
python3 skills/product-canvas/scripts/product_canvas.py scaffold-scenarios \
  --manifest docs/interaction-board/admin-prod/board.seed.json \
  --scenario-dir docs/interaction-board/admin-prod/scenarios \
  --base-url https://admin.example.com \
  --auth-surface admin \
  --auth-profile prod-admin \
  --scenario-prefix prod-admin \
  --write-specs
```

5. For Web scenarios, render or update Playwright specs from the scenario contract:

```bash
python3 skills/product-canvas/scripts/product_canvas.py render-scenario-spec \
  --scenario docs/interaction-board/scenario.example.json \
  --output docs/interaction-board/scenarios/products-to-detail.spec.ts
```

If AI only needs to locate one page's code anchors and version screenshots, query the board manifest directly:

```bash
python3 skills/product-canvas/scripts/product_canvas.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --query products \
  --limit 1
```

Or list all nodes directly:

```bash
python3 skills/product-canvas/scripts/product_canvas.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json
```

If AI only needs a low-token page map, use compact mode:

```bash
python3 skills/product-canvas/scripts/product_canvas.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --compact
```

If AI only needs code file paths plus version image paths, use:

```bash
python3 skills/product-canvas/scripts/product_canvas.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --paths-only
```

6. For miniapp scenarios, replay the saved contract through `auto-miniprogram`:

```bash
node skills/product-canvas/scripts/miniapp_scenario.js \
  --scenario docs/interaction-board/scenarios/products-to-detail.json \
  --target-name main-live-37768 \
  --ide-port 37768 \
  --automator-port 37381 \
  --json-output out/product-canvas/runs/products-to-detail/result.json
```

Notes:

- If `scenario.target.project_root` is already set, `--path` becomes optional.
- When DevTools is attached to a non-default live target, always pass `--target-name` plus the active IDE / automator ports.

7. If you only need a target sanity check or fresh screenshot, use:

```bash
node skills/product-canvas/scripts/miniapp_smoke.js \
  --scenario docs/interaction-board/scenarios/products-to-detail.json \
  --target-name main-live-37768 \
  --ide-port 37768 \
  --automator-port 37381 \
  --json-output out/product-canvas/runs/miniapp-smoke.json
```

8. For review planning/reporting, initialize and maintain repo-local CSV assets:

```bash
node skills/product-canvas/scripts/init_product_canvas_plan.js \
  --run-id demo-run \
  --out-dir out/product-canvas/runs/demo-run

node skills/product-canvas/scripts/generate_product_canvas_report.js \
  --execution-csv out/product-canvas/runs/demo-run/04_execution_log.csv \
  --bugs-csv out/product-canvas/runs/demo-run/05_bug_list.csv \
  --output out/product-canvas/runs/demo-run/product-canvas-report-demo-run.md \
  --project demo \
  --run-id demo-run
```

9. For Web/Admin CLI-first auth bootstrap, persist a reusable storage state:

```bash
node skills/product-canvas/scripts/web_auth_bootstrap.js \
  --base-url https://eggturtles-admin.sealoshzh.site \
  --auth-surface admin \
  --auth-profile eggturtle-prod-admin \
  --login "$PRODUCT_CANVAS_LOGIN" \
  --password "$PRODUCT_CANVAS_PASSWORD" \
  --json-output out/product-canvas/runs/eggturtle-admin/bootstrap.json
```

10. Replay a Web/Admin screenshot scenario through Playwright CLI:

```bash
node skills/product-canvas/scripts/web_scenario.js \
  --scenario docs/interaction-board/eggturtle-web-prod/scenarios/prod-admin-dashboard.json \
  --json-output out/product-canvas/runs/eggturtle-admin/result.json
```

11. Replay a batch of stable Web/Admin scenarios from one board manifest:

```bash
node skills/product-canvas/scripts/web_scenario_batch.js \
  --manifest docs/interaction-board/admin-prod/board.manifest.json \
  --run-dir out/product-canvas/runs/admin-prod-batch
```

Default behavior:

- only runs `web-playwright-cli` target scenarios
- skips entry nodes such as `/login`
- skips redirect-only nodes
- skips dynamic placeholder routes such as `[tenantId]`

12. After any replay run, rebuild the board so card images read scenario capture outputs instead of stale planned paths:

```bash
python3 skills/product-canvas/scripts/product_canvas.py build-manual-board \
  --manifest docs/interaction-board/admin-prod/board.seed.json \
  --out-dir docs/interaction-board/admin-prod \
  --scenario-dir docs/interaction-board/admin-prod/scenarios \
  --replace-existing-scenarios \
  --skip-missing-scenarios
```

Important:

- `web_scenario.js` and `web_scenario_batch.js` write screenshots and per-run JSON, but they do not rewrite `board.manifest.json`
- if you skip this hydrate step, the HTML board may still point at `screenshots/<node_id>.png` planned placeholders even when `screenshots/<scenario_id>.png` already exists

## Scripts

- `scripts/product_canvas.py`
  - thin wrapper to the existing board truth/render commands
- `scripts/init_product_canvas_plan.js`
- `scripts/generate_product_canvas_report.js`
- `scripts/resolve_miniapp_target.js`
- `scripts/miniapp_smoke.js`
- `scripts/miniapp_scenario.js`
- `scripts/web_cli_support.js`
- `scripts/web_auth_bootstrap.js`
- `scripts/web_scenario.js`
- `scripts/web_scenario_batch.js`

## References

Load only what you need:

- `references/workflow.md`: product-canvas layering and compatibility boundary
- `references/scenario-contract.md`: unified scenario JSON contract and engine split
- `references/reporting.md`: CSV/report workflow and evidence rules

## Rules

- Keep manifest JSON as the source of truth for board state.
- Keep scenario JSON as the source of truth for reusable navigation/review flows.
- Keep screenshots path-based; do not embed binaries into JSON or SQLite in phase 1.
- Prefer file-based assets first. Only add DB indexing after one real validation cycle.
- Do not hand-build a partial board for Web/Admin if route inventory has not been extracted yet.
- Scenario replay is a downstream step, not the discovery step.
