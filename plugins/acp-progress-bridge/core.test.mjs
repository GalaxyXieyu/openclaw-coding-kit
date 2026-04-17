import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCompletionBridgeMessage,
  buildProgressBridgeMessage,
  buildFallbackProgressText,
  collectChildAgentSelection,
  evaluateReplayDecision,
  evaluateSettleState,
  matchesAnyPrefix,
  normalizeConfig,
  pickAssistantTail,
  pruneTrackedRuns,
  readRelaySnapshotFromText,
  readTranscriptSnapshotFromText,
  stripBridgeNoise,
  summarizeDiscovery,
} from "./core.mjs";

test("normalizeConfig keeps multi-provider defaults", () => {
  const config = normalizeConfig({});
  assert.deepEqual(config.childSessionPrefixes, [
    "agent:codex:acp:",
    "agent:claude:acp:",
    "agent:claudecode:acp:",
    "agent:gemini:acp:",
    "agent:opencode:acp:",
    "agent:pi:acp:",
  ]);
  assert.equal(config.deliverProgress, true);
  assert.equal(config.deliverCompletion, true);
});

test("collectChildAgentSelection parses explicit agent ids and wildcard markers", () => {
  assert.deepEqual(
    collectChildAgentSelection(["agent:codex:acp:", "agent:claude:acp:", "agent:*:acp:"]),
    {
      agentIds: ["codex", "claude"],
      hasWildcard: true,
    },
  );
});

test("matchesAnyPrefix supports wildcard parent session prefixes", () => {
  assert.equal(matchesAnyPrefix("agent:main:feishu:group:abc", ["agent:*:feishu:group:"]), true);
  assert.equal(matchesAnyPrefix("agent:main:main", ["agent:*:main"]), true);
  assert.equal(matchesAnyPrefix("agent:other:web", ["agent:*:main"]), false);
});

test("summarizeDiscovery explains why a child session is or is not tracked", () => {
  assert.equal(
    summarizeDiscovery({
      childSessionKey: "agent:codex:acp:child-1",
      parentSessionKey: "agent:pm:main",
      childSessionPrefixes: ["agent:codex:acp:"],
      parentSessionPrefixes: ["agent:*:main"],
    }),
    "tracked",
  );
  assert.equal(
    summarizeDiscovery({
      childSessionKey: "agent:claude:acp:child-1",
      parentSessionKey: "agent:pm:main",
      childSessionPrefixes: ["agent:codex:acp:"],
      parentSessionPrefixes: ["agent:*:main"],
    }),
    "child-prefix-miss",
  );
  assert.equal(
    summarizeDiscovery({
      childSessionKey: "agent:claudecode:acp:child-1",
      parentSessionKey: "agent:pm:main",
      childSessionPrefixes: normalizeConfig({}).childSessionPrefixes,
      parentSessionPrefixes: ["agent:*:main"],
    }),
    "tracked",
  );
});

test("readRelaySnapshotFromText captures progress, done, and assistant tail", () => {
  const snapshot = readRelaySnapshotFromText(
    [
      JSON.stringify({ kind: "system_event", contextKey: "run:progress", text: "gemini: 正在整理改动", epochMs: 1000, runId: "run-1" }),
      JSON.stringify({ kind: "assistant_delta", delta: "前半段分析" }),
      JSON.stringify({ kind: "assistant_message", text: "**已改动**\n- 完成 bridge 回归测试" }),
      JSON.stringify({ kind: "system_event", contextKey: "run:done", epochMs: 2000 }),
    ].join("\n"),
    5000,
  );
  assert.equal(snapshot.runId, "run-1");
  assert.equal(snapshot.latestProgressText, "正在整理改动");
  assert.equal(snapshot.doneAt, 2000);
  assert.match(snapshot.assistantTail, /已改动/);
});

test("stripBridgeNoise removes supported provider labels", () => {
  assert.equal(stripBridgeNoise("claude: 正在分析"), "正在分析");
  assert.equal(stripBridgeNoise("claudecode: 正在改 UI"), "正在改 UI");
  assert.equal(stripBridgeNoise("gemini: 输出页面草图"), "输出页面草图");
});

test("readTranscriptSnapshotFromText prefers the final assistant message", () => {
  const snapshot = readTranscriptSnapshotFromText(
    [
      JSON.stringify({ type: "message", timestamp: "2026-04-07T10:00:00.000Z", message: { role: "user", content: "hello" } }),
      JSON.stringify({
        type: "message",
        timestamp: "2026-04-07T10:01:00.000Z",
        message: {
          role: "assistant",
          content: [{ type: "text", text: "前文" }, { type: "text", text: "**已完成**\n- bridge 已汇报" }],
        },
      }),
    ].join("\n"),
    5000,
  );
  assert.match(snapshot.assistantTail, /已完成/);
  assert.equal(snapshot.assistantTimestampMs, Date.parse("2026-04-07T10:01:00.000Z"));
});

test("bridge messages preserve internal markers and grounded payloads", () => {
  const progressMessage = buildProgressBridgeMessage({ childSessionKey: "agent:codex:acp:child-1", runId: "run-1" }, buildFallbackProgressText());
  assert.match(progressMessage, /\[\[acp_bridge_update\]\]/);
  assert.match(progressMessage, /kind: progress/);

  const completionMessage = buildCompletionBridgeMessage({
    childSessionKey: "agent:codex:acp:child-1",
    runId: "run-1",
    lastProgressText: "已完成修改",
    doneAt: 1234,
    assistantTail: "最终总结",
  });
  assert.match(completionMessage, /kind: done/);
  assert.match(completionMessage, /assistant_tail/);
  assert.match(completionMessage, /最终总结/);
});

test("pickAssistantTail prefers meaningful completion markers", () => {
  const tail = pickAssistantTail("前文\nSummary\n结果\n**已完成**\n- ok", 100);
  assert.match(tail, /已完成/);
});

test("evaluateReplayDecision skips stale completions discovered late", () => {
  const decision = evaluateReplayDecision({
    run: {
      doneAt: 10_000,
      discoveredAt: 400_000,
      completionHandled: false,
    },
    replayCompletedWithinMs: 300_000,
    pollIntervalMs: 3_000,
    nowMsValue: 400_500,
  });
  assert.equal(decision.markHandled, true);
  assert.match(decision.statusHint, /completion skipped replay/);
});

test("evaluateSettleState waits until settle window expires", () => {
  const waiting = evaluateSettleState({ doneAt: 10_000, settleAfterDoneMs: 4_000, nowMsValue: 12_000 });
  assert.equal(waiting.ready, false);
  assert.equal(waiting.remainingMs, 2_000);

  const ready = evaluateSettleState({ doneAt: 10_000, settleAfterDoneMs: 4_000, nowMsValue: 14_500 });
  assert.equal(ready.ready, true);
  assert.equal(ready.remainingMs, 0);
});

test("pruneTrackedRuns removes only stale runs", () => {
  const result = pruneTrackedRuns({
    runs: {
      keep: { discoveredAt: 1000, lastSeenAt: 99_000 },
      drop: { discoveredAt: 1000, completionHandledAt: 2_000 },
    },
    nowMsValue: 100_000,
    maxAgeMs: 10_000,
  });
  assert.deepEqual(Object.keys(result.nextRuns), ["keep"]);
  assert.deepEqual(result.removedKeys, ["drop"]);
});
