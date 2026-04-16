# Interaction Board Inventory

- 生成时间：`2026-04-15T17:21:29+08:00`
- 项目：`Eggturtle 生产后台`
- 已注册页面：`2`
- 候选页面：`0`
- 草稿节点：`0`
- 关系边：`2`
- 冲突项：`0`
- 有截图页面：`2`
- 截图快照：`2`
- 绑定场景节点：`2`
- 场景引用：`3`

## 页面矩阵

| 状态 | 标题 | 路由 | 分组 | 包 | 截图 | 场景 | 组件 |
|---|---|---|---|---|---|---|---|
| 已注册 | 后台登录 | `login` | entry | main | scenario:prod-admin-login | prod-admin-dashboard, prod-admin-login | `apps/admin/app/login/page.tsx` |
| 已注册 | 平台概况 | `dashboard` | admin | main | scenario:prod-admin-dashboard | prod-admin-dashboard | `apps/admin/app/dashboard/page.tsx` |

## 主要关系

| From | To | 类型 | 触发 |
|---|---|---|---|
| 后台登录 | 平台概况 | navigateTo | password-login:router.replace |
| 平台概况 | 后台登录 | redirect | middleware:missing-session |

## 冲突清单

- 当前未发现冲突。
