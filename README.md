# OpenClaw PM Coder Kit

这是一个把 `PM + Developer + ACPX + progress bridge + 共享工作区` 组合成可复用工程资产的仓库。

它不是一篇零散教程，也不是只给单次 demo 用的脚手架。这个仓库的目标，是把复杂项目里已经验证过生产力的一套协作模式，沉淀成可安装、可版本化、可跨平台迁移的 kit。

## 最快开始

如果你只是想先把这套 kit 跑起来，不要一上来就啃完整安装文档。最快路径建议这样走：

1. Star / clone 这个仓库
2. 先看 [INSTALL.md](./INSTALL.md) 里的本地无鉴权验证部分
3. 直接把 [INSTALL.md](./INSTALL.md) 交给 Codex / Claude Code 一类 AI 安装代理执行

推荐的最短口径：

- 人看：先看 [INSTALL.md](./INSTALL.md)
- AI 看：直接读 [INSTALL.md](./INSTALL.md)
- 第一目标：先跑通本地模式，不要一开始就接 Feishu

如果你只是想验证 repo 是否能跑，先完成这 3 个检查就够：

```bash
python3 -m py_compile skills/pm/scripts/*.py skills/coder/scripts/*.py
python3 skills/pm/scripts/pm.py init --project-name demo --task-backend local --doc-backend repo --dry-run
python3 skills/pm/scripts/pm.py context --refresh
```

这 3 步过了，再继续 `route-gsd`、OpenClaw front agent、Feishu / progress bridge 集成，排错成本最低。

## 这套架构解决什么问题

复杂需求一旦塞进单个 AI 会话，很容易出现三类问题：

- 业务沟通、排期、实现细节混在一起，上下文容易污染
- 不同 AI 工具各自擅长不同环节，但天然不共享同一套项目事实
- 多群、多会话、多子任务并行后，进度和结果很难稳定回流

这个仓库的核心思路是：

- `PM` 负责需求澄清、任务流、文档同步、上下文组织
- `Developer / coder` 负责 ACP coding session 的实际执行
- 飞书工作区在集成模式下承担共享事实源
- `acp-progress-bridge` 负责把子会话进度和完成结果回推到父会话

如果你当前只是先在本地验证这套链路，也可以先不接 Feishu，直接走 repo-local 的 bootstrap 和 smoke checks。
现在也可以显式使用 repo-local backend 先闭环：

- `task.backend = "local"`
- `doc.backend = "repo"`

这样 `pm create`、`pm context --refresh`、`pm coder-context`、`materialize-gsd-tasks` 都能先在本地跑通。
现在本地模式也支持把 `--file` 证据挂到任务上，附件元数据会落到 `.pm/local-tasks.json`。

## 为什么是 PM + Developer

这套 kit 不是为了把一个 AI 会话包装得更复杂，而是为了把原来容易混在一起的三类工作拆开：

- `PM` 负责和业务、客户、排期、范围、文档说人话
- `coder` 负责把已经收敛的任务上下文转成代码与验证结果
- `bridge` 负责把子会话里的执行进度异步回流给父会话

这样做的原因很直接：

- 业务沟通和编码实现的上下文污染模式不同，不应该强塞进同一个长会话
- PM 侧适合维护共享文档、todo、需求变更和进度叙事
- coder 侧适合拿稳定上下文做实现、调试、验证和交付
- bridge 只负责回传 progress/completion，不负责拥有任务真相

如果没有飞书群，这套模型也能跑，只是父会话从 Feishu group 退化为本地 `main` 会话。

## 使用模式

这套仓库建议分两档理解：

- 本地优先模式：先验证 `pm` / `coder` / GSD 路由、安装步骤、文档和脚本是否一致，不依赖真实 Feishu
- 集成模式：再把仓库内容接入真实 OpenClaw 实例，并按需启用 Feishu 绑定和 `acp-progress-bridge`

这两个模式不是互斥关系，而是推荐顺序。先做本地验证，再接外部依赖，排错成本最低。

## 角色边界

分享和排错时，统一按下面这张口径理解：

- `PM` 是 tracked work front door。用户请求先进入 PM，由 PM 决定是否建任务、刷新上下文、走 task/doc 写回、以及是否路由到 GSD 或 coder。
- `GSD` 是 roadmap / phase backend。它负责 `.planning/*` 里的 phase planning 和执行编排，不拥有 task/doc truth。
- `coder` 是 canonical execution worker。它读取 PM 交给它的上下文，执行代码工作，并把证据和结果写回 PM。
- `acp-progress-bridge` 是 progress relay。它观察 ACP 子会话并把进度/完成素材回推到父会话，不负责 task/doc 写入，也不是 source of truth owner。

对应命令边界：

- `route-gsd`：判断当前 phase 下一步该 plan、execute 还是 materialize
- `plan-phase`：为某个 phase 产出或刷新 `.planning/phases/*/*-PLAN.md`
- `materialize-gsd-tasks`：把 phase plan 映射成任务系统中的 tracked tasks；只有你真的要 task backend 对齐时才需要
- 当 `task.backend = "local"` 时，上面的 tracked tasks 会落到 `.pm/local-tasks.json`

如果当前只是本地执行 phase 计划，不要把“已完成 plan 执行”误说成“已经完成任务同步”。

## Source Of Truth 分层

这套仓库里至少有四层 truth，必须分开讲：

- `.planning/*`：roadmap、phase、summary 的长期规划 truth，由 GSD 工作流消费
- `.pm/*.json`：PM repo-local cache 和 handoff bundle，是运行辅助快照，不是最终业务 truth
- Feishu task/doc：协作 truth。只有在真实集成模式下，它才承载共享任务、长文档和团队可见进度
- OpenClaw session/state：会话运行态 truth，主要服务 ACP 子会话、bridge 发现和 parent/child 关联

不要把 `.planning`、`.pm`、Feishu task/doc、session store 混写成同一种状态。

## 快速入口

建议按这个顺序进入：

1. 看 [INSTALL.md](./INSTALL.md)
2. 本地先跑 `python3 skills/pm/scripts/pm.py init --project-name demo --dry-run`
3. 再跑 `python3 skills/pm/scripts/pm.py context --refresh`
4. 最后用 `python3 skills/pm/scripts/pm.py route-gsd --repo-root .`

如果你要先走完全本地模式，推荐把 `pm.json` 配成：

```json
{
  "task": { "backend": "local" },
  "doc": { "backend": "repo" }
}
```

如果你项目名包含中文或其他非 ASCII 字符，补上：

```bash
python3 skills/pm/scripts/pm.py init --project-name "测试项目" --english-name demo --dry-run
```

## PM/GSD 验证基线

如果你想验证的是 PM/GSD product surface，不要把所有命令当成同一种检查：

- 本地无鉴权：`init --dry-run`、`context --refresh`、`route-gsd --repo-root .`
- 宿主 runtime：`openclaw agents list --bindings`，再看 `plan-phase`
- 真实 task backend：最后才看 `materialize-gsd-tasks`

一个简单判断原则：

- `route-gsd` 主要验证 repo-local planning 和 runtime diagnostics
- `plan-phase` 还依赖真实 OpenClaw front agent
- `materialize-gsd-tasks` 会依赖当前 task backend；如果配置成 `local`，它也可以作为 repo-local smoke

更完整的 operator 路径见 [INSTALL.md](./INSTALL.md) 和 [.planning/codebase/TESTING.md](./.planning/codebase/TESTING.md)。

## 仓库结构

```text
openclaw-pm-coder-kit/
  README.md
  INSTALL.md
  examples/
    openclaw.json5.snippets.md
    pm.json.example
  plugins/
    acp-progress-bridge/
  skills/
    coder/
    openclaw-lark-bridge/
    pm/
  tests/
```

目录职责：

- `skills/pm`：任务编排 front door、文档同步、上下文组织、GSD 路由
- `skills/coder`：canonical execution worker，负责 ACP coding session 的 dispatch / continue / observe / execution
- `skills/openclaw-lark-bridge`：repo 内 Feishu bridge script，复用 OpenClaw Gateway 里已加载的 `openclaw-lark` 工具
- `plugins/acp-progress-bridge`：progress relay，把子会话进度和完成结果回推到父会话
- `examples/`：最小配置与增强配置片段
- `tests/`：repo-local unittest 基线，优先覆盖新抽象 seam

## 跨平台路径约定

从 Phase 2 开始，关键运行时路径统一遵循：

1. 显式环境变量覆盖
2. `PATH` / 系统命令发现
3. 平台候选目录兜底

当前已经支持的关键覆盖项：

- `OPENCLAW_BIN`
- `CODEX_BIN`
- `GSD_TOOLS_PATH`
- `OPENCLAW_LARK_BRIDGE_SCRIPT`
- `OPENCLAW_CONFIG`
- `OPENCLAW_HOME`
- `PM_STATE_DIR`
- `PM_WORKSPACE_ROOT`
- `PM_WORKSPACE_TEMPLATE_ROOT`

常见检查命令：

- macOS / Linux: `which openclaw`, `which codex`, `which node`
- Windows CMD: `where openclaw`, `where codex`, `where node`
- Windows PowerShell: `Get-Command openclaw`, `Get-Command codex`, `Get-Command node`

## 运行态目录边界

安装和排错时要明确区分两类路径：

- repo-local：`.planning/`、`.pm/`、可选的 `./openclaw.json`、`./.openclaw/openclaw.json`
- user-global：OpenClaw 用户配置目录、ACP session store、PM 全局状态目录

不要把 repo-local 文档资产和 user-global 运行态缓存当成同一类东西。

## 示例入口

从示例配置开始时，优先看：

1. [examples/pm.json.example](./examples/pm.json.example)
2. [examples/openclaw.json5.snippets.md](./examples/openclaw.json5.snippets.md)

其中：

- `pm.json.example` 现在是本地优先的最小示例
- `openclaw.json5.snippets.md` 里把最小配置、progress bridge、Feishu 绑定拆成了不同片段

## 安全约定

这个仓库只提交代码、示例和文档，不提交真实运行态数据。

不要提交：

- 真实 token、API key、OAuth 凭证
- 真实 Feishu 群 ID、用户 ID、allowlist
- 真实项目文档链接、tasklist GUID
- 本地 session、缓存、state
