# 完整安装与集成说明

这份文档面向已经决定做真实接入的人。

如果你只是第一次接触这个仓库，目标只是确认“它能不能跑通一个本地闭环”，不要先读这里，先回到 `README` 走 `3-Minute Quickstart`：

- 英文入口：`README.md`
- 中文入口：`README.zh-CN.md`

只有当你的目标已经变成下面这些事时，再继续看这份文档：

- 把仓库资产部署到 Codex / OpenClaw
- 接入真实 OpenClaw runtime
- 接入 Feishu bot / 群 / task / doc
- 跑通 bridge、授权、真实 backend 初始化和 E2E

相关资料：

- 仓库介绍与角色边界：`README.md`
- 中文介绍：`README.zh-CN.md`
- 最小 PM 配置示例：`examples/pm.json.example`
- OpenClaw 配置片段：`examples/openclaw.json5.snippets.md`

## 0. 先判断你该走哪条路径

这套仓库有三种典型目标，不同目标不要混着排障：

| 路径 | 目标 | 是否应该先看这份文档 |
|------|------|----------------|
| 本地验证 | 证明 `pm` / `coder` / GSD 路由能启动 | 否，先看 `README` |
| OpenClaw 接入 | 证明 skill / plugin / agent 配置生效 | 是 |
| 完整集成 | 证明 task/doc/OAuth/bridge 能跑通 | 是 |

一句话原则：

- 只想验证仓库是否有价值，先走 `README`
- 真正要做运行时接入和协同系统集成，再留在 `INSTALL.md`

## 1. 完整安装 Checklist

如果你的目标已经不是“只验证 repo 能跑”，而是把整套链路真实装起来，按这 6 步走：

1. 先装基础运行时：`python3 >= 3.9`、`node >= 22`、`openclaw = 2026.3.22`、`codex`、`gsd-tools`；如果要 ACP / bridge，再装 `acpx`
2. 如果目标包含 Feishu，这一步就并行准备：安装 `@larksuite/openclaw-lark`、写 `channels.feishu`、准备飞书 app / bot / 群 / 权限、让用户完成 `/auth`；如果要附件上传，再补 attachment OAuth
3. 部署仓库资产：`skills/pm`、`skills/coder`、`skills/product-canvas`、`skills/openclaw-lark-bridge` 放到 Codex；`plugins/acp-progress-bridge` 放到 OpenClaw；兼容窗口内如仍依赖旧 board 命令，再额外同步 `skills/interaction-board`
4. 写配置：先把 `openclaw.json` 和 `pm.json` 配好
5. 再跑 smoke / runtime 验证：这时再跑 `py_compile`、`context --refresh`、`route-gsd`、`openclaw agents list --bindings`、`openclaw plugins list`
6. 最后才做真实 backend 的 `init` 和 E2E；如果是 Feishu backend，必须等 bot / 群 / 权限都 ready 之后再跑真实 `pm init`

### 1.1 这些步骤必须用户手动完成

下面这些动作，AI 最多只能帮你生成链接、命令和导入 JSON，不能替你点完：

1. 运行 `@larksuite/openclaw-lark` 的交互式安装流程，并在需要时扫码或确认 App 信息
2. 在飞书开放平台确认新增应用权限，并发布应用版本
3. 在飞书里私聊机器人或目标群里执行 `/auth` 或 `/feishu auth`
4. 在真实群里发消息验证“不用 @ 也回复”是否已经生效

也就是说，AI 可以把授权入口一次性整理好，但最后的人机确认动作还是要你自己点。

## 2. 安装策略

如果你已经决定做完整安装，推荐顺序如下：

1. 先检查并补齐运行时。
2. 如果目标包含 Feishu，让用户并行准备 app / bot / 群 / 权限，同时安装 `openclaw-lark`。
3. 先把仓库资产部署到 Codex / OpenClaw，并写好 `openclaw.json` / `pm.json`。
4. 再跑 smoke 和 runtime 验证。
5. 最后才做真实 Feishu backend 的 `init`、任务流和 E2E。

关键原则：

- 默认先走 `local/repo` backend，再接真实 Feishu。
- 先补依赖，再改配置。
- `front agent` 和 ACP worker 不是一回事，不要把 `codex` 直接当成 front agent。
- `cc` 不是必需前置，但要记录是否已安装。
- `openclaw` 默认基线固定为 `2026.3.22`，不要默认升级到 `2026.4.5+`。
- 如果目标包含 Feishu，用户侧创建 app / bot / 群 / 权限申请要和机器侧安装并行进行。

## 3. Step 0：环境检查

### 3.1 必查命令

最少检查：

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
python3 --version
node -v
openclaw -v
```

Windows PowerShell:

```powershell
Get-Command python3
Get-Command node
Get-Command openclaw
Get-Command codex
Get-Command cc
Get-Command gsd-tools
python3 --version
node -v
openclaw -v
```

版本基线：

- Python `>= 3.9`
- Node.js `>= 22`
- OpenClaw `= 2026.3.22`

注意：

- 不能只看“机器上有更高版本 Python”；真正执行 `pm.py` 的 `python3` 必须满足 `>= 3.9`
- 如果机器上同时有 3.8 和 3.12，建议把登录环境里的默认 `python3` 前置到 3.12
- 这次远端验证机实际用的是 `~/.local/bin/python3 -> /usr/local/bin/python3.12`
- 如果 `cc` 不存在，不阻塞本仓库安装，但交付里要明确写出“仅验证了 Codex 路径”

### 3.2 缺失时优先补什么

#### GSD

如果要让 `route-gsd`、`plan-phase`、`materialize-gsd-tasks` 正常工作，先安装 GSD：

```bash
npx get-shit-done-cc@latest --codex --global
node ~/.codex/get-shit-done/bin/gsd-tools.cjs --help
```

如果不是默认安装路径，显式设置：

```bash
export GSD_TOOLS_PATH=/abs/path/to/gsd-tools.cjs
```

#### ACPX

如果你准备启用：

- `acp.backend = "acpx"`
- ACP 子会话派发
- `acp-progress-bridge`

就先安装 `acpx` CLI：

```bash
npm install -g acpx@latest
acpx --help
```

注意：

- `acpx` CLI 装好了，不代表旧的 `openclaw.json` 插件配置一定合法
- 如果 `openclaw config validate` 仍报 `plugin not found`，优先修配置，而不是重复安装 CLI

#### Feishu 插件

Feishu 集成依赖运行时插件 `@larksuite/openclaw-lark`，不是本仓库自带代码。

最小检查与安装顺序：

```bash
openclaw plugins list
openclaw plugins info openclaw-lark
openclaw plugins install @larksuite/openclaw-lark
openclaw gateway restart
```

验收标准不是“记住某个包名”，而是：

- `openclaw plugins info openclaw-lark` 显示 `Status: loaded`
- 插件工具面可用

补充一个运行态约束：

- 如果你已经启用了 `openclaw-lark`，通常不要再把内置 `plugins.entries.feishu.enabled` 打开
- 两套 Feishu 工具同时注册时，可能出现 `plugin tool name conflict (openclaw-lark): feishu_chat`
- 在远端真实环境里，这种双注册还可能把 `openclaw plugins list` 顶到 Node OOM

### 3.3 如果目标包含 Feishu，立刻并行准备

不要等本地 smoke 全跑完才让用户去准备 Feishu。

用户侧应并行完成：

1. 创建飞书应用
2. 开启 Bot 能力
3. 准备 `appId` / `appSecret`
4. 创建目标群
5. 申请 task / attachment / doc 相关权限

这里的预期是 OAuth 授权链接或卡片，不是 OpenClaw pairing 二维码。

### 3.4 路径约定

这套仓库按下面顺序查找运行时入口：

1. 显式环境变量覆盖
2. `PATH`
3. 平台候选目录

常见覆盖项：

- `OPENCLAW_BIN`
- `CODEX_BIN`
- `GSD_TOOLS_PATH`
- `OPENCLAW_CONFIG`
- `OPENCLAW_HOME`
- `PM_STATE_DIR`
- `PM_WORKSPACE_ROOT`
- `PM_WORKSPACE_TEMPLATE_ROOT`

如果一台机器上同时有多个 OpenClaw profile，建议显式设置：

```bash
export OPENCLAW_CONFIG=/abs/path/to/real/openclaw.json
```

不要依赖 repo 根目录里的占位 `openclaw.json` 自动猜。

这次远端验证机实际使用的是：

```bash
export OPENCLAW_CONFIG=/home/openclaw/.openclaw-coding-kit/openclaw.json
```

路径建议：

- macOS / Linux：`/abs/path/to/workspace`
- Windows JSON：`C:/path/to/workspace` 或 `C:\\path\\to\\workspace`

## 4. Step 1：本地无鉴权验证

这一段只验证仓库本身，不要求你已经接入 OpenClaw 或 Feishu。

### 4.1 CLI 与语法检查

```bash
python3 -m py_compile skills/pm/scripts/*.py skills/coder/scripts/*.py skills/openclaw-lark-bridge/scripts/*.py
python3 skills/pm/scripts/pm.py --help
python3 skills/pm/scripts/pm.py context --help
python3 skills/coder/scripts/observe_acp_session.py --help
python3 skills/openclaw-lark-bridge/scripts/invoke_openclaw_tool.py --help
```

至少记录：

- `python3` 路径
- `node` 路径
- `openclaw` 路径
- `codex` 路径

### 4.2 先跑 `pm init --dry-run`

```bash
python3 skills/pm/scripts/pm.py init --project-name demo --dry-run
```

如果项目名包含中文或其他非 ASCII 字符：

```bash
python3 skills/pm/scripts/pm.py init --project-name "测试项目" --english-name demo --dry-run
```

重点看：

- `status: "dry_run"`
- `config_preview`
- `workspace_bootstrap`

说明：

- 这一段只是在验证 repo-local CLI 形状，不等于你已经完成了真实安装
- 不传 `--group-id` 时，`workspace_bootstrap: null` 是预期行为
- 非 ASCII 项目名未传 `--english-name` 会直接报错

### 4.3 刷新上下文并验证 GSD 路由

```bash
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
```

至少保留这些 evidence：

- `.pm/current-context.json`
- `.pm/bootstrap.json`
- `.pm/doc-index.json`
- `route-gsd` 输出里的 `runtime.ready`

如果 `route-gsd` 已经报：

- `gsd-tools not found`
- `node not found`

就先修运行时，不要继续谈 `plan-phase`。

### 4.4 repo-local smoke 建议口径

如果你只是要证明仓库本地可用，这一组命令已经够用：

```bash
python3 skills/pm/scripts/pm.py init --project-name demo --task-backend local --doc-backend repo --dry-run
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py route-gsd --repo-root .
```

如果你要再证明本地 task/doc 写入链路也可用，可以补：

```bash
python3 skills/pm/scripts/pm.py create --summary "Install smoke task"
python3 skills/pm/scripts/pm.py upload-attachments --task-id T1 --file ./README.md
python3 skills/pm/scripts/pm.py complete --task-id T1 --content "local smoke done"
python3 skills/pm/scripts/pm.py get --task-id T1 --include-completed
```

预期：

- `.pm/local-tasks.json` 出现任务
- `attachments` 非空
- `comments` 中出现完成说明
- 如果 `pm.json.task.completion_due_mode` 设为 `if_missing` 或 `always`，`get --include-completed` 里还应看到 `due.timestamp == completed_at`

## 5. Step 2：接入 OpenClaw

本地无鉴权验证通过以后，再做这一步。

### 5.1 复制仓库资产

这一段要分清楚两侧：

```text
Codex / CODEX_HOME
skills/pm                    -> ~/.codex/skills/pm
skills/coder                 -> ~/.codex/skills/coder
skills/openclaw-lark-bridge  -> ~/.codex/skills/openclaw-lark-bridge

OpenClaw workspace
plugins/acp-progress-bridge  -> $OPENCLAW_WORKSPACE/plugins/acp-progress-bridge
```

默认推荐：

- `pm`、`coder`、`openclaw-lark-bridge` 先放到 Codex skills 目录
- OpenClaw 侧默认同步 `pm`、`coder` 到 workspace skills
- `acp-progress-bridge` 同步到 OpenClaw plugins 目录
- `skills/openclaw-lark-bridge` 仍然不作为默认 OpenClaw workspace 资产

推荐直接使用仓库自带同步脚本：

```bash
python3 scripts/sync_local_skills.py --target both
```

脚本行为：

- `codex`：默认同步 `pm`、`coder`、`openclaw-lark-bridge`、`project-review`
- `openclaw`：默认同步 `pm`、`coder`
- `openclaw plugins`：默认同步 `acp-progress-bridge`
- 对未变化目录直接跳过，不再每次整目录备份重装
- 会忽略 `__pycache__`、`.DS_Store`、`*.pyc`

如果只想同步指定 skill：

```bash
python3 scripts/sync_local_skills.py --target codex --skill pm
python3 scripts/sync_local_skills.py --target openclaw --skill pm --skill coder
```

如果 OpenClaw front agent 确实也要直接加载 `openclaw-lark-bridge`：

```bash
python3 scripts/sync_local_skills.py --target openclaw --skill pm --skill coder --skill openclaw-lark-bridge
```

同步后立刻检查：

- `~/.codex/skills/pm/SKILL.md` 是否存在
- `~/.codex/skills/coder/SKILL.md` 是否存在
- `~/.codex/skills/openclaw-lark-bridge/SKILL.md` 是否存在
- `plugins/acp-progress-bridge` 主文件是否存在

这里仍然不建议默认复制：

```text
skills/openclaw-lark-bridge -> $OPENCLAW_WORKSPACE/skills/openclaw-lark-bridge
```

### 5.2 最小 OpenClaw 配置

最低要求：

1. 有真实可见的 front agent
2. `acp` 已启用
3. 如果该 front agent 直接依赖 repo skills，再给它挂 `pm` 和 `coder`

最小形状：

```json
{
  "agents": {
    "list": [
      {
        "id": "your-agent-id",
        "name": "your-agent-id",
        "workspace": "REPLACE_WITH_ABSOLUTE_WORKSPACE_PATH",
        "skills": ["pm", "coder"]
      }
    ]
  },
  "acp": {
    "enabled": true,
    "backend": "acpx",
    "defaultAgent": "codex"
  }
}
```

注意：

- `front agent` 配的是你要直接对话的 agent
- ACP worker 由 `acp.defaultAgent` 或运行时派发逻辑决定
- 两者可以相同，也可以不同
- `openclaw-lark-bridge` 默认是 Codex 侧 skill，不是 OpenClaw agent 必挂 skill

验证：

```bash
acpx --help
openclaw agents list --bindings
openclaw plugins list
```

### 5.3 最小 PM 配置

`pm.json` 至少要明确：

1. `repo_root`
2. `project.name`
3. `project.agent`
4. `task.backend`
5. `doc.backend`
6. `coder.backend`
7. `coder.agent_id`

本地优先最小配置：

```json
{
  "task": { "backend": "local" },
  "doc": { "backend": "repo" }
}
```

可选的完成时间同步配置：

- 默认 `task.completion_due_mode = "never"`，完成任务时只写 `completed_at`，不会改 `due`
- `task.completion_due_mode = "if_missing"` 只在任务还没有 `due` 时把 `completed_at` 回填到 `due.timestamp`
- `task.completion_due_mode = "always"` 总是用 `completed_at` 覆盖 `due.timestamp`
- 兼容旧键 `task.sync_completed_at_to_due`：`true` 等价于 `if_missing`，`false` 等价于 `never`
- 这个配置同时影响手动 `pm complete` 和 `pm materialize-gsd-tasks` 触发的自动完成

如果要接 Feishu，再补：

- `task.tasklist_guid` 或可解析的 `tasklist_name`
- `doc.folder_token`
- `project.group_id`

修改后验证：

```bash
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py next --refresh
```

不要直接把旧机器上的 `pm.json` 原样复制到新机器继续跑。至少要重写：

- `repo_root`
- backend 类型
- 旧 `group_id`
- 旧 token / 文档地址

## 6. Step 3：可选接 Feishu / OAuth / Bridge

如果当前目标只是本地或 OpenClaw 接入验证，可以跳过本节。

### 6.1 Feishu 接入最小要求

先完成飞书应用准备，再回头写 repo 配置。

最少需要：

1. 飞书应用和 Bot
2. `appId` / `appSecret`
3. 事件订阅
4. task / doc / attachment 所需权限
5. 目标群

建议优先参考：

- OpenClaw Feishu 文档
- `larksuite/openclaw-lark` README

安装后先做诊断，不要手抄一大段权限清单。

### 6.2 OpenClaw Feishu 配置

最小形状：

```json5
{
  channels: {
    feishu: {
      enabled: true,
      domain: "feishu",
      accounts: {
        main: {
          appId: "cli_xxx",
          appSecret: "xxx",
          name: "My AI assistant"
        }
      }
    }
  }
}
```

如果是国际版 Lark，把 `domain` 改成 `"lark"`。

如果目标是群会话，还要补：

- `bindings`
- `channels.feishu.groups`
- 必要时 `groupAllowFrom`

这里有一个高频坑：

- `allowFrom` 通常是用户
- `groupAllowFrom` 通常是群 id，例如 `oc_xxx`

如果 `groupPolicy = "allowlist"`，但 `groupAllowFrom` 里写成用户 open_id，机器人会收到群消息但不回复。

### 6.3 统一授权入口

现在 `pm init` 默认会附带 `auth_bundle`。

如果你想单独重新生成整套授权引导，直接运行：

```bash
python3 skills/pm/scripts/pm.py auth
```

默认会一次性输出：

- tenant 应用权限 bundle
- 群里不用 `@` 也回复所需的敏感权限
- 附件上传所需的 user OAuth 链接
- 机器人侧建议执行的 `/auth` / `/feishu auth`
- 当前仍需人工确认的步骤

输出里可以直接优先看这几个顶层字段：

- `permission_url`
- `app_scope_auth_url`
- `user_oauth_verification_url`
- `manual_steps`

如果你只想做最小初始化、不想默认生成这组引导，可以显式关闭：

```bash
python3 skills/pm/scripts/pm.py init --project-name demo --no-auth-bundle --dry-run
```

### 6.4 `/auth` 与附件 OAuth

Bot 能收消息后，要明确引导用户主动触发授权：

- 优先尝试 `/auth`
- 如果机器人帮助文案显示 `/feishu auth`，以机器人提示为准

附件上传不是 bridge 行为，而是 PM 直接调用 Feishu attachment API。

第一次执行下面命令时，如果还没有有效 OAuth：

```bash
python3 skills/pm/scripts/pm.py attachments --task-id T1
python3 skills/pm/scripts/pm.py upload-attachments --task-id T1 --file ./evidence.txt
```

预期会返回：

- `status = "authorization_required"`
- `verification_uri_complete`
- `user_code`

也可以主动取授权链接：

```bash
python3 skills/pm/scripts/pm.py auth-link \
  --mode user-oauth \
  --scopes task:task:read task:attachment:read task:attachment:write offline_access
```

如果附件授权失败，按这个顺序排查：

1. `openclaw.json` 里是否已有 `channels.feishu.appId` / `appSecret`
2. app 权限是否完整
3. 返回的授权链接是否由正确账号完成
4. state 目录里是否残留过期 token / pending 文件

补充一个这次远端真实踩到的坑：

- 如果 `appSecret` 不是明文，而是 OpenClaw SecretRef，例如 `{"source":"file","provider":"lark-secrets","id":"/lark/appSecret"}`，旧版 PM 可能会把它当普通字符串直接发给飞书，表现为 `device authorization failed: invalid_client`
- 现在仓库内 PM 已支持解析常见的 `env` / `file` / `exec` SecretRef；如果你在旧环境里遇到这个报错，先不要急着怀疑飞书凭证本身错了，先检查是不是 SecretRef 没有被正确解引用

### 6.5 把飞书权限开通抽出来

不要把“权限开通”混在长链路安装末尾再做。

尤其下面这类能力，应该单独准备并尽早验：

- 群里不用 `@` 也回复
- PM 附件上传
- Feishu task / doc 真同步

先看内置 preset：

```bash
python3 skills/pm/scripts/pm.py permission-bundle --list-presets
```

给 OpenClaw Lark 插件生成 tenant 权限导入 JSON：

```bash
python3 skills/pm/scripts/pm.py permission-bundle \
  --preset openclaw-lark-tenant-baseline
```

给“群里不 @ 也回复”额外生成敏感权限导入 JSON：

```bash
python3 skills/pm/scripts/pm.py permission-bundle \
  --preset openclaw-lark-tenant-baseline \
  --preset group-open-reply
```

输出里重点看：

- `permission_url`
- `auth_url`
- `import_payload`
- `notes`
- `manual_steps`

这一步的定位要说清楚：

- PM 现在能帮你生成权限页链接和批量导入 JSON
- 但 `im:message.group_msg` 这类敏感权限，仍然要在飞书开放平台确认新增权限并重新发布应用
- 也就是说，这不是“后台全自动开通”，而是“把要开的权限一次性整理好，减少人工抄写和漏项”
- 飞书官方插件能自动化的是“扫码建 bot / 写配置 / 生成用户授权入口”，不能替你在开放平台代点“确认新增权限”“创建版本”“确认发布”

如果你已经把 `requireMention=false` 配好了，但群里还是必须 `@` 才回复，优先检查这里，而不是反复重装 OpenClaw。

### 6.6 用户手动步骤要单独看

完整安装里，下面这些动作一定要明确告诉用户是“手动步骤”：

1. 手动运行 `npx -y @larksuite/openclaw-lark install`
2. 如果安装过程要求扫码或确认 App 信息，用户自己完成
3. 手动在飞书开放平台导入权限、确认新增权限并发布
4. 手动在飞书里执行 `/auth` 或 `/feishu auth`
5. 手动在目标群里发普通消息验证机器人是否已经能免 `@` 回复

不要把这些步骤写成“AI 会自动做好”，否则后面最容易绕晕。

### 6.7 可选启用 progress bridge

只有在你需要下面能力时，才启用 `acp-progress-bridge`：

- 子会话进度自动回推
- 子会话完成结果自动回推
- Feishu 群内持续看到执行状态

它不是最小安装前置。

如果 bridge 没有自动汇报，按这个顺序排查：

1. `parentSessionPrefixes` 是否命中父会话
2. `childSessionPrefixes` 是否命中子会话
3. OpenClaw session store / transcript / ACP stream 是否存在
4. `bridge-status` 是否已显示 `progress delivered` 或 `completion delivered`

如果 plugin 内部已经 delivered，但外部仍看不到结果，再去查父会话策略、bindings 或消息投递链路。

## 7. 验收建议

### 7.1 最小可交付

如果只做本地验证，至少交付：

1. `py_compile`
2. `pm.py --help`
3. `init --dry-run`
4. `context --refresh`
5. `route-gsd --repo-root .`

### 7.2 OpenClaw 接入验收

至少补：

1. `openclaw agents list --bindings`
2. `openclaw plugins list`
3. `python3 skills/pm/scripts/pm.py next --refresh`

### 7.3 完整集成验收

如果用户明确要求 Feishu E2E，再继续做。

这里的前置条件必须已经满足：

1. OpenClaw runtime 已可用
2. `openclaw-lark` 已安装并加载
3. `channels.feishu` 已配置
4. 飞书 app / bot / 群 / 权限已准备好
5. 用户已能通过 `/auth` 或环境里的等价命令完成授权

真正的完整链路才是：

1. 创建真实任务
2. 派给 Codex
3. 观察 bridge 回推
4. 完成任务
5. 读取最终状态

可直接按下面顺序执行：

```bash
python3 skills/pm/scripts/pm.py init --project-name demo --group-id oc_xxx --task-backend feishu --doc-backend feishu --write-config
python3 skills/pm/scripts/pm.py create --summary "Install E2E smoke task" --request "Verify PM -> coder -> bridge -> completion flow"
python3 skills/pm/scripts/pm.py run --task-id T1
python3 skills/pm/scripts/pm.py complete --task-id T1 --content "E2E smoke done"
python3 skills/pm/scripts/pm.py get --task-id T1 --include-completed
```

如果你在 `pm.json.task` 里显式开启了 `completion_due_mode`，最后一步返回的任务详情还应体现 `due.timestamp` 已按配置回填。

建议最终交付统一按这几个状态汇报：

```text
Installation Summary
- repo_smoke: pass/fail
- gsd_runtime: pass/fail
- openclaw_runtime: pass/fail
- openclaw_lark: pass/fail
- progress_bridge: not_run/pass/fail
- feishu_binding: not_run/pass/fail
- attachment_oauth: not_run/pass/fail
```

## 8. 常见问题

- `workspace` 不是绝对路径：改成目标机器真实绝对路径
- Windows JSON 路径未转义：优先写 `C:/...`
- 中文项目名没传 `--english-name`：补参数
- `route-gsd` 的 `runtime.ready = false`：先检查 `node` 和 `gsd-tools`
- `plan-phase` 报 `Unknown agent id`：说明 front agent 不存在，不要把 ACP worker 当成 front agent
- `upload-attachments` 一直返回 `authorization_required`：附件 OAuth 还没完成，不等于 PM 安装失败
- `openclaw plugins info openclaw-lark` 不是 `Status: loaded`：插件未安装、未启用或版本不兼容
- 群消息到了但机器人不回：优先检查 `groupAllowFrom` 是否写成了错误的用户 id
- `invoke_openclaw_tool.py --dry-run` 失败：通常是 `openclaw.json`、gateway token 或 gateway URL 解析有问题

## 9. 运行态目录

| 类别 | 典型位置 | 说明 |
|------|----------|------|
| repo-local | `.planning/`, `.pm/`, `./openclaw.json`, `./.openclaw/openclaw.json` | 跟当前仓库强相关，适合版本化 |
| user-global | `~/.openclaw/`, `~/.config/openclaw/`, `%APPDATA%\\OpenClaw\\`, `%LOCALAPPDATA%\\OpenClawPMCoder\\` | 跟当前用户环境强相关，不应直接提交 |
