# Reporting Rules

`product-canvas` 当前沿用文件化 review 资产，避免在 phase 1 过早引入数据库。

## 资产结构

1. `01_scope.csv`
2. `02_coverage_matrix.csv`
3. `03_test_cases.csv`
4. `04_execution_log.csv`
5. `05_bug_list.csv`
6. `06_summary.csv`

## Evidence Rules

- 每条执行记录都应该带 `evidence_path`
- 截图路径建议写进 `screenshot_path`
- 失败必须标 `failure_type`
- 优先把 scenario 结果路径写回 `04_execution_log.csv`

## 输出物

- Markdown 报告
- `result.json`
- screenshot
- board manifest 中的 `scenario_refs[]`

## 迁移边界

当前 phase 只要求：

- repo 内可初始化模板
- 执行后有结构化 JSON 结果
- 报告能消费 CSV 结果

SQLite、版本索引、跨项目检索留到下一阶段。
