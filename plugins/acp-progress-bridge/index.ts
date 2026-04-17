import crypto from "node:crypto";
import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import {
  buildCompletionBridgeMessage,
  buildFallbackProgressText,
  buildProgressBridgeMessage,
  collectChildAgentSelection,
  compactText,
  DEFAULT_CHILD_AGENT_IDS,
  evaluateReplayDecision,
  evaluateSettleState,
  formatMs,
  formatPrefixList,
  isMeaningfulProgressText,
  matchesAnyPrefix,
  matchesPrefixPattern,
  normalizeConfig,
  nowMs,
  parseSessionKey,
  pickAssistantTail,
  pruneTrackedRuns,
  readRelaySnapshotFromText,
  readTranscriptSnapshotFromText,
  stripBridgeNoise,
} from "./core.mjs";

const execFileAsync = promisify(execFile);
const PLUGIN_ID = "acp-progress-bridge";
const CHILD_ENV_FLAG = "OPENCLAW_ACP_PROGRESS_BRIDGE_CHILD";
const STATE_VERSION = 1;
const DAY_MS = 24 * 60 * 60 * 1000;

type BridgeConfig = {
  enabled?: boolean;
  parentSessionPrefixes?: string[];
  childSessionPrefixes?: string[];
  pollIntervalMs?: number;
  firstProgressDelayMs?: number;
  progressDebounceMs?: number;
  maxProgressUpdatesPerRun?: number;
  settleAfterDoneMs?: number;
  replayCompletedWithinMs?: number;
  finalAssistantTailChars?: number;
  deliverProgress?: boolean;
  deliverCompletion?: boolean;
};

type SessionStoreEntry = {
  sessionId?: string;
  sessionFile?: string;
  spawnedBy?: string;
  updatedAt?: number;
  label?: string;
};

type RelaySnapshot = {
  runId?: string;
  lineCount: number;
  latestProgressText?: string;
  doneAt?: number;
  lastEventAt?: number;
  assistantTail?: string;
};

type TrackedRun = {
  childSessionKey: string;
  childAgentId: string;
  childSessionId?: string;
  sessionFile?: string;
  parentSessionKey: string;
  parentAgentId: string;
  parentSessionId?: string;
  streamPath: string;
  discoveredAt: number;
  processedLineCount: number;
  lastProgressText?: string;
  lastProgressSentText?: string;
  lastProgressSentAt?: number;
  progressCount: number;
  doneAt?: number;
  completionHandled?: boolean;
  completionHandledAt?: number;
  assistantTail?: string;
  runId?: string;
  lastEventAt?: number;
  lastSeenAt?: number;
  statusHint?: string;
};

type BridgeState = {
  version: number;
  runs: Record<string, TrackedRun>;
};

function sha1(text: string) {
  return crypto.createHash("sha1").update(text).digest("hex");
}

async function readJson(filePath: string) {
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch {
    return null;
  }
}

async function fileExists(filePath: string) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function ensureDir(dirPath: string) {
  await fs.mkdir(dirPath, { recursive: true });
}

async function loadState(stateFile: string): Promise<BridgeState> {
  const data = await readJson(stateFile);
  if (!data || typeof data !== "object") {
    return { version: STATE_VERSION, runs: {} };
  }
  const runs = data.runs && typeof data.runs === "object" ? data.runs : {};
  return { version: STATE_VERSION, runs };
}

async function saveState(stateFile: string, state: BridgeState) {
  await ensureDir(path.dirname(stateFile));
  await fs.writeFile(stateFile, JSON.stringify(state, null, 2) + "\n", "utf8");
}

async function loadSessionStore(
  stateDir: string,
  agentId: string,
): Promise<Record<string, SessionStoreEntry>> {
  const storePath = path.join(stateDir, "agents", agentId, "sessions", "sessions.json");
  const data = await readJson(storePath);
  if (!data || typeof data !== "object") return {};
  return data as Record<string, SessionStoreEntry>;
}

async function listKnownChildAgentIds(stateDir: string): Promise<string[]> {
  try {
    const entries = await fs.readdir(path.join(stateDir, "agents"), { withFileTypes: true });
    return entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name.trim()).filter(Boolean);
  } catch {
    return [];
  }
}

function resolveStreamPath(stateDir: string, agentId: string, entry: SessionStoreEntry) {
  const sessionFile = typeof entry.sessionFile === "string" ? entry.sessionFile : "";
  const sessionId = typeof entry.sessionId === "string" ? entry.sessionId.trim() : "";
  if (sessionFile.endsWith(".jsonl")) return sessionFile.replace(/\.jsonl$/, ".acp-stream.jsonl");
  if (!sessionId) return "";
  return path.join(stateDir, "agents", agentId, "sessions", `${sessionId}.acp-stream.jsonl`);
}

async function resolveParentSessionId(stateDir: string, parentSessionKey: string) {
  const { agentId } = parseSessionKey(parentSessionKey);
  if (!agentId) return undefined;
  const store = await loadSessionStore(stateDir, agentId);
  const entry = store[parentSessionKey];
  if (!entry || typeof entry.sessionId !== "string") return undefined;
  return entry.sessionId.trim() || undefined;
}

type TranscriptSnapshot = {
  assistantTail?: string;
  assistantTimestampMs?: number;
};

async function readTranscriptSnapshot(
  sessionFile: string,
  finalAssistantTailChars: number,
): Promise<TranscriptSnapshot | null> {
  try {
    return readTranscriptSnapshotFromText(await fs.readFile(sessionFile, "utf8"), finalAssistantTailChars);
  } catch {
    return null;
  }
}

async function readRelaySnapshot(
  streamPath: string,
  finalAssistantTailChars: number,
): Promise<RelaySnapshot | null> {
  try {
    return readRelaySnapshotFromText(await fs.readFile(streamPath, "utf8"), finalAssistantTailChars);
  } catch {
    return null;
  }
}

async function runAgentAutomation(params: {
  sessionId: string;
  agentId: string;
  message: string;
  deliver: boolean;
  thinking: "minimal" | "medium";
  timeoutSeconds: number;
}) {
  const cliEntry = process.argv[1]?.trim();
  if (!cliEntry) {
    throw new Error("OpenClaw CLI entrypoint is unavailable (process.argv[1] is empty).");
  }
  if (!(await fileExists(cliEntry))) {
    throw new Error(`OpenClaw CLI entrypoint is unavailable at ${cliEntry}.`);
  }
  const args = [
    cliEntry,
    "agent",
    "--session-id",
    params.sessionId,
    "--message",
    params.message,
    "--thinking",
    params.thinking,
    "--timeout",
    String(params.timeoutSeconds),
    "--json",
  ];
  if (params.deliver) args.push("--deliver");
  return await execFileAsync(process.execPath, args, {
    env: {
      ...process.env,
      [CHILD_ENV_FLAG]: "1",
    },
    maxBuffer: 2 * 1024 * 1024,
    timeout: (params.timeoutSeconds + 15) * 1000,
  });
}

function formatStatusSummary(
  state: BridgeState,
  config: ReturnType<typeof normalizeConfig>,
  discoverySummary: string,
) {
  const runs = Object.values(state.runs)
    .filter(
      (run) =>
        !run.completionHandled || (run.completionHandledAt ?? 0) > nowMs() - 6 * 60 * 60 * 1000,
    )
    .sort((left, right) => (right.lastSeenAt ?? right.discoveredAt) - (left.lastSeenAt ?? left.discoveredAt));

  if (runs.length === 0) {
    return [
      "ACP progress bridge is enabled.",
      `Scope: children=${formatPrefixList(config.childSessionPrefixes)} -> parents=${formatPrefixList(config.parentSessionPrefixes)}`,
      `Discovery: ${discoverySummary}`,
      "No recent tracked ACP child runs. Default contract watches common ACP providers; add custom child prefixes only for providers that emit compatible ACP progress/done events.",
    ].join("\n");
  }

  const lines = [
    "ACP progress bridge status:",
    `- scope: children=${formatPrefixList(config.childSessionPrefixes)} -> parents=${formatPrefixList(config.parentSessionPrefixes)}`,
    `- discovery: ${discoverySummary}`,
  ];
  for (const run of runs.slice(0, 8)) {
    const status = run.completionHandled ? "done" : run.doneAt ? "awaiting-finalization" : "running";
    const progress = run.lastProgressText ? ` · progress=${run.lastProgressText}` : "";
    const hint = run.statusHint ? ` · hint=${run.statusHint}` : "";
    lines.push(`- ${status} · child=${run.childSessionKey}${progress}${hint}`);
  }
  return lines.join("\n");
}

export default function register(api: any) {
  const config = normalizeConfig((api.pluginConfig?.config ?? api.pluginConfig ?? {}) as BridgeConfig);

  api.on(
    "before_tool_call",
    (
      event: { toolName?: string; params?: Record<string, unknown> },
      ctx?: { sessionKey?: string },
    ) => {
      if (event.toolName !== "sessions_send") return;
      const params = event.params ?? {};
      const sessionKey = typeof params.sessionKey === "string" ? params.sessionKey.trim() : "";
      if (!sessionKey) return;
      const callerSessionKey = typeof ctx?.sessionKey === "string" ? ctx.sessionKey.trim() : "";
      const isBridgeAcpContinue =
        callerSessionKey &&
        matchesAnyPrefix(callerSessionKey, config.parentSessionPrefixes) &&
        matchesAnyPrefix(sessionKey, config.childSessionPrefixes);
      let changed = false;
      const nextParams: Record<string, unknown> = { ...params };
      for (const key of ["label", "agentId"]) {
        if (key in nextParams) {
          delete nextParams[key];
          changed = true;
        }
      }
      if (isBridgeAcpContinue && nextParams.timeoutSeconds !== 0) {
        nextParams.timeoutSeconds = 0;
        changed = true;
      }
      if (!changed) return;
      const notes = ["stripped label/agentId"];
      if (isBridgeAcpContinue) notes.push("forced timeoutSeconds=0 for ACP bridge continue");
      api.logger.info(`[${PLUGIN_ID}] sanitized sessions_send params for ${sessionKey} (${notes.join("; ")})`);
      return { params: nextParams };
    },
    { priority: 100 },
  );

  const serviceDisabled = process.env[CHILD_ENV_FLAG] === "1";
  let timer: NodeJS.Timeout | null = null;
  let polling = false;
  let state: BridgeState = { version: STATE_VERSION, runs: {} };
  let stateFile = "";
  let stateDir = "";
  let discoverySummary = "not started";
  let lastDiscoveryLogLine = "";

  const logInfo = (message: string) => api.logger.info(`[${PLUGIN_ID}] ${message}`);
  const logWarn = (message: string) => api.logger.warn(`[${PLUGIN_ID}] ${message}`);
  const logError = (message: string) => api.logger.error(`[${PLUGIN_ID}] ${message}`);

  async function persistState() {
    if (!stateFile) return;
    await saveState(stateFile, state);
  }

  async function discoverRuns() {
    const summary = {
      scannedEntries: 0,
      trackedRuns: 0,
      newRuns: 0,
      childPrefixMisses: 0,
      missingParent: 0,
      parentPrefixMisses: 0,
      missingStreamPath: 0,
    };
    const selection = collectChildAgentSelection(config.childSessionPrefixes);
    const discoveredAgentIds = selection.hasWildcard ? await listKnownChildAgentIds(stateDir) : [];
    const agentIds = Array.from(
      new Set(
        [
          ...selection.agentIds,
          ...discoveredAgentIds,
          ...(selection.agentIds.length === 0 && discoveredAgentIds.length === 0 ? DEFAULT_CHILD_AGENT_IDS : []),
        ].filter(Boolean),
      ),
    );

    for (const agentId of agentIds) {
      const store = await loadSessionStore(stateDir, agentId);
      for (const [childSessionKey, entry] of Object.entries(store)) {
        summary.scannedEntries += 1;
        if (!matchesAnyPrefix(childSessionKey, config.childSessionPrefixes)) {
          summary.childPrefixMisses += 1;
          continue;
        }
        const parentSessionKey = typeof entry.spawnedBy === "string" ? entry.spawnedBy.trim() : "";
        if (!parentSessionKey) {
          summary.missingParent += 1;
          continue;
        }
        if (!matchesAnyPrefix(parentSessionKey, config.parentSessionPrefixes)) {
          summary.parentPrefixMisses += 1;
          continue;
        }

        const existing = state.runs[childSessionKey];
        const childAgentId = parseSessionKey(childSessionKey).agentId || agentId;
        const parentAgentId = parseSessionKey(parentSessionKey).agentId;
        const streamPath = resolveStreamPath(stateDir, childAgentId, entry);
        if (!streamPath) {
          summary.missingStreamPath += 1;
          continue;
        }

        if (!existing) {
          summary.newRuns += 1;
          logInfo(`tracked child session ${childSessionKey} -> parent ${parentSessionKey}`);
        }
        summary.trackedRuns += 1;

        state.runs[childSessionKey] = {
          childSessionKey,
          childAgentId,
          childSessionId:
            typeof entry.sessionId === "string" ? entry.sessionId.trim() : existing?.childSessionId,
          sessionFile:
            typeof entry.sessionFile === "string" ? entry.sessionFile.trim() : existing?.sessionFile,
          parentSessionKey,
          parentAgentId,
          parentSessionId: existing?.parentSessionId,
          streamPath,
          discoveredAt: existing?.discoveredAt ?? nowMs(),
          processedLineCount: existing?.processedLineCount ?? 0,
          lastProgressText: existing?.lastProgressText,
          lastProgressSentText: existing?.lastProgressSentText,
          lastProgressSentAt: existing?.lastProgressSentAt,
          progressCount: existing?.progressCount ?? 0,
          doneAt: existing?.doneAt,
          completionHandled: existing?.completionHandled,
          completionHandledAt: existing?.completionHandledAt,
          assistantTail: existing?.assistantTail,
          runId: existing?.runId,
          lastEventAt: existing?.lastEventAt,
          lastSeenAt: nowMs(),
          statusHint: existing?.statusHint ?? "discovered; awaiting ACP stream activity",
        };
      }
    }

    discoverySummary = [
      `scanned=${summary.scannedEntries}`,
      `tracked=${summary.trackedRuns}`,
      `new=${summary.newRuns}`,
      `child-prefix-miss=${summary.childPrefixMisses}`,
      `missing-parent=${summary.missingParent}`,
      `parent-prefix-miss=${summary.parentPrefixMisses}`,
      `missing-stream=${summary.missingStreamPath}`,
    ].join(" ");
    if (summary.newRuns > 0 || discoverySummary !== lastDiscoveryLogLine) {
      logInfo(`discovery summary: ${discoverySummary}`);
      lastDiscoveryLogLine = discoverySummary;
    }
  }

  async function updateRunSnapshot(run: TrackedRun) {
    let sawAnySnapshot = false;
    if (await fileExists(run.streamPath)) {
      const snapshot = await readRelaySnapshot(run.streamPath, config.finalAssistantTailChars);
      if (snapshot) {
        sawAnySnapshot = true;
        run.processedLineCount = snapshot.lineCount;
        run.runId = snapshot.runId ?? run.runId;
        run.lastEventAt = snapshot.lastEventAt ?? run.lastEventAt;
        run.lastSeenAt = nowMs();
        if (snapshot.latestProgressText) run.lastProgressText = snapshot.latestProgressText;
        if (snapshot.assistantTail) run.assistantTail = snapshot.assistantTail;
        if (snapshot.doneAt) run.doneAt = snapshot.doneAt;
        if (snapshot.latestProgressText) run.statusHint = "captured ACP progress update";
        if (snapshot.doneAt) run.statusHint = "completion detected; waiting for settle window";
      }
    }

    if (run.sessionFile && (await fileExists(run.sessionFile))) {
      const transcript = await readTranscriptSnapshot(run.sessionFile, config.finalAssistantTailChars);
      const transcriptDoneAt = transcript?.assistantTimestampMs;
      if (transcript) sawAnySnapshot = true;
      if (
        transcriptDoneAt &&
        transcriptDoneAt > (run.completionHandledAt ?? 0) &&
        transcriptDoneAt > (run.doneAt ?? 0)
      ) {
        run.assistantTail = transcript.assistantTail ?? run.assistantTail;
        run.doneAt = transcriptDoneAt;
        run.lastEventAt = Math.max(run.lastEventAt ?? 0, transcriptDoneAt);
        run.lastSeenAt = nowMs();
        run.completionHandled = false;
        run.completionHandledAt = undefined;
        run.statusHint = "transcript tail updated after completion";
      }
    }

    const replayDecision = evaluateReplayDecision({
      run,
      replayCompletedWithinMs: config.replayCompletedWithinMs,
      pollIntervalMs: config.pollIntervalMs,
    });
    if (replayDecision.markHandled) {
      run.completionHandled = true;
      run.completionHandledAt = nowMs();
      run.statusHint = replayDecision.statusHint;
    }

    if (!sawAnySnapshot) {
      run.statusHint = "waiting for stream/transcript files to update";
    }

    return sawAnySnapshot;
  }

  async function ensureParentSessionId(run: TrackedRun) {
    if (run.parentSessionId) return run.parentSessionId;
    run.parentSessionId = await resolveParentSessionId(stateDir, run.parentSessionKey);
    if (run.parentSessionId) {
      run.statusHint = `resolved parent sessionId for ${run.parentSessionKey}`;
    }
    return run.parentSessionId;
  }

  async function maybeSendProgress(run: TrackedRun) {
    if (!config.deliverProgress) {
      run.statusHint = "progress delivery disabled by config";
      return;
    }
    if (run.doneAt) {
      run.statusHint = "completion already detected; progress delivery stopped";
      return;
    }
    if (run.progressCount >= config.maxProgressUpdatesPerRun) {
      run.statusHint = `progress capped at maxProgressUpdatesPerRun=${config.maxProgressUpdatesPerRun}`;
      return;
    }

    const progressText = isMeaningfulProgressText(run.lastProgressText)
      ? run.lastProgressText
      : run.progressCount === 0 && (run.lastEventAt || run.processedLineCount > 0)
        ? buildFallbackProgressText()
        : undefined;
    if (!progressText) {
      run.statusHint = "no meaningful progress text yet";
      return;
    }
    if (progressText === run.lastProgressSentText) {
      run.statusHint = "latest progress already delivered";
      return;
    }

    const baselineTs = run.lastProgressSentAt ?? run.discoveredAt;
    const minDelay = run.progressCount === 0 ? config.firstProgressDelayMs : config.progressDebounceMs;
    if (nowMs() - baselineTs < minDelay) {
      const remainingMs = minDelay - (nowMs() - baselineTs);
      const delayLabel =
        run.progressCount === 0 ? `firstProgressDelayMs=${formatMs(config.firstProgressDelayMs)}` : `progressDebounceMs=${formatMs(config.progressDebounceMs)}`;
      run.statusHint = `waiting ${delayLabel}; remaining ${formatMs(remainingMs)}`;
      return;
    }

    const sessionId = await ensureParentSessionId(run);
    if (!sessionId) {
      run.statusHint = `missing parent sessionId for ${run.parentSessionKey}`;
      logWarn(`missing parent sessionId for ${run.parentSessionKey}`);
      return;
    }

    const message = buildProgressBridgeMessage(run, progressText);
    await runAgentAutomation({
      sessionId,
      agentId: run.parentAgentId,
      message,
      deliver: true,
      thinking: "minimal",
      timeoutSeconds: 90,
    });

    run.lastProgressSentAt = nowMs();
    run.lastProgressSentText = progressText;
    run.progressCount += 1;
    run.statusHint = "progress delivered";
    logInfo(`progress delivered for ${run.childSessionKey}`);
  }

  async function maybeSendCompletion(run: TrackedRun) {
    if (!run.doneAt) return;
    if (run.completionHandled) {
      if (!run.statusHint) run.statusHint = "completion already handled";
      return;
    }
    const settleState = evaluateSettleState({
      doneAt: run.doneAt,
      settleAfterDoneMs: config.settleAfterDoneMs,
    });
    if (!settleState.ready) {
      const remainingMs = settleState.remainingMs;
      run.statusHint = `waiting settleAfterDoneMs=${formatMs(config.settleAfterDoneMs)}; remaining ${formatMs(remainingMs)}`;
      return;
    }

    const sessionId = await ensureParentSessionId(run);
    if (!sessionId) {
      run.statusHint = `missing parent sessionId for ${run.parentSessionKey}`;
      logWarn(`missing parent sessionId for ${run.parentSessionKey}`);
      return;
    }

    const message = buildCompletionBridgeMessage(run);
    await runAgentAutomation({
      sessionId,
      agentId: run.parentAgentId,
      message,
      deliver: config.deliverCompletion,
      thinking: "medium",
      timeoutSeconds: 180,
    });

    run.completionHandled = true;
    run.completionHandledAt = nowMs();
    run.statusHint = config.deliverCompletion ? "completion delivered" : "completion processed without parent deliver";
    logInfo(
      config.deliverCompletion
        ? `completion delivered for ${run.childSessionKey}`
        : `completion processed without deliver for ${run.childSessionKey}`,
    );
  }

  function pruneRuns() {
    const result = pruneTrackedRuns({ runs: state.runs, maxAgeMs: DAY_MS });
    state.runs = result.nextRuns as Record<string, TrackedRun>;
  }

  async function pollOnce() {
    if (!config.enabled || polling) return;
    polling = true;
    try {
      await discoverRuns();
      for (const run of Object.values(state.runs)) {
        await updateRunSnapshot(run);
        await maybeSendProgress(run);
        await maybeSendCompletion(run);
      }
      pruneRuns();
      await persistState();
    } catch (error) {
      logError(error instanceof Error ? error.message : String(error));
    } finally {
      polling = false;
    }
  }

  api.registerCommand({
    name: "bridge-status",
    description: "Show ACP progress bridge status.",
    handler: async () => ({ text: formatStatusSummary(state, config, discoverySummary) }),
  });

  api.registerService({
    id: PLUGIN_ID,
    start: async (ctx: any) => {
      if (!config.enabled || serviceDisabled) {
        logInfo(`service skipped (enabled=${String(config.enabled)} child=${String(serviceDisabled)})`);
        return;
      }
      stateDir = ctx.stateDir;
      stateFile = path.join(ctx.stateDir, "plugins", PLUGIN_ID, "state.json");
      state = await loadState(stateFile);
      await pollOnce();
      timer = setInterval(() => {
        void pollOnce();
      }, config.pollIntervalMs);
      logInfo("service started");
    },
    stop: async () => {
      if (timer) clearInterval(timer);
      timer = null;
      if (stateFile) await persistState();
      logInfo("service stopped");
    },
  });
}
