<!-- PM_SHARED_CONTRACT:START -->
## Repo / Coder Execution Contract

- PM config: `{{pm_config_path}}`
- repo root: `{{repo_root}}`
- tasklist: `{{tasklist_name}}`
- doc folder: `{{doc_folder_name}}`
- default engineering worker: `{{default_worker}}`
- preferred UI worker: `{{preferred_ui_worker}}`

- `product-canvas` clarifies ambiguous product, UX, and acceptance questions before implementation.
- `pm` remains task truth, context truth, progress write-back, and completion truth.
- `coder` executes implementation after PM intake and routes engineering work to `{{default_worker}}` while preferring `{{preferred_ui_worker}}` for UI or visual exploration.
- `project-review` is the project-level review and quality layer after implementation, not the front-door intake role.
- Any tracked behavior, docs, workflow, or code change should still start from a normalized PM task before execution.
<!-- PM_SHARED_CONTRACT:END -->
