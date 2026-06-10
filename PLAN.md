# PLAN.md — PM 工具链瘦身为纯 PM + 官方 lark-cli

## 目标

把 `/Volumes/DATABASE/code/learn/openclaw-pm-coder-kit` 裁剪成一个**纯 PM + Feishu/Lark 任务与文档管理工具**：

- Feishu/Lark 交付只走官方 `lark-cli`
- 不再依赖 OpenClaw / Gateway bridge
- 不再依赖 ACP / coder dispatch / workspace bootstrap / OpenClaw auth bundle
- 保留 PM 的核心能力：`context`、`search`、`create`、`get`、`comment`、`complete`、`docs`、`local backend`
- 本地 backend 必须继续独立可用，不能要求 `lark-cli` 或任何外部飞书登录

这是一次**瘦身/裁剪**，不是新增一套平行架构。目标是把历史 OpenClaw 包袱删掉，只保留 PM 真正需要的任务和文档管理能力。

---

## 当前已确认事实

- `lark-cli` 已安装并可用，版本 `1.0.50`
- clean env 下：
  - bot identity ready
  - user identity missing
  - `doctor` 显示 workspace local ok
- 当前 shell 若残留 OpenClaw 环境变量，会让 `lark-cli auth status` / `doctor` 检测到 `openclaw context detected but lark-cli is not bound to it`
- `lark-cli auth status` / `doctor` **不支持** `--format json`
- PM 目前已有一个基础 `pm_lark_cli.py` 适配层，但 **Phase 1 还只支持 health action**，task/doc/drive/comment 业务映射尚未完成
- `pm` 的 local backend 仍然独立，不应被本次瘦身破坏

---

## 瘦身原则

1. **PM 核心命令优先保留**
   - `context`
   - `next`
   - `search`
   - `get`
   - `create`
   - `comment`
   - `update-description`
   - `complete`
   - `docs`
   - `init`
   - `local backend`

2. **Feishu delivery 只保留官方 lark-cli**
   - 不再允许 OpenClaw/Gateway 作为默认或隐式 fallback
   - `PM_FEISHU_PROVIDER=openclaw-gateway` 只应作为显式 legacy 错误分支，最终删掉

3. **先补齐映射，再删旧代码**
   - 先完成 lark-cli task/comment/doc/drive 映射
   - 再删除 OpenClaw bridge、ACP、coder dispatch、workspace bootstrap、auth/token 逻辑

4. **保留 local backend 独立性**
   - local backend 不得调用 `lark-cli`
   - local backend 不得依赖 OpenClaw 配置或会话状态

5. **删减优先于重构**
   - 只保留 PM 需要的能力
   - 旧的 OpenClaw / ACP / workspace 体系能删就删，不再维护双栈

---

## 剩余目标架构

最终目标是尽量收敛为：

```text
skills/pm/
  SKILL.md

skills/pm/scripts/
  pm.py
  pm_cli.py
  pm_commands.py
  pm_api.py
  pm_api_support.py
  pm_api_context.py
  pm_api_tasks.py
  pm_config.py
  pm_context.py
  pm_docs.py
  pm_lark_cli.py
  pm_local_backend.py
  pm_io.py
  pm_tasks.py
```

如果某些模块只服务于 OpenClaw / ACP / coder dispatch / workspace bootstrap，而不再服务 PM 核心能力，则进入删除或合并候选。

---

## Phase 0 — 盘点与保护边界

### 目标

先确认哪些代码必须保留、哪些可以删除、哪些必须等 lark-cli 映射完成后再删。

### 需要保护的边界

- local backend 必须完整保留
- PM 核心命令必须继续可用
- 任何删除不得影响 `pm context/search/create/comment/complete/docs`
- 任何删除不得让 `pm` 依赖 OpenClaw/Gateway

### 盘点内容

1. 统计 OpenClaw / ACP / coder dispatch / gateway bridge 相关文件
2. 统计 PM 核心命令直接依赖的文件
3. 统计仍需 lark-cli 映射的 Feishu tool/action surface
4. 记录删除顺序和阻塞依赖

### 关注文件

- `skills/pm/scripts/pm_api_support.py`
- `skills/pm/scripts/pm_lark_cli.py`
- `skills/pm/scripts/pm_api_tasks.py`
- `skills/pm/scripts/pm_docs.py`
- `skills/pm/scripts/pm_config.py`
- `skills/pm/scripts/pm_bridge.py`
- `skills/pm/scripts/pm_runtime.py`
- `skills/pm/scripts/pm_dispatch.py`
- `skills/pm/scripts/pm_worker.py`
- `skills/pm/scripts/pm_workspace.py`
- `skills/pm/scripts/pm_bootstrap.py`
- `skills/openclaw-lark-bridge/**`
- `plugins/acp-progress-bridge/**`
- `plugins/skill-router/**`

### 验证命令

```bash
cd /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit
python3 -m py_compile skills/pm/scripts/pm_lark_cli.py skills/pm/scripts/pm_api_support.py skills/pm/scripts/pm_config.py
PYTHONPATH=skills/pm/scripts python3 -m unittest tests.test_pm_lark_cli
```

### 成功标准

- 盘点清楚删除边界
- local backend 不受影响
- lark-cli adapter 仍可正常运行

---

## Phase 1 — 完成 lark-cli 任务/评论主路径

### 目标

让 PM 的核心任务管理命令真正走官方 lark-cli，而不是停留在 health action。

### 需要实现

- `feishu_task_tasklist.list`
- `feishu_task_tasklist.create`
- `feishu_task_tasklist.tasks`
- `feishu_task_task.get`
- `feishu_task_task.create`
- `feishu_task_task.patch`
- `feishu_task_comment.create`
- `feishu_task_comment.list`

### 要求

- 显式字段映射，不允许 flat args 任意透传
- `patch` 必须白名单化字段
- 返回值必须继续兼容 `details_of(payload)`
- 不支持的 action 必须清晰报错，不能静默 fallback 到 OpenClaw bridge

### 验证命令

```bash
cd /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit
PYTHONPATH=skills/pm/scripts pytest -q tests/test_pm_lark_cli.py
PM_FEISHU_PROVIDER=lark-cli python3 skills/pm/scripts/pm.py search --query '__pm_lark_cli_smoke_no_match__'
PM_FEISHU_PROVIDER=lark-cli python3 skills/pm/scripts/pm.py create --summary '[CLI瘦身冒烟] lark-cli adapter test' --request '验证 PM task create 通过官方 lark-cli adapter 创建任务'
PM_FEISHU_PROVIDER=lark-cli python3 skills/pm/scripts/pm.py comment --task-id '<smoke-task-id>' --content 'lark-cli adapter smoke comment'
```

### 成功标准

- `search/create/comment/get` 主路径不再依赖 OpenClaw/Gateway
- `pm` 核心任务流可用
- local backend 仍然独立

---

## Phase 2 — 完成 lark-cli 文档/Drive 主路径

### 目标

让 PM 的文档整理和项目文档 bootstrap 也走官方 lark-cli。

### 需要实现

- `feishu_drive_file.list`
- `feishu_drive_file.create_folder`
- `feishu_drive_file.delete`
- `feishu_create_doc`
- `feishu_update_doc`

### 要求

- 先基于 `lark-cli schema` / `lark-doc` / `lark-drive` 内置 skill 确认具体参数
- 保留 `token` / `file_token` / `doc_url` 兼容字段
- 不支持的动作要明确报错，不要回流到 OpenClaw bridge

### 验证命令

```bash
cd /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit
lark-cli skills read lark-doc
lark-cli skills read lark-drive
lark-cli docs +create --help
lark-cli drive +create-folder --help
PM_FEISHU_PROVIDER=lark-cli python3 skills/pm/scripts/pm.py init --project-name 'PM工具链 CLI 瘦身冒烟' --dry-run
```

### 成功标准

- `pm init` / 文档创建更新不再需要 OpenClaw Gateway
- PM 的项目文档整理能力保留

---

## Phase 3 — 删除 OpenClaw Gateway bridge 与旧 Feishu auth/token 逻辑

### 目标

在 lark-cli 任务/文档主路径完成后，删除 PM 对 OpenClaw Gateway 的直接依赖。

### 可删除内容

- `skills/openclaw-lark-bridge/**`
- `skills/pm/scripts/pm_bridge.py`
- `tests/test_invoke_openclaw_tool.py`
- `BRIDGE_SCRIPT_CANDIDATES` / `BRIDGE_SCRIPT_ENV_VARS` / bridge script discovery
- OpenClaw Feishu app / token / keychain 读取逻辑
- OpenClaw 授权链接 / permission bundle / auth bundle 中与 PM Feishu delivery 无关的部分

### 需要保留或替代的内容

- `pm_lark_cli.py`
- local backend
- PM 核心任务/文档命令

### 验证命令

```bash
cd /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit
python3 -m py_compile skills/pm/scripts/*.py
PYTHONPATH=skills/pm/scripts python3 -m unittest tests.test_pm_lark_cli
```

### 成功标准

- `pm` 不再通过 OpenClaw Gateway 调用 Feishu
- OpenClaw Feishu 配置 / token / bridge 相关路径不再是 PM 依赖

---

## Phase 4 — 删除 ACP / coder dispatch / workspace bootstrap

### 目标

把项目从 OpenClaw 执行派发体系中剥离，只保留 PM 的任务/文档管理能力。

### 可删除或大幅裁剪的内容

- `skills/pm/scripts/pm_runtime.py` 中 OpenClaw / ACP dispatch 相关路径
- `skills/pm/scripts/pm_dispatch.py`
- `skills/pm/scripts/pm_worker.py`
- `skills/pm/scripts/pm_bootstrap.py`
- `skills/pm/scripts/pm_workspace.py` 中 OpenClaw workspace 注册/注销逻辑
- `pm run` 的 ACP / OpenClaw agent 派发分支
- `workspace-init` / `workspace-delete` / `register_workspace` / `unregister_workspace`
- OpenClaw session / bridge / coder handoff 相关配置与文档

### 保留策略

- 如果某些命令还能服务纯 PM 上下文整理，可以降级成只输出上下文，不再派发执行
- 如果不能保留 PM 核心价值，直接删除并在 CLI 中明确提示已废弃

### 验证命令

```bash
cd /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit
PYTHONPATH=skills/pm/scripts python3 -m unittest tests.test_pm_lark_cli
python3 skills/pm/scripts/pm.py context --refresh
python3 skills/pm/scripts/pm.py search --query 'lark-cli adapter test'
```

### 成功标准

- 项目不再默认依赖 ACP / coder dispatch / OpenClaw runtime
- PM 仍然能完成任务/文档整理工作

---

## Phase 5 — 清理插件、测试、文档与残留引用

### 目标

删除已经不再服务 PM 纯瘦身目标的历史文件和引用。

### 可能清理对象

- `plugins/acp-progress-bridge/**`
- `plugins/skill-router/**`
- `examples/openclaw.json5.snippets.md`
- `tests/test_invoke_openclaw_tool.py`
- `skills/openclaw-lark-bridge/**`
- 文档中残留的 OpenClaw / ACP / gateway bridge 说明
- 不再被任何命令调用的测试和 helper

### 需要同步更新

- `AGENTS.md`
- `skills/pm/SKILL.md`
- 任何仍然提到 OpenClaw 作为 PM Feishu 默认路径的文档

### 验证命令

```bash
cd /Volumes/DATABASE/code/learn/openclaw-pm-coder-kit
python3 -m py_compile skills/pm/scripts/*.py
PYTHONPATH=skills/pm/scripts python3 -m unittest tests.test_pm_lark_cli
```

### 成功标准

- 仓库中不再保留 PM 需要的 OpenClaw/Gateway/ACP/coder 旧路径
- 纯 PM + lark-cli + local backend 的目标清晰、可维护

---

## 删除顺序建议

1. **先补 lark-cli task/comment/doc/drive 映射**
2. **再删除 OpenClaw Gateway bridge**
3. **再删除 ACP / coder dispatch / workspace bootstrap**
4. **最后清理插件、旧测试、旧文档、旧配置引用**

不要反过来删。没有映射完成就删旧桥接，会让 PM 核心命令断掉。

---

## 风险与假设

### 风险 1：lark-cli 业务映射不完整

- 影响：`search/create/comment/init/docs` 断掉
- 缓解：先做 task/comment，再做 docs/drive，未支持动作必须明确报错

### 风险 2：local backend 被误伤

- 影响：离线/本地 PM 工作流失效
- 缓解：单独测试 local backend，不让它调用 lark-cli

### 风险 3：OpenClaw/ACP 还有残留依赖

- 影响：删完后 `pm run`、bootstrap、插件加载失败
- 缓解：分 Phase 删除，先查依赖再删

### 风险 4：文档/插件里还有历史引用

- 影响：README/AGENTS/SKILL 与实际行为不一致
- 缓解：最后统一清理与回归检查

---

## 非目标

本计划**不**恢复 OpenClaw bridge、ACP dispatch 或 coder 自动执行能力。

本计划也**不**新增新的执行框架。目标只是把 PM 收缩成一个更小、更干净的任务和文档管理工具。
