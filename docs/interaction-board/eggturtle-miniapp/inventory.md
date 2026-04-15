# Interaction Board Inventory

- 生成时间：`2026-04-15T14:24:41+08:00`
- 项目：`Eggturtle-breeding-library`
- 已注册页面：`26`
- 候选页面：`0`
- 草稿节点：`0`
- 关系边：`93`
- 冲突项：`0`
- 有截图页面：`12`
- 截图快照：`29`
- 绑定场景节点：`6`
- 场景引用：`8`

## 页面矩阵

| 状态 | 标题 | 路由 | 分组 | 包 | 截图 | 场景 | 组件 |
|---|---|---|---|---|---|---|---|
| 已注册 | 选择空间 | `pages/workspace-entry/index` | entry | main | planned | n/a | `apps/miniapp/src/features/tenant/workspace-entry/screen.tsx` |
| 已注册 | 龟圈 | `pages/guiquan/index` | guiquan | main | guiquan, gq-compose, gq-detail | guiquan-to-community-detail | `apps/miniapp/src/features/guiquan/screen.tsx` |
| 已注册 | 社区详情 | `subpackages/workspace/pages/guiquan-community-detail/index` | guiquan | workspace | gq-detail | guiquan-to-community-detail | `apps/miniapp/src/features/guiquan/community-detail-screen.tsx` |
| 已注册 | 发帖 | `subpackages/workspace/pages/guiquan-compose/index` | guiquan | workspace | gq-compose, preview | n/a | `apps/miniapp/src/features/guiquan/community-compose-screen.tsx` |
| 已注册 | listing 详情 | `subpackages/workspace/pages/guiquan-marketplace-detail/index` | guiquan | workspace | planned | n/a | `apps/miniapp/src/features/guiquan/marketplace-detail-screen.tsx` |
| 已注册 | 租户市场 | `subpackages/workspace/pages/guiquan-marketplace/index` | guiquan | workspace | planned | n/a | `apps/miniapp/src/features/guiquan/marketplace-list-screen.tsx` |
| 已注册 | 拍卖进度 | `subpackages/workspace/pages/guiquan-seller-marketplace-detail/index` | guiquan | workspace | planned | n/a | `apps/miniapp/src/features/guiquan/marketplace-seller-detail-screen.tsx` |
| 已注册 | 我的拍卖 | `subpackages/workspace/pages/guiquan-seller-marketplace/index` | guiquan | workspace | planned | n/a | `apps/miniapp/src/features/guiquan/marketplace-seller-list-screen.tsx` |
| 已注册 | 收货地址 | `subpackages/workspace/pages/guiquan-supply-addresses/index` | guiquan | workspace | planned | n/a | `apps/miniapp/src/features/guiquan/supply-addresses-screen.tsx` |
| 已注册 | 补给购物车 | `subpackages/workspace/pages/guiquan-supply-cart/index` | guiquan | workspace | ui-ux-smoke | n/a | `apps/miniapp/src/features/guiquan/supply-cart-screen.tsx` |
| 已注册 | 商品详情 | `subpackages/workspace/pages/guiquan-supply-detail/index` | guiquan | workspace | planned | n/a | `apps/miniapp/src/features/guiquan/supply-detail-screen.tsx` |
| 已注册 | 补给订单 | `subpackages/workspace/pages/guiquan-supply-orders/index` | guiquan | workspace | ui-ux-smoke | n/a | `apps/miniapp/src/features/guiquan/supply-orders-screen.tsx` |
| 已注册 | 宠物档案 | `pages/products/index` | products | main | compare, style-pass2, style-pass3, weapp-smoke, weapp-fidelity | products-to-detail, products-to-footprint-tab, products-to-me-tab | `apps/miniapp/src/features/product/list/screen.tsx` |
| 已注册 | 宠物详情 | `subpackages/workspace/pages/product-detail/index` | products | workspace | planned | products-to-detail | `apps/miniapp/src/features/product/detail/screen.tsx` |
| 已注册 | 宠物编辑 | `subpackages/workspace/pages/product-editor/index` | products | workspace | planned | n/a | `apps/miniapp/src/features/product/editor/screen.tsx` |
| 已注册 | 快速记录 | `subpackages/workspace/pages/quick-record/index` | products | workspace | planned | n/a | `apps/miniapp/src/features/product/quick-record/screen.tsx` |
| 已注册 | 分享配置 | `subpackages/workspace/pages/share-config/index` | products | workspace | share-dialog | n/a | `apps/miniapp/src/features/tenant/share-config/screen.tsx` |
| 已注册 | 足迹 | `pages/series/index` | footprint | main | compare, weapp-smoke | products-to-footprint-tab | `apps/miniapp/src/features/series/screen.tsx` |
| 已注册 | 种龟详情 | `subpackages/workspace/pages/breeders/detail/index` | footprint | workspace | style-pass2, style-pass3, weapp-smoke | n/a | `apps/miniapp/src/features/breeder/detail/screen.tsx` |
| 已注册 | 勋章柜 | `subpackages/workspace/pages/footprint-badges/index` | footprint | workspace | planned | n/a | `apps/miniapp/src/subpackages/workspace/features/series/badges/screen.tsx` |
| 已注册 | 系列管理 | `subpackages/workspace/pages/series-manage/index` | footprint | workspace | planned | n/a | `apps/miniapp/src/features/series/manage-screen.tsx` |
| 已注册 | 我的 | `pages/me/index` | account | main | compare, style-pass2, weapp-fidelity | products-to-me-tab | `apps/miniapp/src/features/me/screen.tsx` |
| 已注册 | 证书中心 | `subpackages/workspace/pages/account-certificates/index` | account | workspace | planned | n/a | `apps/miniapp/src/features/me/certificates-screen.tsx` |
| 已注册 | 邀请中心 | `subpackages/workspace/pages/account-referral/index` | account | workspace | planned | n/a | `apps/miniapp/src/features/me/referral-screen.tsx` |
| 已注册 | 公开档案 | `subpackages/public/pages/share-detail/index` | public | public | style-pass3, public-smoke | n/a | `apps/miniapp/src/features/share/public-detail/screen.tsx` |
| 已注册 | 公开图鉴 | `subpackages/public/pages/share/index` | public | public | compare, style-pass2, style-pass3, weapp-smoke, public-smoke | n/a | `apps/miniapp/src/subpackages/public/features/share/public-feed/screen.tsx` |

## 主要关系

| From | To | 类型 | 触发 |
|---|---|---|---|
| 选择空间 | 宠物档案 | redirect | redirectToTarget:products |
| 龟圈 | 商品详情 | navigateTo | buildMiniappRoute:guiquan-supply-detail |
| 龟圈 | 发帖 | navigateTo | MINIAPP_PAGE_PATHS.guiquanCommunityCompose |
| 龟圈 | 种龟详情 | navigateTo | buildMiniappRoute:breeder-detail |
| 龟圈 | listing 详情 | navigateTo | buildMiniappRoute:guiquan-marketplace-detail |
| 龟圈 | 选择空间 | redirect | redirectToTarget:login |
| 龟圈 | 宠物档案 | redirect | MINIAPP_PAGE_PATHS.products |
| 龟圈 | 龟圈 | navigateTo | MINIAPP_PAGE_PATHS.guiquan |
| 龟圈 | 社区详情 | navigateTo | MINIAPP_PAGE_PATHS.guiquanCommunityDetail |
| 龟圈 | 种龟详情 | navigateTo | MINIAPP_PAGE_PATHS.breederDetail |
| 龟圈 | 补给购物车 | navigateTo | buildMiniappRoute:guiquan-supply-cart |
| 龟圈 | 补给订单 | navigateTo | buildMiniappRoute:guiquan-supply-orders |
| 龟圈 | 我的拍卖 | navigateTo | buildMiniappRoute:guiquan-seller-marketplace |
| 社区详情 | 龟圈 | navigateTo | MINIAPP_PAGE_PATHS.guiquan |
| 社区详情 | 选择空间 | redirect | redirectToTarget:login |
| 社区详情 | 宠物档案 | redirect | MINIAPP_PAGE_PATHS.products |
| 社区详情 | 社区详情 | navigateTo | MINIAPP_PAGE_PATHS.guiquanCommunityDetail |
| 社区详情 | 宠物详情 | navigateTo | MINIAPP_PAGE_PATHS.productDetail |
| 发帖 | 龟圈 | reLaunch | MINIAPP_PAGE_PATHS.guiquan |
| 发帖 | 社区详情 | navigateTo | MINIAPP_PAGE_PATHS.guiquanCommunityDetail |
| listing 详情 | 选择空间 | redirect | redirectToTarget:login |
| 租户市场 | 选择空间 | redirect | redirectToTarget:login |
| 租户市场 | listing 详情 | navigateTo | buildMiniappRoute:guiquan-marketplace-detail |
| 拍卖进度 | 选择空间 | redirect | redirectToTarget:login |
| 我的拍卖 | 选择空间 | redirect | redirectToTarget:login |
| 我的拍卖 | 拍卖进度 | navigateTo | buildMiniappRoute:guiquan-seller-marketplace-detail |
| 收货地址 | 选择空间 | redirect | redirectToTarget:login |
| 收货地址 | 宠物档案 | redirect | redirectToTarget:products |
| 收货地址 | 龟圈 | navigateTo | buildMiniappRoute:guiquan |
| 补给购物车 | 选择空间 | redirect | redirectToTarget:login |
| 补给购物车 | 宠物档案 | redirect | redirectToTarget:products |
| 补给购物车 | 龟圈 | navigateTo | buildMiniappRoute:guiquan |
| 补给购物车 | 收货地址 | navigateTo | buildMiniappRoute:guiquan-supply-addresses |
| 补给购物车 | 补给订单 | navigateTo | buildMiniappRoute:guiquan-supply-orders |
| 商品详情 | 选择空间 | redirect | redirectToTarget:login |
| 商品详情 | 宠物档案 | redirect | redirectToTarget:products |
| 商品详情 | 龟圈 | navigateTo | buildMiniappRoute:guiquan |
| 商品详情 | 补给购物车 | navigateTo | buildMiniappRoute:guiquan-supply-cart |
| 商品详情 | 收货地址 | navigateTo | buildMiniappRoute:guiquan-supply-addresses |
| 商品详情 | 补给订单 | navigateTo | buildMiniappRoute:guiquan-supply-orders |
| 补给订单 | 选择空间 | redirect | redirectToTarget:login |
| 补给订单 | 宠物档案 | redirect | redirectToTarget:products |
| 补给订单 | 龟圈 | navigateTo | buildMiniappRoute:guiquan |
| 宠物档案 | 宠物详情 | navigateTo | MINIAPP_PAGE_PATHS.productDetail |
| 宠物档案 | 选择空间 | redirect | redirectToTarget:login |
| 宠物档案 | 宠物编辑 | navigateTo | MINIAPP_PAGE_PATHS.productEditor |
| 宠物档案 | 分享配置 | navigateTo | MINIAPP_PAGE_PATHS.shareConfig |
| 宠物档案 | 宠物档案 | reLaunch | MINIAPP_PAGE_PATHS.products |
| 宠物档案 | 快速记录 | navigateTo | buildMiniappRoute:quick-record |
| 宠物详情 | 种龟详情 | navigateTo | MINIAPP_PAGE_PATHS.breederDetail |
| 宠物详情 | 宠物详情 | navigateTo | MINIAPP_PAGE_PATHS.productDetail |
| 宠物详情 | 宠物档案 | navigateTo | MINIAPP_PAGE_PATHS.products |
| 宠物详情 | 宠物编辑 | navigateTo | MINIAPP_PAGE_PATHS.productEditor |
| 宠物详情 | 分享配置 | navigateTo | MINIAPP_PAGE_PATHS.shareConfig |
| 宠物编辑 | 种龟详情 | reLaunch | buildMiniappRoute:breeder-detail |
| 宠物编辑 | 宠物档案 | reLaunch | MINIAPP_PAGE_PATHS.products |
| 宠物编辑 | 宠物档案 | reLaunch | buildMiniappRoute:products |
| 宠物编辑 | 种龟详情 | navigateTo | MINIAPP_PAGE_PATHS.breederDetail |
| 宠物编辑 | 宠物详情 | navigateTo | MINIAPP_PAGE_PATHS.productDetail |
| 快速记录 | 足迹 | navigateTo | buildMiniappRoute:footprint |
| 快速记录 | 种龟详情 | navigateTo | buildMiniappRoute:breeder-detail |
| 快速记录 | 宠物档案 | navigateTo | MINIAPP_PAGE_PATHS.products |
| 快速记录 | 宠物编辑 | navigateTo | buildMiniappRoute:product-editor |
| 快速记录 | 宠物编辑 | navigateTo | MINIAPP_PAGE_PATHS.productEditor |
| 足迹 | 选择空间 | redirect | redirectToTarget:login |
| 足迹 | 足迹 | navigateTo | MINIAPP_PAGE_PATHS.footprint |
| 足迹 | 宠物档案 | navigateTo | buildMiniappRoute:products |
| 足迹 | 勋章柜 | navigateTo | MINIAPP_PAGE_PATHS.footprintBadges |
| 足迹 | 我的 | navigateTo | buildMiniappRoute:me |
| 足迹 | 系列管理 | navigateTo | MINIAPP_PAGE_PATHS.seriesManage |
| 种龟详情 | 种龟详情 | navigateTo | MINIAPP_PAGE_PATHS.breederDetail |
| 种龟详情 | 宠物档案 | navigateTo | MINIAPP_PAGE_PATHS.products |
| 种龟详情 | 选择空间 | redirect | redirectToTarget:login |
| 种龟详情 | 宠物编辑 | navigateTo | buildMiniappRoute:product-editor |
| 种龟详情 | 分享配置 | navigateTo | MINIAPP_PAGE_PATHS.shareConfig |
| 种龟详情 | 快速记录 | navigateTo | buildMiniappRoute:quick-record |
| 勋章柜 | 选择空间 | redirect | redirectToTarget:login |
| 勋章柜 | 勋章柜 | navigateTo | MINIAPP_PAGE_PATHS.footprintBadges |
| 系列管理 | 选择空间 | redirect | redirectToTarget:login |
| 系列管理 | 宠物档案 | navigateTo | buildMiniappRoute:products |
| 我的 | 选择空间 | redirect | redirectToTarget:login |
| 我的 | 邀请中心 | navigateTo | MINIAPP_PAGE_PATHS.accountReferral |
| 我的 | 证书中心 | navigateTo | MINIAPP_PAGE_PATHS.accountCertificates |
| 我的 | 宠物档案 | redirect | redirectToTarget:products |
| 我的 | 收货地址 | navigateTo | MINIAPP_PAGE_PATHS.guiquanSupplyAddresses |
| 证书中心 | 选择空间 | redirect | redirectToTarget:login |
| 邀请中心 | 选择空间 | redirect | redirectToTarget:login |
| 邀请中心 | 邀请中心 | navigateTo | MINIAPP_PAGE_PATHS.accountReferral |
| 公开档案 | 宠物档案 | reLaunch | MINIAPP_PAGE_PATHS.defaultPrivateLanding |
| 公开图鉴 | 选择空间 | navigateTo | MINIAPP_PAGE_PATHS.login |
| 公开图鉴 | 宠物档案 | reLaunch | MINIAPP_PAGE_PATHS.defaultPrivateLanding |
| 公开图鉴 | 宠物档案 | reLaunch | MINIAPP_PAGE_PATHS.products |
| 公开图鉴 | 选择空间 | reLaunch | MINIAPP_PAGE_PATHS.login |

## 冲突清单

- 当前未发现冲突。
