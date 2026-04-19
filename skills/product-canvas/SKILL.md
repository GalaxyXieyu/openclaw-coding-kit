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

## What This Skill Owns

- product flow canvas workflow
- unified scenario contract for Web and miniapp
- board/report orchestration
- repo-local CSV/Markdown review assets
- miniapp target resolution and scenario replay wrapper

It does not replace `pm`.
If the work is tracked, update task state through `pm`.

## Default Workflow

1. Build or refresh the board truth with:

```bash
python3 skills/product-canvas/scripts/product_canvas.py build-miniapp-sample \
  --repo-root /abs/path/to/repo \
  --out-dir docs/interaction-board/sample
```

2. Store reusable scenario contracts under the board docs area, for example:

- `docs/interaction-board/scenarios/*.json`
- `docs/interaction-board/scenarios/*.spec.ts`

3. For Web scenarios, render or update Playwright specs from the scenario contract:

```bash
python3 skills/product-canvas/scripts/product_canvas.py render-scenario-spec \
  --scenario docs/interaction-board/scenario.example.json \
  --output docs/interaction-board/scenarios/products-to-detail.spec.ts
```

4. For miniapp scenarios, replay the saved contract through `auto-miniprogram`:

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

5. If you only need a target sanity check or fresh screenshot, use:

```bash
node skills/product-canvas/scripts/miniapp_smoke.js \
  --scenario docs/interaction-board/scenarios/products-to-detail.json \
  --target-name main-live-37768 \
  --ide-port 37768 \
  --automator-port 37381 \
  --json-output out/product-canvas/runs/miniapp-smoke.json
```

6. For review planning/reporting, initialize and maintain repo-local CSV assets:

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

## Scripts

- `scripts/product_canvas.py`
  - thin wrapper to the existing board truth/render commands
- `scripts/init_product_canvas_plan.js`
- `scripts/generate_product_canvas_report.js`
- `scripts/resolve_miniapp_target.js`
- `scripts/miniapp_smoke.js`
- `scripts/miniapp_scenario.js`

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
