# Project Review LLM Review Orchestration

## 核心原则

`project-review` 不应该只靠规则直接下结论。

更稳的做法是参考 GSD 的 verifier / checker 模式：

1. **规则层先收证据**
2. **LLM reviewer 再做判断**
3. **结果必须结构化返回**
4. **state store 负责缓存和去重**

这和 GSD 里 “orchestrator -> checker/verifier agent -> structured output -> writeback” 的思路是一致的。

## 为什么不能只靠规则

规则适合做这些事：

- 有没有改代码但没改 docs
- 有没有缺测试
- 有没有长文件 / 长函数
- 有没有 API 改动

但下面这些单靠规则很容易不准：

- docs 是不是语义漂移
- `AGENTS.md` 和真实流程是不是冲突
- 两个工具是不是其实功能重复
- 某份文档是不是应该删

这些要让 reviewer 型 LLM 来判断。

## 推荐架构

### 1. collector

由本地脚本负责：

- `code_review_lane.py`
- `docs_review_lane.py`

职责：

- 缩范围
- 收证据
- 产出候选 findings / flags
- 不把候选当最终真相

### 2. review_llm_adapter

负责把 collector 结果组装成 reviewer request：

- lane 名称
- changed files
- commit 摘要
- 候选 findings / flags
- 文档片段
- 代码片段
- 严格 JSON schema

职责：

- prompt 构造
- response 解析
- verdict 规范化

当前实现里，这一层由：

- `scripts/review_llm_adapter.py`
- `scripts/review_orchestrator.py`

配合完成。

### 3. reviewer worker / subagent

由外部 orchestrator 调用 LLM：

- 可以是 Codex 子 agent
- 可以是 OpenClaw agent
- 也可以是未来独立的 reviewer runtime

职责：

- 读取 adapter 给的结构化 request
- 按 schema 返回 verdict

### 4. state store

负责：

- 缓存本轮输入 hash
- 缓存 reviewer verdict
- 记录 prompt version / model / review_id
- 记录 callback 后状态

## reviewer 返回格式

必须要求 reviewer 返回严格 JSON。

推荐结构：

```json
{
  "lane": "docs-review",
  "summary": "docs 有 2 处明显漂移",
  "findings": [
    {
      "severity": "P1",
      "title": "接口文档没同步",
      "summary": "代码里返回字段变了，docs 还是旧字段",
      "file": "docs/api.md",
      "evidence": [
        "src/api/home.ts",
        "docs/api.md"
      ],
      "suggestion": "更新字段说明"
    }
  ],
  "docs_flags": [
    "AGENTS.md 可能没同步"
  ]
}
```

## 合并策略

最终 bundle 里的结果应该是：

- `rule findings`
- `llm findings`
- 去重后的 merged findings

规则层更像：

- candidate detector
- evidence collector

LLM 层才是：

- semantic judge
- drift reviewer
- duplication reviewer

## 推荐执行顺序

### code-health

1. `commit_window`
2. `code_review_lane`
3. `docs_review_lane`
4. `review_orchestrator.py prepare` 生成 request 并写本地 draft state
5. reviewer worker / subagent 审核
6. `review_orchestrator.py ingest` 合并 verdict
7. `risk_card_builder`
8. `review_state_store`

### weekly / monthly

1. `project-retro`
2. 如有需要补 `graph-observe`
3. 如要深审，再用 reviewer 做一轮 summary tightening

## 当前落地方式

现在的落地方式是两段式：

1. `scripts/review_orchestrator.py prepare`
2. 外部 reviewer worker / subagent 执行审核
3. `scripts/review_orchestrator.py ingest`

示例：

```bash
python3 skills/project-review/scripts/review_orchestrator.py prepare \
  --payload @review-input.json \
  --model reviewer-mini
```

上一步会产出：

- `review_id`
- `reviewer_requests`
- `pending_llm_lanes`
- 本地 `.pm/project-review-state.json` draft 记录

reviewer worker 只需要读取 `reviewer_requests[*].request`，返回严格 JSON。

然后用：

```bash
python3 skills/project-review/scripts/review_orchestrator.py ingest \
  --review-id RV-xxxx \
  --payload @reviewer-output.json \
  --model reviewer-mini
```

这一步会：

- 解析 reviewer JSON
- 合并到 bundle
- 重建 card preview
- 更新本地 state 的 `llm_verdict` / `pending_llm_lanes` / `llm_ready`

现在也支持一条命令直接走完：

```bash
python3 skills/project-review/scripts/review_orchestrator.py codex \
  --payload @review-input.json \
  --model codex
```

这条命令会自动执行：

1. `prepare`
2. 用 `codex exec` 跑每个 pending reviewer lane
3. `ingest`
4. 输出合并后的 bundle / card 结果

## 实施约束

- 不让 Python 脚本自己直接决定“语义漂移真相”
- 不让 reviewer 直接扫全仓库
- 只给 reviewer 小而准的 evidence bundle
- reviewer 的返回必须结构化，可解析，可缓存

## 结论

`docs_review_lane.py` 和 `code_review_lane.py` 负责“发现可疑点”。

真正的“漂移是不是成立”“这个工具是不是重复”“这个文档是不是该删”，应该交给 reviewer 型 LLM worker。
