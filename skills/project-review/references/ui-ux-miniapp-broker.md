# Miniapp Broker Workflow

适用场景：

- 同一个项目有多个 worktree / 分支并行开发
- 同时还有多个不同的小程序项目
- 需要确保 agent 连的是正确 target，而不是某个历史默认实例

## 默认原则

- 显式路径优先，不盲猜
- 没传路径时，只允许从当前 `cwd` 推导唯一候选
- 先核对 identity，再做自动化操作
- `auto-miniprogram` 是 broker，不再假设它启动时就已经绑定目标项目

## 标准顺序

1. 解析路径

```bash
node scripts/resolve_miniapp_target.js --path <project_root|worktree_root|app_root>
```

如果你只是想先做“resolve path -> register target -> probe -> screenshot”的快速 smoke，不必手动拆步骤，直接跑：

```bash
node scripts/miniapp_smoke.js \
  --path <project_root|worktree_root|app_root> \
  --json-output out/miniapp-smoke.json
```

它内部会转调 `auto-miniprogram` 的：

```bash
pnpm --dir /Volumes/DATABASE/code/auto-miniprogram run broker:probe -- --path <resolved_worktree> --json
```

2. 确保 broker 存在

- 调 `miniapp_ensure_project_broker`
- 输入用上一步解析出来的 `projectRoot` 或 `appRoot`

3. 注册并激活 target

- 调 `miniapp_register_target`
- 推荐传：
  - `worktree_root`
  - 或 `app_root`
  - `use_now=true`

4. 探测运行时

- 调 `miniapp_probe_runtime`
- 如果需要构建，显式传 `ensure_build=true`

5. 核对返回 identity

至少确认：

- `identity.projectRoot`
- `identity.worktreeRoot`
- `identity.appRoot`
- `identity.gitBranch`
- `identity.label`

如果在真机 / LAN 模式，再额外确认：

- `identity.clientHost`
- `identity.clientApiBaseUrl`
- `identity.clientPublicWebBaseUrl`

6. 再执行具体自动化

- `miniapp_screenshot`
- `miniapp_query_elements`
- `miniapp_get_page_data`
- `miniapp_tap_element`
- `miniapp_input_element`
- `miniapp_get_logs`
- `miniapp_get_exceptions`

## 项目特例

如果目标项目本身就有“按 worktree 分配 devtools 端口 / identity”的启动入口，先执行项目已有命令，再注册到 broker。

常见模式是：

```bash
pnpm --filter <miniapp-package> <project-specific-devtools-command>
```

这样项目自己的 `.env.*.local` 或等价配置会先写好该 worktree 的端口和 identity，再注册到 broker。

## 错误处理

- 报 `No miniapp target bound`：先 `miniapp_register_target`
- 报 `target 名称存在于多个项目`：给 `miniapp_use_target` 补 `project_key`
- identity 不一致：停止自动化，重新绑定正确路径
