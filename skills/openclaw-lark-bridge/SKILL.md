---
name: openclaw-lark-bridge
description: Reuse the running local OpenClaw Gateway's openclaw-lark Feishu tools via POST /tools/invoke for deterministic feishu_* calls.
---

# OpenClaw Lark Bridge

Use this skill when OpenClaw or local Codex needs to reuse the same Feishu/Lark tooling that the OpenClaw Gateway already runs.

This skill does not install another plugin.
It calls the already-loaded `openclaw-lark` tools through the local Gateway HTTP endpoint.

It is a local script/skill, not an MCP server name.
Do not call `resources/list` or try `server=openclaw-lark-bridge`.

## What to use

- Bridge script: `scripts/invoke_openclaw_tool.py`
- Plugin inspection: `openclaw plugins info openclaw-lark`

## Rules

- Prefer direct tool calls over `openclaw agent --message ...` when the action must be deterministic.
- Default to read-only actions first: `list`, `get`, `search`, `tasks`.
- For write actions, state the target tool/action and required identifiers before running.

## How it works

The script resolves:

- config: `./openclaw.json` first, then `~/.openclaw/openclaw.json`
- gateway URL: `OPENCLAW_GATEWAY_URL` or `http://127.0.0.1:<gateway.port>`
- gateway token: `OPENCLAW_GATEWAY_TOKEN`, then `CLAWDBOT_GATEWAY_TOKEN`, then `gateway.auth.token`

Then it sends:

```json
{
  "tool": "feishu_task_tasklist",
  "action": "list",
  "args": {
    "action": "list"
  },
  "sessionKey": "main"
}
```

to `POST /tools/invoke` with `Authorization: Bearer <token>`.

## Instruction snippet

- Use `python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py` to call `feishu_*` tools through `POST /tools/invoke`.
- If a tool needs an `action`, pass `--action <name>` so the bridge can mirror it into `args.action`.
- Do not treat `openclaw-lark-bridge` as an MCP server; invoke the script directly.
- The script prints the full gateway envelope plus extracted `details`, `_meta`, and `_diagnosis` when `result` is missing.

## Quick commands

Inspect the loaded OpenClaw Lark plugin:

```bash
openclaw plugins info openclaw-lark
```

List task lists:

```bash
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py \
  --tool feishu_task_tasklist \
  --action list
```

List unfinished tasks:

```bash
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py \
  --tool feishu_task_task \
  --action list \
  --args '{"completed": false, "page_size": 20}'
```

Get one task:

```bash
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py \
  --tool feishu_task_task \
  --action get \
  --args '{"task_guid": "task-guid-here"}'
```

Mark one task complete:

```bash
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py \
  --tool feishu_task_task \
  --action patch \
  --args '{"task_guid": "task-guid-here", "completed_at": "2026-03-13 10:30:00"}'
```

List Drive files in a folder:

```bash
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py \
  --tool feishu_drive_file \
  --action list \
  --args '{"folder_token": ""}'
```

Pass headers that some OpenClaw policies may use:

```bash
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py \
  --tool feishu_task_task \
  --action list \
  --message-channel feishu \
  --account-id cli-local
```

## Notes

- `sessionKey` is optional; default is `main`.
- If the tool schema already has an `action` field, Gateway merges `action` into the tool args.
- If Gateway returns `ok: false`, treat it as a real tool failure, not a parsing failure.
- If Gateway returns `ok: true` without `result`, inspect `_meta.request_args_has_action` and `_diagnosis.next_steps` in the script output.
- If a Feishu write is blocked, check the Lark auth scopes and the acting user identity inside `openclaw-lark`.
- Task attachments are not the same thing as Drive files:
  - use Task Attachment APIs (`task/v2/attachments`, `task/v2/attachments/:attachment_guid`, `task/v2/attachments/upload`)
  - do not assume `feishu_drive_file download` can fetch a task attachment
- Task attachment downloads should use the temporary `url` returned by the Task Attachment API. That URL is short-lived and must be refreshed from the task attachment API when expired.
