---
name: interaction-board
description: Use this skill to build and maintain interaction prototype boards, page inventories, route graphs, screenshot-ready manifests, and draw.io/HTML artifacts for apps under active development. Trigger when the user wants a lightweight prototype canvas, app flow board, page matrix, screenshot board, route drift audit, or versioned UI review surface without depending on Figma first.
---

# Interaction Board

`interaction-board` is the lightweight visual truth layer that sits between product intent, app routes, screenshots, and review.

If the user wants one unified entrypoint that also covers scenario replay, miniapp runner orchestration, and UI review reporting, prefer `product-canvas`.
Keep `interaction-board` focused on board truth and rendering.

Use it when the user wants to:

- map app pages into one board
- build a quick prototype surface before polished UI work
- connect routes, entry points, and user flow on one canvas
- generate screenshot-ready manifests for CI
- detect route drift between code and docs
- keep multiple versions of page snapshots understandable

This skill does not replace `pm`, `product-canvas`, or a full design tool.
It gives the project one compact, machine-readable board contract that can later be rendered into draw.io, HTML, screenshots, or stored history.

## What This Skill Owns

- page inventory extraction from code
- route graph extraction from navigation calls
- draw.io board generation
- HTML board generation
- screenshot placeholder path planning
- route drift / doc drift detection
- manifest contract for later CI and version snapshots
- lightweight board overlay for AI/manual draft cards and extra links

`interaction-board` does not own task truth.
`pm` remains the task/doc source of truth.

## Default Workflow

1. Refresh or create tracked work in `pm` first when the work should be managed.
2. Extract one normalized board manifest from the target app.
3. For Web/Admin, do route inventory first, not manual cards first.
4. Scaffold one scenario stub per node before replay.
5. Generate one editable draw.io board from the manifest.
6. Generate one HTML board for review and artifact hosting.
7. If screenshots exist, attach them by reference instead of embedding binaries.
8. Write findings, conflicts, and artifact paths back to the task system.

## Route-First Rule

When the target has multiple screens, the board must be built in this order:

1. scan routes/pages from code
2. infer primary navigation edges from layout/nav/redirect files
3. write `board.seed.json`
4. scaffold `scenarios/*.json`
5. replay scenarios and collect screenshots
6. rebuild or hydrate the board manifest
7. attach scenario refs and screenshots back into `board.manifest.json`

Do not start from a hand-written partial node list unless the user explicitly wants a draft-only overlay.
Do not assume replay tools will auto-refresh the board manifest for you.

## Current MVP Scope

Current MVP focuses on:

- miniapp page matrix extraction
- Next.js Web/Admin route inventory extraction
- route-first board seed generation
- scenario stub scaffolding per node
- route constants vs registered pages diff
- wrapper page to screen component mapping
- doc route drift detection from one markdown runbook
- draw.io canvas generation
- HTML review board generation
- inventory markdown generation

Out of scope for now:

- embedded canvas editing UI
- screenshot capture itself
- image diff storage
- comment threads inside the board
- database-backed history

## Scripts

- `scripts/interaction_board.py`
  - `extract-miniapp`
  - `extract-nextjs`
  - `attach-screenshots`
  - `attach-scenarios`
  - `scaffold-scenarios`
  - `query-node`
  - `render-drawio`
  - `render-html`
  - `render-inventory`
  - `apply-overlay`
  - `render-scenario-spec`
  - `build-manual-board`
  - `build-miniapp-sample`
  - `build-nextjs-board`

## Recommended Usage

Generate a normalized manifest from a miniapp repo:

```bash
python3 skills/interaction-board/scripts/interaction_board.py extract-miniapp \
  --repo-root /abs/path/to/repo \
  --output out/board.manifest.json
```

Build a complete sample artifact set:

```bash
python3 skills/interaction-board/scripts/interaction_board.py build-miniapp-sample \
  --repo-root /abs/path/to/repo \
  --out-dir docs/interaction-board/sample
```

Generate a route-first manifest from a Next.js Web/Admin app:

```bash
python3 skills/interaction-board/scripts/interaction_board.py extract-nextjs \
  --repo-root /abs/path/to/repo \
  --app-dir apps/admin \
  --output docs/interaction-board/admin-prod/board.seed.json
```

Scaffold per-page scenario contracts before replay:

```bash
python3 skills/interaction-board/scripts/interaction_board.py scaffold-scenarios \
  --manifest docs/interaction-board/admin-prod/board.seed.json \
  --scenario-dir docs/interaction-board/admin-prod/scenarios \
  --base-url https://admin.example.com \
  --auth-surface admin \
  --auth-profile prod-admin \
  --scenario-prefix prod-admin \
  --write-specs
```

Build a full route-first board bundle for Web/Admin:

```bash
python3 skills/interaction-board/scripts/interaction_board.py build-nextjs-board \
  --repo-root /abs/path/to/repo \
  --app-dir apps/admin \
  --base-url https://admin.example.com \
  --auth-surface admin \
  --auth-profile prod-admin \
  --out-dir docs/interaction-board/admin-prod \
  --scenario-prefix prod-admin
```

After replaying scenarios, hydrate the board again so HTML cards can resolve the latest scenario screenshots:

```bash
python3 skills/interaction-board/scripts/interaction_board.py build-manual-board \
  --manifest docs/interaction-board/admin-prod/board.seed.json \
  --out-dir docs/interaction-board/admin-prod \
  --scenario-dir docs/interaction-board/admin-prod/scenarios \
  --replace-existing-scenarios \
  --skip-missing-scenarios
```

If many cards still show no image, check this first before changing the renderer:

- the replay run may have produced `screenshots/<scenario_id>.png`
- but the current `board.manifest.json` may still only contain planned `screenshots/<node_id>.png`
- rebuilding the board re-hydrates `card.primary_image` and `card.images` from scenario capture outputs

Attach existing screenshots to an already generated manifest:

```bash
python3 skills/interaction-board/scripts/interaction_board.py attach-screenshots \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --source compare=/abs/path/to/manual-ui-compare \
  --source smoke=/abs/path/to/miniapp-smoke
```

Apply a lightweight overlay so AI can add draft pages and links without rewriting the extracted manifest:

```bash
python3 skills/interaction-board/scripts/interaction_board.py apply-overlay \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --overlay docs/interaction-board/board.overlay.example.json \
  --output docs/interaction-board/sample/board.merged.json
```

Generate a Playwright spec from a saved scenario contract:

```bash
python3 skills/interaction-board/scripts/interaction_board.py render-scenario-spec \
  --scenario docs/interaction-board/scenario.example.json \
  --output docs/interaction-board/scenarios/products-to-detail.spec.ts
```

Attach scenario bindings into an existing manifest so node cards can expose reusable automation paths:

```bash
python3 skills/interaction-board/scripts/interaction_board.py attach-scenarios \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --scenario-dir docs/interaction-board \
  --output docs/interaction-board/sample/board.with-scenarios.json
```

Query one node so AI can quickly find page code locations and version screenshots:

```bash
python3 skills/interaction-board/scripts/interaction_board.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --query products \
  --limit 1
```

List every node without a keyword:

```bash
python3 skills/interaction-board/scripts/interaction_board.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json
```

If AI only needs lightweight code entry paths plus screenshot paths:

```bash
python3 skills/interaction-board/scripts/interaction_board.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --compact
```

If AI only needs the thinnest lookup payload for code and image files:

```bash
python3 skills/interaction-board/scripts/interaction_board.py query-node \
  --manifest docs/interaction-board/sample/board.manifest.json \
  --paths-only
```

## References

Load only what you need:

- `references/workflow.md`: board lifecycle and role boundary
- `references/data-contract.md`: manifest, node, edge, and conflict fields
- `references/eggturtle-sample.md`: sample expectations for Eggturtle miniapp

## Implementation Notes

- Prefer manifest JSON as machine truth; do not treat draw.io XML as the long-term source of truth.
- Keep screenshot handling path-based. Do not put image binaries into SQLite or JSON in the first version.
- Start file-based. Add SQLite only after version lookup and cross-project indexing become necessary.
- Detect real drift first: registered vs candidate vs doc-only routes.
- For Web/Admin, manifest nodes should come from code scanning first, then overlay/manual cards can extend that truth.
