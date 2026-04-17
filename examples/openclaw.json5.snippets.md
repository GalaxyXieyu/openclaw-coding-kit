# `openclaw.json` 配置片段

这个文件按“最小配置”和“可选增强”拆开。

不要把所有片段一次性照抄进真实配置。推荐顺序是：

1. 先使用最小 OpenClaw 片段
2. 本地验证通过后，再按需追加 progress bridge
3. 最后再追加 Feishu `bindings/channels`

路径相关说明：

- `workspace` 必须替换成当前机器上的绝对路径
- Windows JSON 里如果写反斜杠，需要转义成 `C:\\path\\to\\workspace`
- Windows 也可以直接写成 `C:/path/to/workspace`
- 如果 CLI 不在 PATH，可以改用环境变量 `OPENCLAW_BIN`、`CODEX_BIN`、`GSD_TOOLS_PATH`

## 片段 A：最小 OpenClaw 接入

```json
{
  "acp": {
    "enabled": true,
    "dispatch": {
      "enabled": true
    },
    "backend": "acpx",
    "defaultAgent": "codex",
    "allowedAgents": ["codex", "claude", "opencode", "gemini", "pi"],
    "maxConcurrentSessions": 8
  },
  "agents": {
    "list": [
      {
        "id": "your-agent-id",
        "name": "your-agent-id",
        "workspace": "REPLACE_WITH_ABSOLUTE_WORKSPACE_PATH",
        "skills": ["pm", "coder"]
      }
    ]
  }
}
```

这一步必改：

- `your-agent-id`
- `REPLACE_WITH_ABSOLUTE_WORKSPACE_PATH`

## 片段 B：可选启用 `acp-progress-bridge`

只有在你需要自动进度回推和完成汇报时，才追加这段：

```json
{
  "plugins": {
    "entries": {
      "acp-progress-bridge": {
        "enabled": true,
        "config": {
          "enabled": true,
          "parentSessionPrefixes": [
            "agent:*:feishu:group:",
            "agent:*:main"
          ],
          "childSessionPrefixes": [
            "agent:codex:acp:",
            "agent:claude:acp:",
            "agent:claudecode:acp:",
            "agent:gemini:acp:",
            "agent:opencode:acp:",
            "agent:pi:acp:"
          ],
          "pollIntervalMs": 3000,
          "firstProgressDelayMs": 5000,
          "progressDebounceMs": 45000,
          "maxProgressUpdatesPerRun": 6,
          "settleAfterDoneMs": 4000,
          "replayCompletedWithinMs": 300000,
          "finalAssistantTailChars": 5000,
          "deliverProgress": true,
          "deliverCompletion": true
        }
      }
    }
  }
}
```

如果你现在只做本地无鉴权验证，这段可以完全跳过。

当前推荐契约是：

- 默认子会话作用域：`agent:codex:acp:`、`agent:claude:acp:`、`agent:claudecode:acp:`、`agent:gemini:acp:`、`agent:opencode:acp:`、`agent:pi:acp:`
- 默认父会话作用域：`agent:*:feishu:group:` 和 `agent:*:main`
- 默认行为模型：plugin 只回推内部 `[[acp_bridge_update]]`，真正对用户可见的话术仍由父会话生成

按配置面理解：

### 作用域

- `parentSessionPrefixes`：哪些父会话允许接收 bridge 内部更新
- `childSessionPrefixes`：哪些 ACP 子会话会被观察
- 默认已覆盖常见 ACP provider，但“被观察”不等于“所有 provider 都已做过同等级生产验证”

### 节流

- `pollIntervalMs`：扫描 session store 和 stream 的轮询间隔
- `firstProgressDelayMs`：首次 progress 至少等待多久再发
- `progressDebounceMs`：同一 run 两次 progress 之间至少间隔多久
- `maxProgressUpdatesPerRun`：一个 run 最多发多少次 progress

### 完成策略

- `settleAfterDoneMs`：看到 done 后再等一小段时间，给 transcript 和 assistant tail 落稳
- `replayCompletedWithinMs`：插件晚发现已完成 run 时，只在窗口内尝试补发 completion；太旧的 run 直接标记 handled
- `finalAssistantTailChars`：completion 内附带多少 assistant 尾部摘要素材
- `deliverProgress` / `deliverCompletion`：是否真的把 progress / completion 回推给父会话

什么时候需要改这段：

- 只做本地 main session 验证：通常不用改前缀
- 需要接真实 Feishu 群：保留默认 `parentSessionPrefixes`，再补 `bindings/channels`
- 需要自定义 provider：再显式扩展 `childSessionPrefixes`

## 片段 C：可选 Feishu `bindings/channels`

只有在你已经准备好真实 Feishu 群和绑定信息时，才追加这段：

```json
{
  "bindings": [
    {
      "agentId": "your-agent-id",
      "match": {
        "channel": "feishu",
        "peer": {
          "kind": "group",
          "id": "oc_xxx"
        }
      }
    }
  ],
  "channels": {
    "feishu": {
      "groups": {
        "oc_xxx": {
          "requireMention": false
        }
      }
    }
  }
}
```

这一步必改：

- `your-agent-id`
- `oc_xxx`

这不是最小安装前置。

## 路径替换示例

- macOS / Linux: `/Users/you/workspaces/openclaw-demo`
- Windows: `C:\\Users\\you\\workspaces\\openclaw-demo`
- Windows 也可写成: `C:/Users/you/workspaces/openclaw-demo`

## 多 agent 进度回传示例

如果还想让自定义 agent 一起参与 bridge 观察，可以把 `childSessionPrefixes` 扩成：

```json
{
  "childSessionPrefixes": [
    "agent:codex:acp:",
    "agent:claude:acp:",
    "agent:claudecode:acp:",
    "agent:gemini:acp:",
    "agent:opencode:acp:",
    "agent:your-custom-agent:acp:"
  ]
}
```

但这只表示“prefix 层面允许发现这些子会话”，前提仍然是：

- 这些 provider 走的是 ACP 子会话
- stream 里也会产出兼容的 `:progress` / `:done` 事件
- 父会话对 `[[acp_bridge_update]]` 的自然语言转译策略仍然合适
