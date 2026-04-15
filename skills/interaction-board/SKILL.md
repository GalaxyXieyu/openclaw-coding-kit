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
3. Generate one editable draw.io board from the manifest.
4. Generate one HTML board for review and artifact hosting.
5. If screenshots exist, attach them by reference instead of embedding binaries.
6. Write findings, conflicts, and artifact paths back to the task system.

## Current MVP Scope

Current MVP focuses on:

- miniapp page matrix extraction
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
  - `attach-screenshots`
  - `attach-scenarios`
  - `render-drawio`
  - `render-html`
  - `render-inventory`
  - `apply-overlay`
  - `render-scenario-spec`
  - `build-miniapp-sample`

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
