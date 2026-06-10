<!-- PM_SHARED_CONTRACT:START -->
## Repo / Coder Execution Contract

- PM config: `{{pm_config_path}}`
- repo root: `{{repo_root}}`
- tasklist: `{{tasklist_name}}`
- doc folder: `{{doc_folder_name}}`
- default engineering worker: `{{default_worker}}`
- preferred UI worker: `{{preferred_ui_worker}}`

- This repository root is the binding point for Claude Code, Codex, PM context, and local project truth.
- Start Claude Code / Codex from `{{repo_root}}` before running PM commands or editing project files.
- Read `pm.json`, `.pm/current-context.json`, `.pm/bootstrap.json`, and `.pm/coder-context.json` before tracked implementation work.
- `pm` remains task truth, context truth, progress write-back, and completion truth.
- Feishu delivery uses the official `lark-cli`; do not route PM Feishu work through OpenClaw/Gateway/Hermes bridge layers.
- Local backend mode must stay offline and must not invoke `lark-cli`.
- Do not store app secret, access token, refresh token, tenant secret, or user token in `pm.json`.
- `product-canvas` clarifies ambiguous product, UX, and acceptance questions before implementation.
- `coder` executes implementation after PM intake and routes engineering work to `{{default_worker}}` while preferring `{{preferred_ui_worker}}` for UI or visual exploration.
- `project-review` is the project-level review and quality layer after implementation, not the front-door intake role.
- Any tracked behavior, docs, workflow, or code change should still start from a normalized PM task before execution.
<!-- PM_SHARED_CONTRACT:END -->
