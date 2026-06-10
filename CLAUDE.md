# CLAUDE.md

本仓库是 PM / lark-cli 工具链仓库。默认中文沟通。

## 当前方向

- 业务项目以后默认绑定真实本地仓库目录，例如 `/Volumes/DATABASE/code/business/Eggturtle-breeding-library`。
- Claude Code 和 Codex 都直接在业务仓库根目录工作，不再默认依赖 OpenClaw workspace / Gateway / Hermes 绑定层。
- PM 的 Feishu 投递走官方 `lark-cli`；不要恢复 `openclaw-lark-bridge` 或 `pm_bridge.py`。
- `pm.json` 只保存非密配置，不保存 app secret、access token、refresh token、tenant secret 或 user token。

## 初始化一个业务仓库时

1. 在业务仓库根目录创建或更新 `pm.json`。
2. 生成 `.pm/` repo-local 缓存和上下文文件。
3. 写入 `AGENTS.md` 作为 Claude Code / Codex / 其他 agent 的共享规则。
4. 可选写入 `CLAUDE.md`，只放 Claude Code 专用补充，不和 `AGENTS.md` 冲突。
5. 如果启用 Feishu backend，先确认 `lark-cli auth status` 可用，再让 PM 读写任务/文档。

## 工作规则

- 两步及以上任务维护计划。
- 修改 PM 行为时同步更新 `skills/pm/SKILL.md`、模板和测试。
- 本地 backend 不得调用 `lark-cli`。
- 不要新增 OpenClaw/Gateway/Hermes 映射层；必须直接使用官方 `lark-cli` 命令风格 helper。
