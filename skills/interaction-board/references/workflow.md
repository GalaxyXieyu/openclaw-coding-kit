# Workflow

## Goal

Give an active product one lightweight visual surface that connects:

- current page inventory
- route entry points
- page-to-page navigation
- screenshot placeholders or real screenshots
- code truth vs doc truth conflicts

## Layering

Use three layers and keep them separate:

1. `draw.io`
   - low-friction human editing surface
   - good for initial prototype and quick drag/drop updates
2. `manifest.json`
   - machine-readable truth
   - consumed by CI, HTML board, drift checks, future snapshot indexing
3. `HTML board`
   - review surface
   - easy to publish as CI artifact or static page

Do not collapse all three into one file format.

## MVP Rollout

### Phase A

- one project
- one app surface
- one manifest
- one draw.io board
- one HTML board
- one inventory markdown

### Phase B

- automated screenshot attachment
- task/commit version metadata
- route conflict highlighting in review surface

### Phase C

- SQLite indexing
- cross-version lookup
- multi-project landing board

## Failure Handling

- If screenshot capture is unavailable, still publish manifest + draw.io + HTML board.
- If docs are missing, still publish code-truth inventory and mark doc drift as unavailable.
- If a route constant exists but the page is not registered, publish it as a candidate node rather than hiding it.
