# UI/UX Review Playbook (Generic)

更新日期: 2026-02-28

## 1. 目标

定义一套不依赖项目、不依赖 agent 的 UI/UX 定向验证方法，覆盖完整闭环：

1. 验证路径规划（如何覆盖整个项目）
2. 验证资产组织（Excel/CSV 多表）
3. 执行期更新规则（如何持续回填）
4. 报告产出（如何生成带截图 Markdown）

## 2. 覆盖规划方法

### 2.1 路径盘点

按“端 + 角色 + 模块”列出核心路径：

- 端：Web / Admin / Public
- 角色：匿名 / 普通用户 / 管理员 / 超管
- 模块：登录、浏览、写操作、高风险操作、公开链路

### 2.2 风险维度

每个模块至少覆盖 6 个维度：

- `Critical Flow`
- `Permission`
- `Data Integrity`
- `Error Recovery`
- `Responsive`
- `Observability`

### 2.3 覆盖判定

“覆盖整个项目”按覆盖矩阵判定，不按用例数量判定。

## 3. Excel/CSV 结构（6 张表）

1. `01_scope.csv`：范围与边界
2. `02_coverage_matrix.csv`：模块 x 风险维度
3. `03_test_cases.csv`：用例定义
4. `04_execution_log.csv`：执行结果与证据
5. `05_bug_list.csv`：缺陷清单
6. `06_summary.csv`：汇总与门禁

模板目录：`assets/templates/`

## 4. 执行更新规则

### 执行前

- 填写 `01_scope` `02_coverage_matrix` `03_test_cases`
- 确认 `run_id`
- 可先跑预检：

```bash
bash skills/project-review/scripts/uiux_preflight.sh --web-url <web_login_url> --admin-url <admin_login_url> --api-health-url <api_health_url>
```

### 执行中

- 每跑完 1 条就回填 `04_execution_log.csv`
- `result` 只能是：`PASS/FAIL/BLOCKED/NOT_RUN`
- 失败必须标：`PRODUCT/ENV/GAP`
- 每条必须有 `evidence_path`，截图写在 `screenshot_path`

### 执行后

- FAIL/BLOCKED 同步到 `05_bug_list.csv`
- 汇总写入 `06_summary.csv`
- 生成报告并回填任务系统

## 5. 图文报告生成

```bash
node skills/project-review/scripts/generate_uiux_report.js \
  --execution-csv out/project-review/ui-ux/<run_id>/04_execution_log.csv \
  --bugs-csv out/project-review/ui-ux/<run_id>/05_bug_list.csv \
  --output out/project-review/ui-ux/<run_id>/ui-ux-review-report-<run_id>.md \
  --title "UI/UX 定向验证报告 - <project>" \
  --project <project> \
  --run-id <run_id>
```

报告包含：

- 总体通过情况与门禁结论
- 失败/阻塞明细
- 缺陷表
- 全量结果表
- 截图引用（Markdown image）

## 6. 跨项目复用

- Skill 主体不变
- 新项目只新增 `references/profile.<project>.yaml`
- 通过 profile 或脚本参数注入项目差异

## 7. 跨 agent 协作

- OpenClaw：浏览器执行 + 截图
- Codex：报告生成 + 台账回填
- 其他 agent：只要遵守 CSV 契约即可接入
