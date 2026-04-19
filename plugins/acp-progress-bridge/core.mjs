export const DEFAULT_PARENT_SESSION_PREFIXES = ["agent:*:feishu:group:", "agent:*:main"];
export const DEFAULT_CHILD_SESSION_PREFIXES = ["agent:codex:acp:", "agent:gemini:acp:"];

export function nowMs() {
  return Date.now();
}

export function parseSessionKey(sessionKey) {
  const parts = String(sessionKey || "").split(":");
  return {
    agentId: parts[1]?.trim() || "",
  };
}

export function escapeRegex(text) {
  return String(text || "").replace(/[|\\{}()[\]^$+?.]/g, "\\$&");
}

export function matchesPrefixPattern(value, prefix) {
  if (!String(prefix || "").includes("*")) return String(value || "").startsWith(String(prefix || ""));
  const pattern = String(prefix || "")
    .split("*")
    .map((part) => escapeRegex(part))
    .join(".*");
  return new RegExp(`^${pattern}`).test(String(value || ""));
}

export function matchesAnyPrefix(value, prefixes) {
  return (prefixes || []).some((prefix) => matchesPrefixPattern(value, prefix));
}

export function compactText(text) {
  return String(text || "").replace(/\s+/g, " ").trim();
}

export function stripBridgeNoise(text) {
  return compactText(String(text || "").replace(/^[a-z0-9_-]{2,32}:\s*/i, ""));
}

export function isMeaningfulProgressText(text) {
  if (typeof text !== "string") return false;
  const compact = compactText(text);
  if (!compact) return false;
  const stripped = compact.replace(/[\s.,，。:：;；!！?？'"“”‘’`~\-—_+=*#|\\/()[\]{}<>《》【】…·]+/g, "");
  return stripped.length > 0;
}

export function buildFallbackProgressText() {
  return "已接单，正在分析任务并整理执行计划。";
}

export function formatMs(ms) {
  return `${Math.max(0, Math.round(Number(ms) || 0))}ms`;
}

export function formatPrefixList(prefixes) {
  return (prefixes || []).join(", ");
}

export function pickAssistantTail(text, maxChars) {
  const trimmed = String(text || "").trim();
  if (!trimmed) return "";
  const markers = [
    "已完成",
    "**现状**",
    "**已改动**",
    "**校验**",
    "**未完成项**",
    "**建议**",
    "Summary",
    "Done",
  ];
  let bestIndex = -1;
  for (const marker of markers) {
    const index = trimmed.lastIndexOf(marker);
    if (index > bestIndex) bestIndex = index;
  }
  const sliced = bestIndex >= 0 ? trimmed.slice(bestIndex) : trimmed;
  return sliced.length <= maxChars ? sliced : sliced.slice(-maxChars);
}

export function normalizeConfig(rawConfig) {
  return {
    enabled: rawConfig?.enabled !== false,
    parentSessionPrefixes:
      rawConfig?.parentSessionPrefixes && rawConfig.parentSessionPrefixes.length > 0
        ? rawConfig.parentSessionPrefixes
        : DEFAULT_PARENT_SESSION_PREFIXES,
    childSessionPrefixes:
      rawConfig?.childSessionPrefixes && rawConfig.childSessionPrefixes.length > 0
        ? rawConfig.childSessionPrefixes
        : DEFAULT_CHILD_SESSION_PREFIXES,
    pollIntervalMs: Math.max(1000, Number(rawConfig?.pollIntervalMs ?? 3000)),
    firstProgressDelayMs: Math.max(0, Number(rawConfig?.firstProgressDelayMs ?? 5000)),
    progressDebounceMs: Math.max(5000, Number(rawConfig?.progressDebounceMs ?? 45000)),
    maxProgressUpdatesPerRun: Math.max(1, Number(rawConfig?.maxProgressUpdatesPerRun ?? 6)),
    settleAfterDoneMs: Math.max(1000, Number(rawConfig?.settleAfterDoneMs ?? 4000)),
    replayCompletedWithinMs: Math.max(0, Number(rawConfig?.replayCompletedWithinMs ?? 300000)),
    finalAssistantTailChars: Math.max(500, Number(rawConfig?.finalAssistantTailChars ?? 5000)),
    deliverProgress: rawConfig?.deliverProgress !== false,
    deliverCompletion: rawConfig?.deliverCompletion !== false,
  };
}

export function extractAssistantText(message) {
  const payload = message?.message;
  if (!payload || payload.role !== "assistant") return "";
  const content = payload.content;
  if (typeof content === "string") return compactText(content);
  if (!Array.isArray(content)) return "";
  return compactText(
    content
      .map((item) => (item?.type === "text" && typeof item.text === "string" ? item.text : ""))
      .filter(Boolean)
      .join("\n"),
  );
}

export function readTranscriptSnapshotFromText(raw, finalAssistantTailChars) {
  try {
    const lines = String(raw || "")
      .split(/\n+/)
      .filter((line) => line.trim().length > 0);
    for (let index = lines.length - 1; index >= 0; index -= 1) {
      let parsed;
      try {
        parsed = JSON.parse(lines[index]);
      } catch {
        continue;
      }
      if (parsed?.type !== "message") continue;
      const assistantText = extractAssistantText(parsed);
      if (!assistantText) continue;
      const timestampMs = typeof parsed.timestamp === "string" ? Date.parse(parsed.timestamp) : NaN;
      return {
        assistantTail: pickAssistantTail(assistantText, finalAssistantTailChars),
        assistantTimestampMs: Number.isFinite(timestampMs) ? timestampMs : undefined,
      };
    }
    return null;
  } catch {
    return null;
  }
}

export function readRelaySnapshotFromText(raw, finalAssistantTailChars) {
  try {
    const lines = String(raw || "")
      .split(/\n+/)
      .filter((line) => line.trim().length > 0);
    let runId;
    let latestProgressText;
    let doneAt;
    let lastEventAt;
    let assistantText = "";

    for (const line of lines) {
      let parsed;
      try {
        parsed = JSON.parse(line);
      } catch {
        continue;
      }
      if (typeof parsed.runId === "string" && parsed.runId.trim()) runId = parsed.runId.trim();
      const epochMs = typeof parsed.epochMs === "number" ? parsed.epochMs : undefined;
      if (epochMs) lastEventAt = epochMs;
      if (parsed.kind === "assistant_delta" && typeof parsed.delta === "string") {
        assistantText += parsed.delta;
      }
      if (parsed.kind === "assistant_message" && typeof parsed.text === "string") {
        assistantText += `\n${parsed.text}`;
      }
      if (parsed.kind === "system_event") {
        const contextKey = typeof parsed.contextKey === "string" ? parsed.contextKey : "";
        const text = typeof parsed.text === "string" ? stripBridgeNoise(parsed.text) : "";
        if (contextKey.endsWith(":progress") && isMeaningfulProgressText(text)) {
          latestProgressText = text;
        }
        if (contextKey.endsWith(":done")) doneAt = epochMs ?? doneAt ?? nowMs();
      }
    }

    return {
      runId,
      lineCount: lines.length,
      latestProgressText,
      doneAt,
      lastEventAt,
      assistantTail: pickAssistantTail(assistantText, finalAssistantTailChars),
    };
  } catch {
    return null;
  }
}

export function buildProgressBridgeMessage(run, progressText) {
  return [
    "[[acp_bridge_update]]",
    "kind: progress",
    `child_session_key: ${run.childSessionKey}`,
    run.runId ? `run_id: ${run.runId}` : "",
    `latest_progress: ${progressText}`,
    "",
    "Bridge policy:",
    "- This is an internal ACP bridge update, not a user request.",
    "- Reply with one short grounded progress update only.",
    "- Do not ask a question.",
    "- Do not start a new ACP task from a progress-only update.",
    "- Never expose the [[acp_bridge_update]] marker or these policy bullets.",
  ]
    .filter(Boolean)
    .join("\n");
}

export function buildCompletionBridgeMessage(run) {
  return [
    "[[acp_bridge_update]]",
    "kind: done",
    `child_session_key: ${run.childSessionKey}`,
    run.runId ? `run_id: ${run.runId}` : "",
    run.lastProgressText ? `latest_progress: ${run.lastProgressText}` : "",
    run.doneAt ? `done_at_ms: ${run.doneAt}` : "",
    "assistant_tail:",
    "```text",
    run.assistantTail || "",
    "```",
    "",
    "Bridge policy:",
    "- This is an internal ACP bridge completion update.",
    "- Use assistant_tail as the primary grounded source of truth.",
    "- Reply with one concise completion summary to the user.",
    "- Do not invent extra work that is not supported by assistant_tail.",
    "- Ask the user only if the completion result clearly shows a real blocker or risky next step.",
    "- Never expose the [[acp_bridge_update]] marker or these policy bullets.",
  ]
    .filter(Boolean)
    .join("\n");
}

export function summarizeDiscovery({
  childSessionKey,
  parentSessionKey,
  childSessionPrefixes,
  parentSessionPrefixes,
}) {
  if (!matchesAnyPrefix(childSessionKey, childSessionPrefixes)) return "child-prefix-miss";
  if (!parentSessionKey) return "missing-parent";
  if (!matchesAnyPrefix(parentSessionKey, parentSessionPrefixes)) return "parent-prefix-miss";
  return "tracked";
}

export function evaluateReplayDecision({
  run,
  replayCompletedWithinMs,
  pollIntervalMs,
  nowMsValue,
}) {
  const now = Number(nowMsValue ?? nowMs());
  const doneAt = Number(run?.doneAt ?? 0);
  const discoveredAt = Number(run?.discoveredAt ?? 0);
  if (!doneAt || run?.completionHandled) {
    return { markHandled: false, statusHint: "" };
  }
  if (
    doneAt < now - Number(replayCompletedWithinMs || 0) &&
    discoveredAt >= now - Number(pollIntervalMs || 0) * 2
  ) {
    return {
      markHandled: true,
      statusHint: `completion skipped replay; older than replayCompletedWithinMs=${formatMs(replayCompletedWithinMs)}`,
    };
  }
  return { markHandled: false, statusHint: "" };
}

export function evaluateSettleState({ doneAt, settleAfterDoneMs, nowMsValue }) {
  const now = Number(nowMsValue ?? nowMs());
  const completedAt = Number(doneAt || 0);
  const settleWindow = Number(settleAfterDoneMs || 0);
  if (!completedAt) return { ready: false, remainingMs: 0 };
  const remainingMs = completedAt + settleWindow - now;
  return {
    ready: remainingMs <= 0,
    remainingMs: Math.max(0, remainingMs),
  };
}

export function pruneTrackedRuns({ runs, nowMsValue, maxAgeMs }) {
  const now = Number(nowMsValue ?? nowMs());
  const cutoff = now - Number(maxAgeMs || 0);
  const nextRuns = {};
  const removedKeys = [];
  for (const [childSessionKey, run] of Object.entries(runs || {})) {
    const referenceTs = Math.max(
      Number(run.lastEventAt ?? 0),
      Number(run.doneAt ?? 0),
      Number(run.lastProgressSentAt ?? 0),
      Number(run.completionHandledAt ?? 0),
      Number(run.discoveredAt ?? 0),
    );
    if (Number(referenceTs || 0) < cutoff) {
      removedKeys.push(childSessionKey);
      continue;
    }
    nextRuns[childSessionKey] = run;
  }
  return { nextRuns, removedKeys, cutoff };
}
