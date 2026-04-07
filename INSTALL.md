# 安装说明

## 目录

1. AI 主流程
2. 实操前注意点
3. Step 0: 环境检查与缺失安装
4. Step 1: 本地无鉴权验证
5. Step 2: 接入 OpenClaw 实例
6. Step 3: Feishu / bridge / OAuth
7. 配置片段说明
8. 验证矩阵
9. 端到端验收示例
10. AI 安装验收清单
11. 常见问题
12. Bridge 调试路径
13. 运行态目录说明

## AI 唯一主流程

如果这份文档是给 AI 安装代理执行，只推荐按下面这一条主路径，不要自己换顺序：

1. 先检查环境里是否已经有 `python3`、`node`、`openclaw`、`codex`、`cc`、`gsd-tools`。
2. 再检查 OpenClaw 里是否已经装好并加载 `openclaw-lark` Feishu 插件。
3. 如果缺失，就先安装缺失项，不要先改配置。
4. 如果要接 Feishu，先确认用户是否已经准备好：
   - Feishu app
   - `appId`
   - `appSecret`
   - 群聊
   - 需要的 task / attachment 权限
5. 如果用户要飞书群协作，让用户先创建群，再把 `group_id` 配进去。
6. 如果权限还没完成，就先生成授权链接，让用户完成授权。
7. 然后把本仓库里的 skills / plugins 复制到目标 OpenClaw workspace / Codex 目录。
8. 再配置 `openclaw.json`、`pm.json`、`acp/acpx`、`bindings/channels`、`acp-progress-bridge`。
9. 再选一个真实项目做 `pm init`。
10. 最后做端到端测试：
   - 创建任务
   - 派给 Codex
   - 观察 bridge 进度
   - Codex 完成
   - 任务状态/评论/附件/汇报都落回去

这个顺序里最关键的原则：

- 缺依赖先安装，不要先改配置
- `cc` 不是必需前置，但要把“已安装 / 未安装”记录清楚
- 缺权限先授权，不要先做 Feishu 写操作
- skills/plugins 先复制，再 reload OpenClaw
- front agent 先确认，再派发 Codex
- 最后才做端到端任务验收

## 实操前注意点

- AI 先输出环境检查结果，再开始安装，不要边查边改
- 能先走 `local/repo` backend 就先走，Feishu 放到后半段接入
- `front agent` 和 `ACP worker` 是两回事，不要把 `codex` 直接当成 front agent
- `skills/openclaw-lark-bridge` 是 skill 层，`plugins/acp-progress-bridge` 是 plugin 层，不要混放
- 要接 Feishu 时，先确认 `openclaw-lark`、`channels.feishu`、群、OAuth，再做写操作
- 这套链路默认按“环境检查 -> 本地 smoke -> OpenClaw 接入 -> Feishu/bridge/OAuth -> E2E 验收”推进

## Step 0: 环境检查与缺失安装

这一节只做两件事：确认环境里有没有关键命令；缺什么就先补什么。

### 0.1 先检查 CLI 是否存在

最少检查下面 6 个入口：

- `python3`
- `node`
- `openclaw`
- `codex`
- `cc`
- `gsd-tools`

macOS / Linux:

```bash
which python3
which node
which openclaw
which codex
which cc
which gsd-tools
```

Windows CMD / PowerShell:

```powershell
where python3
where node
where openclaw
where codex
where cc
where gsd-tools
```

如果 `cc` 不存在，不阻塞这套仓库安装；但 AI 需要在交付结果里明确写出“未安装 Claude Code，仅验证了 Codex 路径”。

### 0.2 缺失时优先补哪几项

GSD 不是本仓库内置的一部分。当前 `skills/pm/scripts/pm_gsd.py` 会按下面的顺序找它：

1. `GSD_TOOLS_PATH` / `GSD_TOOLS_BIN`
2. PATH 里的 `gsd-tools`
3. `CODEX_HOME/get-shit-done/bin/gsd-tools.cjs`
4. `~/.codex/get-shit-done/bin/gsd-tools.cjs`

如果你要让 `route-gsd`、`plan-phase`、`materialize-gsd-tasks` 正常工作，先安装 GSD。

推荐来源：

- GitHub: `https://github.com/gsd-build/get-shit-done`

推荐安装方式：

```bash
npx get-shit-done-cc@latest --codex --global
```

安装完成后，Codex 全局目录通常会出现：

```text
~/.codex/get-shit-done/
```

验证方法：

```bash
node ~/.codex/get-shit-done/bin/gsd-tools.cjs --help
```

以及在 Codex 会话里验证：

```text
$gsd-help
```

如果不是安装到默认目录，就显式设置：

```bash
export GSD_TOOLS_PATH=/abs/path/to/gsd-tools.cjs
```

OpenClaw Feishu 插件不是本仓库自带代码，而是运行时 npm 插件。当前本机实际使用的是：

```text
@larksuite/openclaw-lark
```

如果要接 Feishu，先安装：

```bash
openclaw plugins install @larksuite/openclaw-lark
```

再验证：

```bash
openclaw plugins info openclaw-lark
openclaw plugins list
```

### 0.3 跨平台路径注意点

这套仓库按“环境变量覆盖 -> PATH -> 平台候选目录”顺序查找运行时入口。

| 目标 | macOS / Linux | Windows CMD / PowerShell |
|-----|------|---------|
| 检查 Python | `which python3` | `where python3` / `Get-Command python3` |
| 检查 OpenClaw CLI | `which openclaw` | `where openclaw` / `Get-Command openclaw` |
| 检查 Codex CLI | `which codex` | `where codex` / `Get-Command codex` |
| 检查 Claude Code CLI | `which cc` | `where cc` / `Get-Command cc` |
| 检查 Node | `which node` | `where node` / `Get-Command node` |

如果命令不在 PATH，可以显式设置：

- `OPENCLAW_BIN`
- `CODEX_BIN`
- `GSD_TOOLS_PATH`
- `OPENCLAW_CONFIG`
- `OPENCLAW_HOME`
- `PM_STATE_DIR`
- `PM_WORKSPACE_ROOT`
- `PM_WORKSPACE_TEMPLATE_ROOT`

Windows 额外提醒：

- `openclaw.json`、`pm.json` 里的路径尽量写成 `C:/...`
- 如果一定要用反斜杠，必须双写成 `C:\\...`
- `where openclaw`、`where codex`、`where node` 的结果要记录进安装报告
- `PM_STATE_DIR` 在 Windows 下通常落到 `%LOCALAPPDATA%\\OpenClawPMCoder\\state`

路径写法建议：

- macOS / Linux: `/abs/path/to/workspace`
- Windows JSON: `C:\\path\\to\\workspace`
- Windows 也可以在很多场景里直接写成 `C:/path/to/workspace`

如果你想先完全脱离 Feishu，最小 `pm.json` 建议显式写：

```json
{
  "task": { "backend": "local", "tasklist_name": "demo", "prefix": "T", "kind": "task" },
  "doc": { "backend": "repo", "folder_name": "demo" }
}
```

也可以在初始化时直接指定：

```bash
python3 skills/pm/scripts/pm.py init --project-name demo --task-backend local --doc-backend repo --dry-run
```

## Step 1: 本地无鉴权验证

这一步只在当前仓库里执行，不要求你已经完成 OpenClaw 或 Feishu 接入。

### 1.1 Python 语法与 CLI 基本检查

```bash
python3 -m py_compile skills/pm/scripts/*.py skills/coder/scripts/*.py skills/openclaw-lark-bridge/scripts/*.py
python3 skills/pm/scripts/pm.py --help
python3 skills/pm/scripts/pm.py context --help
python3 skills/coder/scripts/observe_acp_session.py --help
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py --help
```

这些命令分别验证：

- Python 文件至少通过语法检查
- `pm` 主入口可启动
- `context` 子命令存在
- coder observer 可启动
- repo 内 Feishu bridge script 可启动

AI 在这一步应该记录：

- `python3` 路径
- `node` 路径
- `openclaw` 路径
- `codex` 路径
- 如果某个命令不存在，属于哪一类缺失

### 1.2 先跑 `pm init --dry-run`

本地 bootstrap 的首个官方入口是：

```bash
python3 skills/pm/scripts/pm.py init --project-name demo --dry-run
```

如果项目名包含中文或其他非 ASCII 字符，补上 `--english-name`：

```bash
python3 skills/pm/scripts/pm.py init --project-name "测试项目" --english-name demo --dry-run
```

如果省略了 `--english-name`，当前实现会直接报错：

```text
english name is required when project name contains non-ASCII characters
```

如何理解 dry-run 输出：

- `status: "dry_run"`：说明当前只是预演，不会真正写入外部资源
- `config_preview`：说明将要写入的 PM 配置形状
- `workspace_bootstrap: null`：在没有传 `--group-id` 时这是预期结果，不是失败

AI 在这一步应该额外检查：

- `config_preview.task.backend`
- `config_preview.doc.backend`
- `config_preview.project.name`
- 如果项目名非 ASCII，是否已经显式补了 `--english-name`

### 1.3 刷新上下文并检查 GSD 路由

```bash
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
```

使用方式：

- `context --refresh` 用来刷新 repo 扫描、PM 当前配置、GSD 文档状态
- `route-gsd` 用来确认当前 phase 下一步应该走 `plan-phase`、执行、还是其他动作

AI 在这一步至少要留存这些 evidence：

- `.pm/current-context.json`
- `.pm/bootstrap.json`
- `.pm/doc-index.json`
- `route-gsd` 输出里的 `runtime.ready`

在这个仓库当前状态下，Phase 3 已经完成 planning，所以 `route-gsd` 会把下一步指向执行侧。

命令职责可以这样记：

- `route-gsd`：判断当前 phase 下一步该做什么
- `plan-phase`：产出或刷新 phase plan
- `materialize-gsd-tasks`：把 phase plan 同步成 task backend 里的 tracked tasks

如果你当前只是想在本地把 phase 做完，不需要先跑 `materialize-gsd-tasks`。

### 1.4 PM/GSD product surface 验证

把这三类检查分开理解：

**本地无鉴权：**

```bash
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
```

你应该重点看：

- `route`
- `reason`
- `runtime.ready`
- `runtime.issues`

如果这里已经出现：

- `gsd-tools not found`
- `node not found`

先修运行时，再谈 `plan-phase`。

AI 不应在这里直接尝试“自动安装所有东西”。先判断：

- 缺的是 `node`
- 缺的是 `gsd-tools`
- 还是 `pm.json` / `.planning` 本身不完整

**宿主 runtime：**

```bash
openclaw agents list --bindings
```

这一步是为了确认真正存在的 front agent。只有这一步通过以后，再谈：

```bash
python3 skills/pm/scripts/pm.py plan-phase --repo-root . --phase 5 --no-doc-sync --no-progress-sync --no-state-append
```

这里的边界要记清楚：

- `plan-phase` 不是纯本地无鉴权 smoke
- 它依赖真实 OpenClaw front agent
- `codex` 可以是 ACP worker，但不等于它一定是 front agent

如果你看到 `Unknown agent id`，优先怀疑：

- 传错了 front agent
- `project.agent` 没配置成真实可见 agent
- 你把 ACP worker 和 front agent 混成了一个概念

**真实 backend：**

```bash
python3 skills/pm/scripts/pm.py materialize-gsd-tasks --repo-root . --phase 5
```

这一步是在验证当前 task backend 写入链路：

- 如果 `task.backend = "local"`，结果会写到 `.pm/local-tasks.json`
- 如果 `task.backend = "feishu"`，结果会写到真实 Feishu task backend

在 `local` backend 下，下面这类命令也已经能走通：

```bash
python3 skills/pm/scripts/pm.py upload-attachments --task-id T1 --file ./evidence.txt
python3 skills/pm/scripts/pm.py complete --task-id T1 --content "done locally"
```

AI 如果要证明 repo-local 真的可用，建议把这一组命令作为 smoke evidence：

```bash
python3 skills/pm/scripts/pm.py create --summary "Install smoke task"
python3 skills/pm/scripts/pm.py upload-attachments --task-id T1 --file ./README.md
python3 skills/pm/scripts/pm.py complete --task-id T1 --content "local smoke done"
python3 skills/pm/scripts/pm.py get --task-id T1 --include-completed
```

预期：

- `.pm/local-tasks.json` 出现对应任务
- `attachments` 字段非空
- `comments` 中出现完成说明

## Step 2: 把仓库内容接入 OpenClaw 实例

如果本地无鉴权验证已经通过，再开始接入真实 OpenClaw 实例。

目录映射如下：

```text
本仓库                                    目标 OpenClaw 实例
skills/pm                             ->  skills/pm
skills/coder                          ->  skills/coder
skills/openclaw-lark-bridge          ->  skills/openclaw-lark-bridge
plugins/acp-progress-bridge           ->  plugins/acp-progress-bridge
examples/pm.json.example              ->  仅作参考，不直接覆盖真实配置
examples/openclaw.json5.snippets.md   ->  仅作参考，不直接覆盖真实配置
```

最小接入步骤：

1. 把 `skills/pm` 拷贝到目标实例的 `skills/pm`
2. 把 `skills/coder` 拷贝到目标实例的 `skills/coder`
3. 如果要接 Feishu task/doc，把 `skills/openclaw-lark-bridge` 拷贝到目标实例的 `skills/openclaw-lark-bridge`
4. 如果要自动进度回推，再把 `plugins/acp-progress-bridge` 拷贝到目标实例的 `plugins/acp-progress-bridge`
5. 在目标实例的 `openclaw.json` 启用 `acp`
6. 在 `agents.list[]` 给目标 agent 挂上 `skills: ["pm", "coder"]`
7. 把 `workspace` 改成当前机器上的绝对路径
8. 保存后重启或 reload OpenClaw

推荐复制命令示例：

```bash
mkdir -p "$OPENCLAW_WORKSPACE/skills"
cp -R skills/pm "$OPENCLAW_WORKSPACE/skills/pm"
cp -R skills/coder "$OPENCLAW_WORKSPACE/skills/coder"
cp -R skills/openclaw-lark-bridge "$OPENCLAW_WORKSPACE/skills/openclaw-lark-bridge"
cp -R plugins/acp-progress-bridge "$OPENCLAW_WORKSPACE/plugins/acp-progress-bridge"
```

AI 执行复制后应立即检查：

- 目标目录是否存在
- `SKILL.md` 是否在目标 skill 目录中
- `index.ts` / `core.mjs` 是否在 plugin 目录中

如果你希望这些 skills 在 Codex 里也能全局可见，再额外复制到：

```text
~/.codex/skills/pm
~/.codex/skills/coder
~/.codex/skills/openclaw-lark-bridge
```

这不是最小前置，但对于“直接在 Codex 里也能调 PM / coder / lark-bridge”很有用。

### 2.1 OpenClaw 需要配置哪些项

OpenClaw 至少要配清下面几类内容：

1. `agents.list[]`
2. `acp`
3. 如需 Feishu：`channels.feishu`
4. 如需 Feishu 群会话：`bindings`
5. 如需自动汇报：`plugins.entries.acp-progress-bridge`

最低要求的 agent 形状：

```json
{
  "id": "your-agent-id",
  "name": "your-agent-id",
  "workspace": "REPLACE_WITH_ABSOLUTE_WORKSPACE_PATH",
  "skills": ["pm", "coder"]
}
```

最低要求的 ACP 形状：

```json
{
  "acp": {
    "enabled": true,
    "backend": "acpx",
    "defaultAgent": "codex"
  }
}
```

如果要接 Feishu，再至少补：

```json
{
  "channels": {
    "feishu": {
      "appId": "REPLACE_ME",
      "appSecret": "REPLACE_ME",
      "domain": "feishu"
    }
  }
}
```

如果要接群，还要补 `bindings` 和 `channels.feishu.groups`。现成片段见 [examples/openclaw.json5.snippets.md](/Volumes/DATABASE/code/learn/openclaw-pm-coder-kit/examples/openclaw.json5.snippets.md)。

AI 修改 `openclaw.json` 后，至少要重新检查：

```bash
openclaw agents list --bindings
openclaw plugins list
```

预期：

- 目标 agent 出现在 `agents list --bindings`
- 如启用 `acp-progress-bridge`，插件列表里能看到它
- 如安装 `openclaw-lark`，插件列表里能看到 `openclaw-lark`

### 2.2 PM 需要配置哪些项

PM 配置在 `pm.json`。至少要明确：

1. `repo_root`
2. `project.name`
3. `project.agent`
4. `task.backend`
5. `doc.backend`
6. `coder.backend`
7. `coder.agent_id`

如果你只想先本地跑通，保持：

```json
{
  "task": { "backend": "local" },
  "doc": { "backend": "repo" }
}
```

如果要接 Feishu，至少再补：

- `task.tasklist_guid` 或可解析的 `tasklist_name`
- `doc.folder_token`
- `project.group_id`（如果要飞书群 bootstrap / bindings）

AI 修改 `pm.json` 后，应该至少验证：

```bash
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py next --refresh
```

预期：

- `context --refresh` 不报配置解析错误
- `current-context.json` 里的 backend 字段与配置一致

这里再强调一次：

- front agent 配的是你要直接对话的 agent
- ACP worker 由 `acp.defaultAgent` 或运行时派发逻辑决定
- 两者可以相同，也可以不同

如果 front agent 没有叫 `codex`，但 ACP worker 仍然是 `codex`，这是合法配置。

最小配置片段见：

- [examples/openclaw.json5.snippets.md](./examples/openclaw.json5.snippets.md)
- [examples/pm.json.example](./examples/pm.json.example)

## Step 3: Feishu / bridge / OAuth

这一步只在“本地 smoke + OpenClaw 接入”都通过后再做。

如果用户暂时不接 Feishu，可以直接跳到后面的验收章节，只验证本地 `local/repo` backend。

### 3.1 先让用户创建群，并决定是否需要 `--group-id`

只有当你希望同时预演或执行 workspace bootstrap / Feishu 绑定时，才需要加 `--group-id`。

例如：

```bash
python3 skills/pm/scripts/pm.py init --project-name demo --group-id oc_demo --dry-run
```

这时 dry-run 会出现 `workspace_bootstrap`，并额外暴露：

- `workspace_root`
- `template_root`
- `template_root_exists`

如果 `template_root_exists` 是 `false`，说明当前仓库外部模板资产不存在。此时要么：

- 设置 `PM_WORKSPACE_TEMPLATE_ROOT`
- 要么补齐模板来源

不要把这类失败误判成“最小安装步骤写错了”。

### 3.2 安装 OpenClaw Feishu 插件

当前本机实际使用的是官方 `openclaw-lark` 插件，包名是：

```text
@larksuite/openclaw-lark
```

安装命令：

```bash
openclaw plugins install @larksuite/openclaw-lark
```

如果希望安装记录固定到具体版本，可以再加：

```bash
openclaw plugins install --pin @larksuite/openclaw-lark
```

安装后验证：

```bash
openclaw plugins info openclaw-lark
openclaw plugins list
```

你应该看到至少这些事实：

- `id: openclaw-lark`
- `Status: loaded`
- `Install: npm`
- `Spec: @larksuite/openclaw-lark`
- 存在 `feishu_task_task`、`feishu_task_tasklist`、`feishu_update_doc` 等工具

如果插件加载失败，先跑：

```bash
openclaw plugins doctor
feishu-diagnose
```

官方参考：

- package: `@larksuite/openclaw-lark`
- plugin README: `~/.openclaw/extensions/openclaw-lark/README.md`
- usage guide: `https://bytedance.larkoffice.com/docx/MFK7dDFLFoVlOGxWCv5cTXKmnMh`

AI 如果要进一步确认工具层可用，应继续检查：

```bash
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py \
  --tool feishu_task_tasklist \
  --action list \
  --dry-run
```

预期：

- 能解析出 gateway URL
- 能构造出 `/tools/invoke` 请求
- body 里包含 `tool`、`action`、`args.action`

### 3.3 可选启用 progress bridge

如果你只想先完成本地 PM/GSD/Coder 协作，可以跳过 `acp-progress-bridge`。

只有在你需要：

- 子会话进度自动回推
- 子会话完成结果自动回推
- Feishu 群内持续看到执行状态

时，再去启用对应插件和 Feishu 绑定。

当前 bridge 的默认契约要这样理解：

- 默认子会话：`agent:codex:acp:`
- 默认父会话：`agent:*:feishu:group:` 和 `agent:*:main`
- 默认流程：plugin 定时轮询发现子会话 -> 读取 stream / transcript -> 组装内部 `[[acp_bridge_update]]` -> 回推父会话 -> 由父会话生成用户可见自然语言

也就是说，bridge 发现“Codex 跑完了”不是靠 webhook，而是靠轮询 session store、stream 和 transcript：

- 周期性扫描符合前缀的 child sessions
- 通过 `spawnedBy` 找到对应 parent session
- 看到 progress/done 事件后做节流和 settle
- 再把 update 投递回 parent session

这意味着：

- bridge 本身不是最小安装前置
- 它不是直接“替 PM 报进度”
- 它也不是“所有 provider 默认开箱即用”
- 它当前是 Codex-first，再通过前缀做后续扩展

### 3.4 Feishu 附件授权怎么做

任务附件不是走 `openclaw-lark-bridge`，而是 PM 直接走 Feishu Task Attachment API。

第一次用下面这些命令时：

```bash
python3 skills/pm/scripts/pm.py attachments --task-id T1
python3 skills/pm/scripts/pm.py upload-attachments --task-id T1 --file ./evidence.txt
```

如果还没有有效 OAuth，返回结果里会出现：

- `status = "authorization_required"`
- `verification_uri_complete`
- `user_code`

你也可以手动先拿授权链接：

```bash
python3 skills/pm/scripts/pm.py auth-link \
  --mode user-oauth \
  --scopes task:task:read task:attachment:read task:attachment:write offline_access
```

完成授权后，PM 会把 token 缓存在 state 目录下：

- Linux/macOS: `~/.local/state/openclaw-pm-coder-kit/pm/attachment-oauth-token.json`
- Windows: `%LOCALAPPDATA%\\OpenClawPMCoder\\state\\attachment-oauth-token.json`

如果附件授权失败，优先按这个顺序排查：

1. `openclaw.json` 里是否已有 `channels.feishu.appId` / `appSecret`
2. app 权限页里是否已经开通 `task:task:read`、`task:attachment:read`、`task:attachment:write`
3. 返回的 `verification_uri_complete` 是否已由正确账号完成授权
4. state 目录里是否残留过期的 `attachment-oauth-pending.json`
5. 重新执行 `upload-attachments` 时是否仍然返回 `authorization_required`

常见失败现象与处理：

- `missing channels.feishu.appId/appSecret in openclaw.json`
  处理：先补 `channels.feishu` 配置
- `authorization_required`
  处理：打开返回的 `verification_uri_complete`，完成 OAuth 后重试
- `failed to upload task attachments`
  处理：检查 app 权限、用户身份、文件大小限制、网络与 OpenAPI 返回体
- `failed to verify Feishu OAuth user identity`
  处理：优先怀疑授权账号、app 配置或 token 已失效

AI 不应把附件 OAuth 失败误判为“PM 安装失败”。正确分类是：

- PM 安装成功
- Feishu attachment OAuth 未完成
- 这是外部授权问题，不是 repo 代码问题

## 配置片段说明

### `examples/pm.json.example`

这个文件现在是本地优先的最小示例，只保留 repo 和 coder 的核心字段。

如果后续要接真实 Feishu，再按实际环境补：

- `project.group_id`
- `task.tasklist_guid`
- `doc.folder_token`
- 各类文档 token

### `examples/openclaw.json5.snippets.md`

这个文件已经拆成三类片段：

- 最小 OpenClaw 接入片段
- 可选的 `acp-progress-bridge` 片段
- 可选的 Feishu `bindings/channels` 片段

不要把增强片段整体照抄成“最小配置”。

其中 `acp-progress-bridge` 片段建议按三组参数来理解：

- 作用域：`parentSessionPrefixes`、`childSessionPrefixes`
- 节流：`pollIntervalMs`、`firstProgressDelayMs`、`progressDebounceMs`、`maxProgressUpdatesPerRun`
- 完成策略：`settleAfterDoneMs`、`replayCompletedWithinMs`、`finalAssistantTailChars`、`deliverProgress`、`deliverCompletion`

## 验证矩阵

| 类型 | 目标 | 命令 / 动作 |
|-----|------|-------------|
| 本地无鉴权 smoke | Python 语法 | `python3 -m py_compile skills/pm/scripts/*.py skills/coder/scripts/*.py` |
| 本地无鉴权 smoke | CLI 可启动 | `python3 skills/pm/scripts/pm.py --help` |
| 本地无鉴权 smoke | context 子命令存在 | `python3 skills/pm/scripts/pm.py context --help` |
| 本地无鉴权 smoke | bootstrap dry-run | `python3 skills/pm/scripts/pm.py init --project-name demo --dry-run` |
| 本地无鉴权 smoke | GSD 路由 | `python3 skills/pm/scripts/pm.py route-gsd --repo-root .` |
| 本地无鉴权 smoke | repo 内 lark bridge script 可启动 | `python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py --help` |
| 本地无鉴权 smoke | observer 可启动 | `python3 skills/coder/scripts/observe_acp_session.py --help` |
| 真实集成验证 | OpenClaw Feishu 插件已加载 | `openclaw plugins info openclaw-lark` |
| 真实集成验证 | OpenClaw 实例正常加载 skills | 启动或 reload OpenClaw，确认 agent 可见 `pm` / `coder` |
| 真实集成验证 | progress bridge 生效 | 启用插件后观察 ACP 子会话进度回推 |
| 真实集成验证 | Feishu 绑定生效 | 确认 bindings / channels / group id 配置正确 |
| 真实集成验证 | 附件 OAuth 生效 | `upload-attachments` 不再返回 `authorization_required` |

建议 AI 安装代理真正交付时，至少覆盖矩阵里的前 8 项；如果用户明确要求 Feishu，再继续做后 4 项。

## 端到端验收示例

如果用户要求“安装完就要证明这套能跑”，推荐直接在一个真实 repo 里按下面顺序做一次验收。

### E2E-1：初始化项目

本地模式：

```bash
python3 skills/pm/scripts/pm.py init \
  --project-name demo \
  --task-backend local \
  --doc-backend repo \
  --write-config
```

Feishu 群模式：

```bash
python3 skills/pm/scripts/pm.py init \
  --project-name demo \
  --group-id oc_xxx \
  --task-backend feishu \
  --doc-backend feishu \
  --write-config
```

预期：

- `pm.json` 已生成或更新
- `.pm/current-context.json` 已生成
- 如果 bootstrap task 被创建，返回里会有 `bootstrap_task`

### E2E-2：创建一个真实任务

```bash
python3 skills/pm/scripts/pm.py create \
  --summary "Install E2E smoke task" \
  --request "Verify PM -> coder -> bridge -> completion flow"
```

预期：

- 返回 `task_id`
- `current-context.json` 已刷新
- 如果是 Feishu backend，任务已写入 Feishu tasklist

### E2E-3：派给 Codex

```bash
python3 skills/pm/scripts/pm.py run \
  --task-id T1
```

预期：

- 返回 `backend`
- 返回 `agent_id`
- 返回 `result`
- `.pm/last-run.json` 已生成

如果 `backend = "acp"`，说明它会走 ACP / acpx 子会话；如果 bridge 已启用，就应该继续观察父会话进度。

### E2E-4：观察 bridge

如果启用了 `acp-progress-bridge`，继续检查：

```bash
openclaw agents list --bindings
openclaw plugins info acp-progress-bridge
```

并在父会话里确认：

- 是否出现 progress 更新
- Codex 完成后是否出现 completion 汇报

如果没有自动汇报，再回到文档下方的“Bridge 调试路径”排查。

### E2E-5：完成任务

本地模式可以直接手动完成一次：

```bash
python3 skills/pm/scripts/pm.py complete \
  --task-id T1 \
  --content "E2E smoke done"
```

如果要带附件：

```bash
python3 skills/pm/scripts/pm.py complete \
  --task-id T1 \
  --content "E2E smoke done" \
  --file ./README.md
```

预期：

- 任务状态变成 completed
- 评论里出现 completion 内容
- 如果有附件，上传结果写进返回体

### E2E-6：最终读取结果

```bash
python3 skills/pm/scripts/pm.py get --task-id T1 --include-completed
```

预期：

- `completed_at` 非空
- `comments` 非空
- 如果走本地 backend，`.pm/local-tasks.json` 中也能看到最终状态
- 如果走 Feishu backend，Feishu task 中也能看到最终状态

## AI 安装验收清单

如果安装工作是由 Codex、Claude Code 或其他 AI 代理执行，建议把下面这些结果作为最小交付物：

1. 一组本地无鉴权 smoke 命令的实际执行结果。
2. 当前机器上的 `openclaw`、`codex`、`node` 发现结果。
3. 最终使用的 `workspace` 绝对路径。
4. 目标 OpenClaw 实例里是否已经复制：
   - `skills/pm`
   - `skills/coder`
   - `skills/openclaw-lark-bridge`
   - `plugins/acp-progress-bridge`
5. 如果启用 Feishu：
   - `openclaw-lark` 是否已加载
   - `skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py` 是否存在
   - `bindings/channels` 是否已配置
6. 如果启用附件上传：
   - 是否已经拿到 user OAuth
   - `attachment-oauth-token.json` 是否已生成

AI 代理最终输出里，至少应该明确给出：

- 哪一步已经通过
- 哪一步未通过
- 未通过属于 repo、本机运行时、还是 Feishu 外部依赖

建议 AI 最终交付直接包含下面这类摘要：

```text
Installation Summary
- repo_smoke: pass/fail
- gsd_runtime: pass/fail
- openclaw_runtime: pass/fail
- openclaw_lark: pass/fail
- progress_bridge: pass/fail
- feishu_binding: not_run/pass/fail
- attachment_oauth: not_run/pass/fail

Artifacts
- repo_root:
- openclaw_workspace:
- pm_config:
- openclaw_config:
- state_dir:

Blockers
- ...
```

## 常见问题

- `workspace` 不是绝对路径
- Windows 下 JSON 路径写成了未转义的 `C:\path\to\workspace`
- `skills` 已拷贝，但 agent 没挂 `pm`、`coder`
- 装了插件，但没在 `plugins.entries` 里启用
- `skills/openclaw-lark-bridge` 没复制到 OpenClaw workspace，导致 PM 找不到 repo 内 bridge script
- GSD 没装到 Codex 目录，或 `GSD_TOOLS_PATH` 没配对
- 实际使用的 ACP agent 前缀和 `childSessionPrefixes` 不匹配
- 父会话 key 不匹配 `parentSessionPrefixes`，导致子 run 虽存在但不会被 bridge 接管
- 父会话能看到子 run，但找不到对应 `sessionId`
- progress 其实已抓到，但还在 `firstProgressDelayMs` / `progressDebounceMs` 节流窗口里
- completion 已抓到，但还在 `settleAfterDoneMs` 等待窗口里
- run 太旧才被发现，超过 `replayCompletedWithinMs`，所以 completion 不会补发
- 插件宿主不是标准 OpenClaw CLI 入口，导致回推时找不到 CLI entrypoint
- 中文项目名没传 `--english-name`
- `workspace_bootstrap` 预期出现却是 `null`
原因：你没有传 `--group-id`
- `template_root_exists` 为 `false`
原因：workspace 模板资产不在当前默认路径，需要设置 `PM_WORKSPACE_TEMPLATE_ROOT`
- `route-gsd` 里 `runtime.ready` 是 `false`
原因：本地缺少 `gsd-tools`、`node`，或 `GSD_TOOLS_PATH` 指向错误；先安装 `get-shit-done`
- `plan-phase` 报 `Unknown agent id`
原因：front agent 不存在；请先运行 `openclaw agents list --bindings`，不要把 `codex` 这个 ACP worker 名字直接当成 front agent
- `materialize-gsd-tasks` 没有按预期工作
原因：这一步需要真实 task backend，不属于本地无鉴权 smoke
- `upload-attachments` 一直返回 `authorization_required`
原因：附件 OAuth 还没完成，或者 token 已过期/权限不全
- `auth-link` 报 `missing channels.feishu.appId/appSecret in openclaw.json`
原因：Feishu app 配置没写进 `openclaw.json`
- `invoke_openclaw_tool.py --dry-run` 就失败
原因：通常是 `openclaw.json` 找不到、gateway token 不存在、或 gateway URL 无法解析
- `openclaw plugins info openclaw-lark` 没有 `Status: loaded`
原因：插件未安装、未启用、安装记录损坏，或 OpenClaw 版本过低

## Bridge 调试路径

如果你发现“Codex 跑完了，但父会话没自动汇报”，建议按这个顺序排查：

1. 先确认这是不是 bridge 范围内的问题

- 如果只是本地 smoke，还没启用插件，这不算 bridge 故障
- 如果插件启用了，但父会话完全没看到任何 progress / completion，再进入下面几步

2. 看配置作用域是否命中

- 检查 `plugins.entries.acp-progress-bridge.config.parentSessionPrefixes`
- 检查 `plugins.entries.acp-progress-bridge.config.childSessionPrefixes`
- 如果你的父会话是本地 main session，却没包含 `agent:*:main`，就不会回推
- 如果你的子会话不是 `agent:codex:acp:`，也不会被默认观察

3. 看 OpenClaw 运行态文件是否真的存在

- session store：`$OPENCLAW_HOME/agents/<agent>/sessions/sessions.json`
- transcript：`<session>.jsonl`
- ACP stream：`<session>.acp-stream.jsonl`

4. 看 plugin 自己的状态摘要

- 执行 `bridge-status`
- 重点关注：
  - `scope`
  - `discovery`
  - 每个 run 的 `hint`

如果这里已经显示：

- `missing parent sessionId`
- `waiting firstProgressDelayMs`
- `waiting progressDebounceMs`
- `waiting settleAfterDoneMs`
- `completion skipped replay`

那问题已经在 plugin 内部可定位，不要再先怀疑 Feishu。

5. 最后再区分“plugin 内部已成功”还是“外部可见结果缺失”

- 如果日志里已有 `progress delivered` / `completion delivered`，说明 bridge 已把内部消息送回父会话
- 这之后如果 Feishu 群里仍没看到自然语言结果，就要去查父会话策略、bindings/channels 或外部投递链路

## 运行态目录说明

| 类别 | 典型位置 | 说明 |
|-----|------|------|
| repo-local | `.planning/`, `.pm/`, `./openclaw.json`, `./.openclaw/openclaw.json` | 跟当前仓库强相关，便于版本化和协作 |
| user-global | `~/.openclaw/`, `~/.config/openclaw/`, `%APPDATA%\\OpenClaw\\`, `%LOCALAPPDATA%\\OpenClawPMCoder\\` | 跟当前用户环境强相关，不应直接提交 |
