# AGENTS

- project: `{{project_name}}`
- front agent: `{{front_agent_id}}`
- repo root: `{{repo_root}}`
- task backend: `{{task_backend_type}}`
- pm config: `{{pm_config_path}}`

## First Reads

1. `AGENTS.md`
2. `{{pm_config_path}}`
3. `memory.md`
4. `BOOTSTRAP.md`

## Working Rules

- Treat PM as the tracked-work front door.
- Treat `.planning/*` as roadmap and phase truth.
- Treat `.pm/*.json` as repo-local cache, not business truth.
- Use `{{default_worker}}` as the default coder worker.
- Use `{{reviewer_worker}}` for review-only follow-up when needed.
