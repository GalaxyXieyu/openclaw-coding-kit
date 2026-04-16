# Interaction Board Inventory

- 生成时间：`2026-04-15T23:36:23+08:00`
- 项目：`admin`
- 已注册页面：`36`
- 候选页面：`0`
- 草稿节点：`0`
- 关系边：`74`
- 冲突项：`0`
- 有截图页面：`33`
- 截图快照：`33`
- 绑定场景节点：`36`
- 场景引用：`36`

## 页面矩阵

| 状态 | 标题 | 路由 | 分组 | 包 | 截图 | 场景 | 组件 |
|---|---|---|---|---|---|---|---|
| 已注册 | 后台根入口 | `` | entry | main | redirect:admin-dashboard | prod-admin-admin-root | `apps/admin/app/page.tsx` |
| 已注册 | 后台登录 | `login` | entry | main | planned | prod-admin-admin-login | `apps/admin/app/login/page.tsx` |
| 已注册 | 数据 | `dashboard` | admin | main | scenario:prod-admin-admin-dashboard | prod-admin-admin-dashboard | `apps/admin/app/dashboard/page.tsx` |
| 已注册 | 活跃度看板 | `dashboard/analytics` | admin | main | scenario:prod-admin-admin-dashboard-analytics | prod-admin-admin-dashboard-analytics | `apps/admin/app/dashboard/analytics/page.tsx` |
| 已注册 | 治理记录 | `dashboard/audit-logs` | admin | main | redirect:admin-dashboard-settings-audit-logs | prod-admin-admin-dashboard-audit-logs | `apps/admin/app/dashboard/audit-logs/page.tsx` |
| 已注册 | 账单跳转 | `dashboard/billing` | admin | main | redirect:admin-dashboard-analytics-revenue | prod-admin-admin-dashboard-billing | `apps/admin/app/dashboard/billing/page.tsx` |
| 已注册 | 社区入口 | `dashboard/guiquan-management` | admin | main | redirect:admin-dashboard-commerce-community | prod-admin-admin-dashboard-guiquan-management | `apps/admin/app/dashboard/guiquan-management/page.tsx` |
| 已注册 | 用量看板 | `dashboard/usage` | admin | main | scenario:prod-admin-admin-dashboard-usage | prod-admin-admin-dashboard-usage | `apps/admin/app/dashboard/usage/page.tsx` |
| 已注册 | 活跃度看板 | `dashboard/analytics/activity` | admin | main | scenario:prod-admin-admin-dashboard-analytics-activity | prod-admin-admin-dashboard-analytics-activity | `apps/admin/app/dashboard/analytics/activity/page.tsx` |
| 已注册 | 付费看板 | `dashboard/analytics/revenue` | admin | main | scenario:prod-admin-admin-dashboard-analytics-revenue | prod-admin-admin-dashboard-analytics-revenue | `apps/admin/app/dashboard/analytics/revenue/page.tsx` |
| 已注册 | 会员入口 | `dashboard/memberships` | users | main | redirect:admin-dashboard-tenant-management | prod-admin-admin-dashboard-memberships | `apps/admin/app/dashboard/memberships/page.tsx` |
| 已注册 | 平台用户 | `dashboard/tenant-management` | users | main | scenario:prod-admin-admin-dashboard-tenant-management | prod-admin-admin-dashboard-tenant-management | `apps/admin/app/dashboard/tenant-management/page.tsx` |
| 已注册 | Tenants | `dashboard/tenants` | users | main | redirect:admin-dashboard-tenant-management | prod-admin-admin-dashboard-tenants | `apps/admin/app/dashboard/tenants/page.tsx` |
| 已注册 | 租户详情 | `dashboard/tenants/[tenantId]` | users | main | planned | prod-admin-admin-dashboard-tenants-tenantid | `apps/admin/app/dashboard/tenants/[tenantId]/page.tsx` |
| 已注册 | 宠物档案摘要 | `dashboard/tenants/[tenantId]/livestock` | users | main | scenario:prod-admin-admin-dashboard-tenants-tenantid-livestock | prod-admin-admin-dashboard-tenants-tenantid-livestock | `apps/admin/app/dashboard/tenants/[tenantId]/livestock/page.tsx` |
| 已注册 | 经营 | `dashboard/commerce` | commerce | main | redirect:admin-dashboard-commerce-catalog | prod-admin-admin-dashboard-commerce | `apps/admin/app/dashboard/commerce/page.tsx` |
| 已注册 | 商品目录 | `dashboard/commerce/catalog` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-catalog | prod-admin-admin-dashboard-commerce-catalog | `apps/admin/app/dashboard/commerce/catalog/page.tsx` |
| 已注册 | 社区 | `dashboard/commerce/community` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-community | prod-admin-admin-dashboard-commerce-community | `apps/admin/app/dashboard/commerce/community/page.tsx` |
| 已注册 | 发货履约 | `dashboard/commerce/fulfillment` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-fulfillment | prod-admin-admin-dashboard-commerce-fulfillment | `apps/admin/app/dashboard/commerce/fulfillment/page.tsx` |
| 已注册 | 二级市场 | `dashboard/commerce/marketplace` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-marketplace | prod-admin-admin-dashboard-commerce-marketplace | `apps/admin/app/dashboard/commerce/marketplace/page.tsx` |
| 已注册 | 订单管理 | `dashboard/commerce/orders` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-orders | prod-admin-admin-dashboard-commerce-orders | `apps/admin/app/dashboard/commerce/orders/page.tsx` |
| 已注册 | 售后客服 | `dashboard/commerce/support` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-support | prod-admin-admin-dashboard-commerce-support | `apps/admin/app/dashboard/commerce/support/page.tsx` |
| 已注册 | 商品详情 | `dashboard/commerce/catalog/[productId]` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-catalog-productid | prod-admin-admin-dashboard-commerce-catalog-productid | `apps/admin/app/dashboard/commerce/catalog/[productId]/page.tsx` |
| 已注册 | 新建商品 | `dashboard/commerce/catalog/new` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-catalog-new | prod-admin-admin-dashboard-commerce-catalog-new | `apps/admin/app/dashboard/commerce/catalog/new/page.tsx` |
| 已注册 | 帖子详情 | `dashboard/commerce/community/[postId]` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-community-postid | prod-admin-admin-dashboard-commerce-community-postid | `apps/admin/app/dashboard/commerce/community/[postId]/page.tsx` |
| 已注册 | 新建帖子 | `dashboard/commerce/community/new` | commerce | main | scenario:prod-admin-admin-dashboard-commerce-community-new | prod-admin-admin-dashboard-commerce-community-new | `apps/admin/app/dashboard/commerce/community/new/page.tsx` |
| 已注册 | 挂牌详情 | `dashboard/commerce/marketplace/[listingId]` | commerce | main | planned | prod-admin-admin-dashboard-commerce-marketplace-listingid | `apps/admin/app/dashboard/commerce/marketplace/[listingId]/page.tsx` |
| 已注册 | 设置入口 | `dashboard/settings` | settings | main | redirect:admin-dashboard-settings-pricing | prod-admin-admin-dashboard-settings | `apps/admin/app/dashboard/settings/page.tsx` |
| 已注册 | 审计记录 | `dashboard/settings/audit-logs` | settings | main | scenario:prod-admin-admin-dashboard-settings-audit-logs | prod-admin-admin-dashboard-settings-audit-logs | `apps/admin/app/dashboard/settings/audit-logs/page.tsx` |
| 已注册 | 徽章分享素材 | `dashboard/settings/footprint-achievements` | settings | main | scenario:prod-admin-admin-dashboard-settings-footprint-achievements | prod-admin-admin-dashboard-settings-footprint-achievements | `apps/admin/app/dashboard/settings/footprint-achievements/page.tsx` |
| 已注册 | 市场参考运营台 | `dashboard/settings/market-intelligence` | settings | main | scenario:prod-admin-admin-dashboard-settings-market-intelligence | prod-admin-admin-dashboard-settings-market-intelligence | `apps/admin/app/dashboard/settings/market-intelligence/page.tsx` |
| 已注册 | 微信服务号通道健康位 | `dashboard/settings/notifications` | settings | main | scenario:prod-admin-admin-dashboard-settings-notifications | prod-admin-admin-dashboard-settings-notifications | `apps/admin/app/dashboard/settings/notifications/page.tsx` |
| 已注册 | 平台品牌 | `dashboard/settings/platform-branding` | settings | main | scenario:prod-admin-admin-dashboard-settings-platform-branding | prod-admin-admin-dashboard-settings-platform-branding | `apps/admin/app/dashboard/settings/platform-branding/page.tsx` |
| 已注册 | 套餐定价 | `dashboard/settings/pricing` | settings | main | scenario:prod-admin-admin-dashboard-settings-pricing | prod-admin-admin-dashboard-settings-pricing | `apps/admin/app/dashboard/settings/pricing/page.tsx` |
| 已注册 | 供给入口 | `dashboard/settings/supply` | settings | main | redirect:admin-dashboard-commerce-catalog | prod-admin-admin-dashboard-settings-supply | `apps/admin/app/dashboard/settings/supply/page.tsx` |
| 已注册 | 租户品牌 | `dashboard/settings/tenant-branding` | settings | main | scenario:prod-admin-admin-dashboard-settings-tenant-branding | prod-admin-admin-dashboard-settings-tenant-branding | `apps/admin/app/dashboard/settings/tenant-branding/page.tsx` |

## 主要关系

| From | To | 类型 | 触发 |
|---|---|---|---|
| 后台根入口 | 数据 | redirect | apps/admin/app/page.tsx:redirect |
| 数据 | 平台用户 | navigateTo | apps/admin/app/dashboard/page.tsx:href |
| 数据 | 审计记录 | navigateTo | apps/admin/app/dashboard/page.tsx:href |
| 数据 | 租户详情 | navigateTo | apps/admin/app/dashboard/page.tsx:href.template |
| 治理记录 | 审计记录 | redirect | apps/admin/app/dashboard/audit-logs/page.tsx:redirect |
| 账单跳转 | 付费看板 | redirect | apps/admin/app/dashboard/billing/page.tsx:redirect |
| 社区入口 | 社区 | redirect | apps/admin/app/dashboard/guiquan-management/page.tsx:redirect |
| 会员入口 | 平台用户 | redirect | apps/admin/app/dashboard/memberships/page.tsx:redirect |
| 平台用户 | 租户详情 | navigateTo | apps/admin/app/dashboard/tenant-management/page.tsx:router.push.template |
| 平台用户 | 租户详情 | navigateTo | apps/admin/app/dashboard/tenant-management/page.tsx:href.template |
| Tenants | 平台用户 | redirect | apps/admin/app/dashboard/tenants/page.tsx:redirect |
| 租户详情 | 平台用户 | navigateTo | apps/admin/app/dashboard/tenants/[tenantId]/page.tsx:router.push |
| 租户详情 | 平台用户 | navigateTo | apps/admin/app/dashboard/tenants/[tenantId]/page.tsx:href |
| 租户详情 | 审计记录 | navigateTo | apps/admin/app/dashboard/tenants/[tenantId]/page.tsx:href.template |
| 租户详情 | 宠物档案摘要 | navigateTo | apps/admin/app/dashboard/tenants/[tenantId]/page.tsx:href.template |
| 宠物档案摘要 | 租户详情 | navigateTo | apps/admin/app/dashboard/tenants/[tenantId]/livestock/page.tsx:href.template |
| 经营 | 商品目录 | redirect | apps/admin/app/dashboard/commerce/page.tsx:redirect |
| 设置入口 | 套餐定价 | redirect | apps/admin/app/dashboard/settings/page.tsx:redirect |
| 供给入口 | 商品目录 | redirect | apps/admin/app/dashboard/settings/supply/page.tsx:redirect |
| 数据 | 平台用户 | navigateTo | sidebar:config |
| 数据 | 商品目录 | navigateTo | sidebar:config |
| 数据 | 社区 | navigateTo | sidebar:config |
| 数据 | 平台品牌 | navigateTo | sidebar:config |
| 数据 | 平台用户 | navigateTo | top-tabs:config |
| 数据 | 经营 | navigateTo | top-tabs:config |
| 数据 | 平台品牌 | navigateTo | top-tabs:config |
| 经营 | 商品目录 | navigateTo | commerce-tabs:config |
| 经营 | 社区 | navigateTo | commerce-tabs:config |
| 经营 | 二级市场 | navigateTo | commerce-tabs:config |
| 经营 | 订单管理 | navigateTo | commerce-tabs:config |
| 经营 | 售后客服 | navigateTo | commerce-tabs:config |
| 经营 | 发货履约 | navigateTo | commerce-tabs:config |
| 设置入口 | 后台登录 | navigateTo | settings-tabs:router.replace |
| 设置入口 | 套餐定价 | navigateTo | settings-tabs:config |
| 设置入口 | 平台品牌 | navigateTo | settings-tabs:config |
| 设置入口 | 租户品牌 | navigateTo | settings-tabs:config |
| 设置入口 | 市场参考运营台 | navigateTo | settings-tabs:config |
| 设置入口 | 徽章分享素材 | navigateTo | settings-tabs:config |
| 设置入口 | 审计记录 | navigateTo | settings-tabs:config |
| 设置入口 | 微信服务号通道健康位 | navigateTo | settings-tabs:config |
| 数据 | 后台登录 | redirect | middleware:missing-session |
| 活跃度看板 | 后台登录 | redirect | middleware:missing-session |
| 治理记录 | 后台登录 | redirect | middleware:missing-session |
| 账单跳转 | 后台登录 | redirect | middleware:missing-session |
| 社区入口 | 后台登录 | redirect | middleware:missing-session |
| 用量看板 | 后台登录 | redirect | middleware:missing-session |
| 活跃度看板 | 后台登录 | redirect | middleware:missing-session |
| 付费看板 | 后台登录 | redirect | middleware:missing-session |
| 会员入口 | 后台登录 | redirect | middleware:missing-session |
| 平台用户 | 后台登录 | redirect | middleware:missing-session |
| Tenants | 后台登录 | redirect | middleware:missing-session |
| 租户详情 | 后台登录 | redirect | middleware:missing-session |
| 宠物档案摘要 | 后台登录 | redirect | middleware:missing-session |
| 经营 | 后台登录 | redirect | middleware:missing-session |
| 商品目录 | 后台登录 | redirect | middleware:missing-session |
| 社区 | 后台登录 | redirect | middleware:missing-session |
| 发货履约 | 后台登录 | redirect | middleware:missing-session |
| 二级市场 | 后台登录 | redirect | middleware:missing-session |
| 订单管理 | 后台登录 | redirect | middleware:missing-session |
| 售后客服 | 后台登录 | redirect | middleware:missing-session |
| 商品详情 | 后台登录 | redirect | middleware:missing-session |
| 新建商品 | 后台登录 | redirect | middleware:missing-session |
| 帖子详情 | 后台登录 | redirect | middleware:missing-session |
| 新建帖子 | 后台登录 | redirect | middleware:missing-session |
| 挂牌详情 | 后台登录 | redirect | middleware:missing-session |
| 设置入口 | 后台登录 | redirect | middleware:missing-session |
| 审计记录 | 后台登录 | redirect | middleware:missing-session |
| 徽章分享素材 | 后台登录 | redirect | middleware:missing-session |
| 市场参考运营台 | 后台登录 | redirect | middleware:missing-session |
| 微信服务号通道健康位 | 后台登录 | redirect | middleware:missing-session |
| 平台品牌 | 后台登录 | redirect | middleware:missing-session |
| 套餐定价 | 后台登录 | redirect | middleware:missing-session |
| 供给入口 | 后台登录 | redirect | middleware:missing-session |
| 租户品牌 | 后台登录 | redirect | middleware:missing-session |

## 冲突清单

- 当前未发现冲突。
