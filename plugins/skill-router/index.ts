import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";

const PLUGIN_ID = "skill-router";
const ROUTER_START = "[[SKILL_ROUTER_START]]";
const ROUTER_END = "[[SKILL_ROUTER_END]]";

type SkillMeta = {
  name: string;
  description: string;
  skillPath: string; // absolute path to SKILL.md
};

type LlmRoutingConfig = {
  enabled?: boolean;
  model?: string;
  thinking?: "off" | "minimal" | "low" | "medium" | "high" | "xhigh";
  topK?: number;
  maxOutputTokens?: number;
  timeoutMs?: number;
  logSelected?: boolean;
};

type RouterConfig = {
  enabled?: boolean;
  maxSkills?: number;
  includeGlobalSkills?: boolean;
  includeWorkspaceSkills?: boolean;
  respectAgentSkillsFilter?: boolean;
  mode?: "force" | "suggest";
  skipShortPromptsMinChars?: number;

  // Optional: remind the model about available subagents (sessions_spawn targets).
  includeSubagents?: boolean;
  maxSubagents?: number;

  llmRouting?: LlmRoutingConfig;
};

function parseFrontmatter(md: string): Record<string, string> {
  // AgentSkills frontmatter is simple key: value lines; OpenClaw docs: single-line keys.
  const out: Record<string, string> = {};
  const start = md.indexOf("---");
  if (start !== 0) return out;
  const end = md.indexOf("\n---", 3);
  if (end === -1) return out;
  const block = md.slice(3, end).trim();
  for (const line of block.split("\n")) {
    const m = /^([A-Za-z0-9_-]+)\s*:\s*(.*)$/.exec(line.trim());
    if (!m) continue;
    const key = m[1];
    let value = m[2].trim();
    // strip optional quotes
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

async function fileExists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

async function listSkillDirs(skillsRoot: string): Promise<string[]> {
  if (!(await fileExists(skillsRoot))) return [];
  const entries = await fs.readdir(skillsRoot, { withFileTypes: true });
  return entries.filter((e) => e.isDirectory()).map((e) => path.join(skillsRoot, e.name));
}

async function loadSkillsFromRoot(skillsRoot: string): Promise<SkillMeta[]> {
  const dirs = await listSkillDirs(skillsRoot);
  const skills: SkillMeta[] = [];

  for (const dir of dirs) {
    const skillMd = path.join(dir, "SKILL.md");
    if (!(await fileExists(skillMd))) continue;

    // Only read the beginning; name/description live in frontmatter.
    const buf = await fs.readFile(skillMd, "utf8");
    const fm = parseFrontmatter(buf);
    const name = (fm["name"] || "").trim();
    const description = (fm["description"] || "").trim();
    const disableModelInvocation = (fm["disable-model-invocation"] || "").trim().toLowerCase();

    if (!name || !description) continue;
    // Respect Skills' opt-out from model prompt.
    if (disableModelInvocation === "true") continue;

    skills.push({ name, description, skillPath: skillMd });
  }

  return skills;
}

function normalizeSkillKey(name: string): string {
  return name.trim();
}

function resolveAllowedSkillsForAgent(config: any, agentId?: string): Set<string> | null {
  if (!agentId) return null;
  const agents = config?.agents?.list;
  if (!Array.isArray(agents)) return null;
  const agent = agents.find((a: any) => a?.id === agentId);
  const list = agent?.skills;
  if (!Array.isArray(list)) return null;
  // Empty array means: no skills.
  return new Set(list.map((s: any) => String(s)));
}

type ModelRef = { provider: string; model: string };

type ProviderConfig = {
  baseUrl: string;
  apiKey?: string;
  api?: string;
  headers?: Record<string, string>;
};

function parseModelRef(input: string): ModelRef | null {
  const s = input.trim();
  if (!s) return null;
  const idx = s.indexOf("/");
  if (idx === -1) return null;
  const provider = s.slice(0, idx).trim();
  const model = s.slice(idx + 1).trim();
  if (!provider || !model) return null;
  return { provider, model };
}

function resolveAgentModelRef(config: any, agentId?: string): ModelRef | null {
  const list = config?.agents?.list;
  const defaults = config?.agents?.defaults;

  function fromAgent(agent: any): string | undefined {
    if (!agent) return undefined;
    if (typeof agent.model === "string") return agent.model;
    if (agent.model && typeof agent.model.primary === "string") return agent.model.primary;
    return undefined;
  }

  let ref: string | undefined;
  if (agentId && Array.isArray(list)) {
    const agent = list.find((a: any) => a?.id === agentId);
    ref = fromAgent(agent);
  }
  if (!ref) {
    if (typeof defaults?.model?.primary === "string") ref = defaults.model.primary;
    if (typeof defaults?.model === "string") ref = defaults.model;
  }
  if (!ref) return null;
  return parseModelRef(ref);
}

function getProviderConfig(config: any, provider: string): ProviderConfig | null {
  const p = config?.models?.providers?.[provider];
  if (!p || typeof p.baseUrl !== "string") return null;
  const headers: Record<string, string> = {};
  if (p.headers && typeof p.headers === "object") {
    for (const [k, v] of Object.entries(p.headers)) headers[k] = String(v);
  }
  return {
    baseUrl: String(p.baseUrl).replace(/\/$/, ""),
    apiKey: typeof p.apiKey === "string" ? p.apiKey : undefined,
    api: typeof p.api === "string" ? p.api : undefined,
    headers,
  };
}

function sha256Hex(s: string): string {
  return crypto.createHash("sha256").update(s).digest("hex");
}

type LlmRouteResult = { topSkills: string[] };

const llmCache = new Map<string, { at: number; result: LlmRouteResult }>();
const LLM_CACHE_TTL_MS = 5 * 60 * 1000;

function resolveWorkspaceFromConfig(config: any, agentId?: string): string {
  const list = config?.agents?.list;
  if (agentId && Array.isArray(list)) {
    const found = list.find((a: any) => a?.id === agentId);
    if (found?.workspace) return String(found.workspace);
  }
  const def = config?.agents?.defaults?.workspace;
  if (def) return String(def);
  return process.cwd();
}

async function appendJsonlSafe(filePath: string, obj: any): Promise<void> {
  try {
    await fs.mkdir(path.dirname(filePath), { recursive: true });
    await fs.appendFile(filePath, JSON.stringify(obj) + "\n");
  } catch {
    // ignore logging failures
  }
}

function buildLlmRouterPrompt(userPrompt: string, skills: SkillMeta[], topK: number): { system: string; user: string } {
  const system = [
    "You are a router. Select which Skills are most relevant to the user's prompt.",
    "Return STRICT JSON only (no markdown, no prose).",
    "JSON schema:",
    '{"topSkills":["<skillName>",...]}',
    `Rules: topSkills must contain 0..${topK} items. Only choose from the provided skill names exactly.`,
  ].join("\n");

  const lines: string[] = [];
  lines.push("USER_PROMPT:\n" + userPrompt.trim());
  lines.push("");
  lines.push("SKILLS:");
  for (const s of skills) {
    lines.push(`- ${s.name}: ${s.description}`);
  }

  return { system, user: lines.join("\n") };
}

function extractTextFromResponsesApi(json: any): string {
  // OpenAI Responses API typically has output[].content[].text or output_text.
  const out = json?.output;
  if (!Array.isArray(out)) return "";
  const parts: string[] = [];
  for (const item of out) {
    const content = item?.content;
    if (!Array.isArray(content)) continue;
    for (const c of content) {
      if (c?.type === "output_text" && typeof c?.text === "string") parts.push(c.text);
      if (c?.type === "text" && typeof c?.text === "string") parts.push(c.text);
    }
  }
  return parts.join("\n").trim();
}

function extractTextFromChatCompletions(json: any): string {
  const c0 = json?.choices?.[0];
  const msg = c0?.message;
  if (msg && typeof msg.content === "string") return msg.content.trim();
  return "";
}

function tryParseRouterJson(text: string): LlmRouteResult | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start === -1 || end === -1 || end <= start) return null;
  const candidate = trimmed.slice(start, end + 1);
  try {
    const obj = JSON.parse(candidate);
    if (!obj || typeof obj !== "object") return null;
    const top = (obj as any).topSkills;
    if (!Array.isArray(top)) return null;
    const topSkills = top.map((x: any) => String(x)).filter((s: string) => s.trim().length > 0);
    return { topSkills };
  } catch {
    return null;
  }
}

async function routeWithLlm(params: {
  api: any;
  agentId?: string;
  prompt: string;
  skills: SkillMeta[];
  cfg: LlmRoutingConfig;
}): Promise<LlmRouteResult | null> {
  if (!params.cfg?.enabled) return null;

  const startedAt = Date.now();
  const promptHash = sha256Hex(params.prompt).slice(0, 16);
  const logEnabled = params.cfg.logSelected !== false;
  const routesPath = path.join(resolveWorkspaceFromConfig(params.api.config, params.agentId), "plugins", "skill-router", "routes.jsonl");

  const topK = Math.max(0, Math.min(12, Number(params.cfg.topK ?? 4)));
  if (topK === 0) return { topSkills: [] };

  // Resolve model/provider.
  const agentRef = resolveAgentModelRef(params.api.config, params.agentId);
  const requested = typeof params.cfg.model === "string" ? params.cfg.model.trim() : "";
  const requestedRef = requested.includes("/") ? parseModelRef(requested) : null;
  const modelRef: ModelRef | null = requestedRef || (agentRef ? { provider: agentRef.provider, model: requested || agentRef.model } : null);
  if (!modelRef) return null;

  const providerCfg = getProviderConfig(params.api.config, modelRef.provider);
  if (!providerCfg) return null;

  const cacheKey = sha256Hex(
    JSON.stringify({
      p: params.prompt,
      s: params.skills.map((x) => ({ n: x.name, d: x.description })),
      m: modelRef,
      t: params.cfg.thinking ?? "low",
      k: topK,
    })
  );
  const now = Date.now();
  const cached = llmCache.get(cacheKey);
  if (cached && now - cached.at <= LLM_CACHE_TTL_MS) {
    if (logEnabled) {
      await appendJsonlSafe(routesPath, {
        ts: new Date().toISOString(),
        agentId: params.agentId || "",
        provider: modelRef.provider,
        model: modelRef.model,
        thinking: params.cfg.thinking ?? "low",
        topK,
        skillsCount: params.skills.length,
        promptHash,
        cacheHit: true,
        selected: cached.result.topSkills,
        ok: true,
        durationMs: Date.now() - startedAt,
      });
    }
    return cached.result;
  }

  const { system, user } = buildLlmRouterPrompt(params.prompt, params.skills, topK);
  const timeoutMs = Math.max(1000, Number(params.cfg.timeoutMs ?? 12000));

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...providerCfg.headers,
  };
  if (providerCfg.apiKey) headers.Authorization = `Bearer ${providerCfg.apiKey}`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const apiKind = providerCfg.api || "openai-responses";

    let text = "";
    if (apiKind === "openai-responses") {
      const body: any = {
        model: modelRef.model,
        input: [
          // Responses API expects input_text blocks.
          { role: "system", content: [{ type: "input_text", text: system }] },
          { role: "user", content: [{ type: "input_text", text: user }] },
        ],
        max_output_tokens: Number(params.cfg.maxOutputTokens ?? 256),
        temperature: 0,
      };
      const thinking = params.cfg.thinking;
      if (thinking && thinking !== "off") body.reasoning = { effort: thinking };

      const resp = await fetch(`${providerCfg.baseUrl}/responses`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      const raw = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
      const json = (() => {
        try {
          return raw ? JSON.parse(raw) : {};
        } catch {
          return {};
        }
      })();
      text = extractTextFromResponsesApi(json);
    } else {
      // Fallback: OpenAI chat/completions
      const body: any = {
        model: modelRef.model,
        messages: [
          { role: "system", content: system },
          { role: "user", content: user },
        ],
        max_tokens: Number(params.cfg.maxOutputTokens ?? 256),
        temperature: 0,
      };
      const resp = await fetch(`${providerCfg.baseUrl}/chat/completions`, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      const raw = await resp.text().catch(() => "");
      if (!resp.ok) throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
      const json = (() => {
        try {
          return raw ? JSON.parse(raw) : {};
        } catch {
          return {};
        }
      })();
      text = extractTextFromChatCompletions(json);
    }

    const parsed = tryParseRouterJson(text);
    if (!parsed) {
      if (logEnabled) {
        await appendJsonlSafe(routesPath, {
          ts: new Date().toISOString(),
          agentId: params.agentId || "",
          provider: modelRef.provider,
          model: modelRef.model,
          thinking: params.cfg.thinking ?? "low",
          topK,
          skillsCount: params.skills.length,
          promptHash,
          cacheHit: false,
          ok: false,
          error: "parse_failed",
          durationMs: Date.now() - startedAt,
        });
      }
      return null;
    }

    // Keep only allowed skills + clamp.
    const allowed = new Set(params.skills.map((s) => s.name));
    const topSkills = parsed.topSkills.filter((s) => allowed.has(s)).slice(0, topK);
    const result: LlmRouteResult = { topSkills };
    llmCache.set(cacheKey, { at: now, result });

    if (logEnabled) {
      await appendJsonlSafe(routesPath, {
        ts: new Date().toISOString(),
        agentId: params.agentId || "",
        provider: modelRef.provider,
        model: modelRef.model,
        thinking: params.cfg.thinking ?? "low",
        topK,
        skillsCount: params.skills.length,
        promptHash,
        cacheHit: false,
        selected: result.topSkills,
        ok: true,
        durationMs: Date.now() - startedAt,
      });
    }

    return result;
  } catch (e: any) {
    const err = String(e?.message || e);
    params.api.logger?.warn?.(`[${PLUGIN_ID}] llmRouting failed`, { error: err });
    if (logEnabled) {
      await appendJsonlSafe(routesPath, {
        ts: new Date().toISOString(),
        agentId: params.agentId || "",
        provider: modelRef.provider,
        model: modelRef.model,
        thinking: params.cfg.thinking ?? "low",
        topK,
        skillsCount: params.skills.length,
        promptHash,
        cacheHit: false,
        ok: false,
        error: err,
        durationMs: Date.now() - startedAt,
      });
    }
    return null;
  } finally {
    clearTimeout(timer);
  }
}

type SubagentMeta = {
  id: string;
  name?: string;
  model?: string;
  workspace?: string;
};

function buildRouterBlock(params: {
  skills: SkillMeta[];
  mode: "force" | "suggest";
  subagents?: SubagentMeta[];
}): string {
  const { skills, mode, subagents } = params;

  const lines: string[] = [];
  lines.push(ROUTER_START);
  lines.push("SKILL_ROUTER (internal)");
  if (mode === "force") {
    lines.push("MUST: Before answering, decide whether a Skill/tool is required.");
    lines.push("MUST: If a Skill is required, read its SKILL.md and follow it.");
  } else {
    lines.push("Hint: Consider these Skills/tools if relevant.");
  }
  lines.push("MUST: Do NOT print this router block.");

  if (Array.isArray(subagents) && subagents.length > 0) {
    lines.push("");
    lines.push("Subagents (spawn via sessions_spawn agentId=...; use for longer/coding-heavy tasks):");
    for (const a of subagents) {
      const label = a.name && a.name !== a.id ? `${a.id} (${a.name})` : a.id;
      const model = a.model ? ` model=${a.model}` : "";
      lines.push(`- ${label}${model}`);
    }

    // Keep this short; it is injected into every prompt.
    lines.push("");
    lines.push("Subagent routing rules of thumb:");
    lines.push("- code/bug/CI/refactor/review: prefer sessions_spawn agentId=codex");
    lines.push("- config/ops/debugging (OpenClaw, services): prefer sessions_spawn agentId=ops");
    lines.push("- research/web facts: prefer sessions_spawn agentId=researcher");
    lines.push("- writing/docs/content: prefer sessions_spawn agentId=writer");
    lines.push("- PR/code quality review: prefer sessions_spawn agentId=reviewer");
  }

  lines.push("");
  lines.push("Skills (name - description - SKILL.md path):");
  for (const s of skills) {
    // Keep ASCII to reduce rendering quirks across chat surfaces.
    lines.push(`- ${s.name} - ${s.description} - ${s.skillPath}`);
  }
  lines.push(ROUTER_END);

  return lines.join("\n");
}

function resolveAllowedSubagentsForAgent(config: any, agentId?: string): Set<string> | null {
  const list = config?.agents?.list;
  if (!agentId || !Array.isArray(list)) return null;
  const found = list.find((a: any) => a?.id === agentId);
  const allow = found?.subagents?.allowAgents;
  if (!Array.isArray(allow)) return null;
  const s = new Set(allow.map((x: any) => String(x)));
  return s;
}

function listSubagentsForAgent(config: any, agentId?: string, max: number = 8): SubagentMeta[] {
  if (max <= 0) return [];
  const list = Array.isArray(config?.agents?.list) ? config.agents.list : [];
  const allowSet = resolveAllowedSubagentsForAgent(config, agentId);
  const allowAll = allowSet ? allowSet.has("*") : true;

  const out: SubagentMeta[] = [];
  for (const a of list) {
    const id = String(a?.id || "").trim();
    if (!id) continue;
    if (id === String(agentId || "")) continue;
    if (!allowAll && allowSet && !allowSet.has(id)) continue;

    out.push({
      id,
      name: typeof a?.name === "string" ? a.name : undefined,
      model: typeof a?.model === "string" ? a.model : undefined,
      workspace: typeof a?.workspace === "string" ? a.workspace : undefined,
    });
  }

  // Stable ordering: keep predictable list to reduce diff in router hashes.
  out.sort((x, y) => x.id.localeCompare(y.id));
  return out.slice(0, max);
}

function stripRouterLeak(content: string): { content: string; changed: boolean; emptyAfterStrip: boolean } {
  let out = content;
  let changed = false;

  // Strip all occurrences to be safe.
  // Case A: start+end present
  while (true) {
    const startIdx = out.indexOf(ROUTER_START);
    if (startIdx === -1) break;
    const endIdx = out.indexOf(ROUTER_END, startIdx + ROUTER_START.length);
    if (endIdx === -1) {
      // Case B: start present but end missing; drop from start to end-of-message.
      out = out.slice(0, startIdx).trim();
      changed = true;
      break;
    }

    out = `${out.slice(0, startIdx).trimEnd()}\n\n${out.slice(endIdx + ROUTER_END.length).trimStart()}`.trim();
    changed = true;
  }

  // Back-compat: if the model ever prints the old header block, drop it entirely.
  if (out.trimStart().startsWith("## Skill Router")) {
    out = "";
    changed = true;
  }

  return { content: out, changed, emptyAfterStrip: out.trim().length === 0 };
}

export default function register(api: any) {
  // OpenClaw may pass either the raw config object or an entry wrapper ({ enabled, config }).
  // Normalize so cfg always points at the actual config fields.
  const cfg: RouterConfig = ((api.pluginConfig?.config ?? api.pluginConfig) || {}) as RouterConfig;

  // Light debug breadcrumb: helps verify config shape + whether llmRouting is seen by the plugin.
  // This intentionally avoids logging prompt content.
  void (async () => {
    try {
      const ws = String(api.config?.agents?.defaults?.workspace || process.cwd());
      const logPath = path.join(ws, "plugins", "skill-router", "router.log");
      await fs.mkdir(path.dirname(logPath), { recursive: true });

      const pluginConfigKeys =
        api.pluginConfig && typeof api.pluginConfig === "object" ? Object.keys(api.pluginConfig).join(",") : String(typeof api.pluginConfig);
      const cfgKeys = cfg && typeof cfg === "object" ? Object.keys(cfg).join(",") : String(typeof cfg);

      await fs.appendFile(
        logPath,
        `[init] pluginConfigKeys=${pluginConfigKeys} cfgKeys=${cfgKeys} llmRoutingEnabled=${String(cfg?.llmRouting?.enabled)}\n`
      );
    } catch {
      // ignore
    }
  })();

  api.on(
    "message_sending",
    async (event: any, msgCtx: any) => {
      const content = String(event?.content || "");
      if (!content) return;

      // Log to confirm whether this hook runs for a given channel.
      try {
        const ws = resolveWorkspaceForAgent(undefined);
        const logPath = path.join(ws, "plugins", "skill-router", "router.log");
        await fs.appendFile(
          logPath,
          `[message_sending] to=${String(event?.to || "")} channelId=${String(msgCtx?.channelId || "")} contentLen=${content.length}\n`
        );
      } catch {
        // ignore
      }

      const res = stripRouterLeak(content);
      if (!res.changed) return;

      // If the message was only the router block, replace with a minimal hint instead of sending blank.
      if (res.emptyAfterStrip) {
        return {
          content: "(Skill Router is enabled; internal router block was suppressed. Please resend your last question.)",
        };
      }

      return { content: res.content };
    },
    { priority: 200 }
  );

  function resolveWorkspaceForAgent(agentId?: string): string {
    const list = api.config?.agents?.list;
    if (agentId && Array.isArray(list)) {
      const found = list.find((a: any) => a?.id === agentId);
      if (found?.workspace) return String(found.workspace);
    }
    const def = api.config?.agents?.defaults?.workspace;
    if (def) return String(def);
    return process.cwd();
  }

  // Defense-in-depth: strip router block before persisting/sending messages.
  api.on(
    "before_message_write",
    (event: any, hookCtx: any) => {
      const msg = event?.message;
      if (!msg || msg.content == null) return;

      // Useful when debugging hook behavior.
      try {
        const ws = resolveWorkspaceForAgent(hookCtx?.agentId);
        const logPath = path.join(ws, "plugins", "skill-router", "router.log");
        void fs
          .appendFile(
            logPath,
            `[before_message_write] agent=${String(hookCtx?.agentId || "")} role=${String(msg.role || "")} contentType=${Array.isArray(msg.content) ? "array" : typeof msg.content}\n`
          )
          .catch(() => {});
      } catch {
        // ignore
      }

      if (typeof msg.content === "string") {
        const res = stripRouterLeak(msg.content);
        if (!res.changed) return;
        return { message: { ...msg, content: res.content } };
      }

      if (Array.isArray(msg.content)) {
        // Pi message content can be block arrays; router text may be split across blocks.
        // If we see markers anywhere, concatenate all text blocks, strip once, and re-pack.
        const blocks = msg.content as any[];
        const hasMarkers = blocks.some(
          (c) =>
            (c?.type === "text" && typeof c?.text === "string" && (c.text.includes(ROUTER_START) || c.text.includes(ROUTER_END) || c.text.startsWith("## Skill Router"))) ||
            (typeof c === "string" && (c.includes(ROUTER_START) || c.includes(ROUTER_END) || c.startsWith("## Skill Router")))
        );

        if (!hasMarkers) {
          // Best-effort per-block stripping (in case a whole router block fits inside one block)
          let changed = false;
          const newContent = blocks.map((c: any) => {
            if (c?.type !== "text" || typeof c?.text !== "string") return c;
            const res = stripRouterLeak(c.text);
            if (res.changed) changed = true;
            return res.changed ? { ...c, text: res.content } : c;
          });
          if (!changed) return;
          return { message: { ...msg, content: newContent } };
        }

        const textBlocks = blocks.filter((c) => c?.type === "text" && typeof c?.text === "string");
        const otherBlocks = blocks.filter((c) => !(c?.type === "text" && typeof c?.text === "string"));
        const combined = textBlocks.map((c) => c.text).join("\n");
        const res = stripRouterLeak(combined);
        if (!res.changed) return;

        const repacked: any[] = [];
        if (res.content.trim().length > 0) {
          repacked.push({ type: "text", text: res.content });
        }
        // Keep any non-text blocks (rare for router leakage); append after text.
        repacked.push(...otherBlocks);

        return { message: { ...msg, content: repacked } };
      }
    },
    { priority: 200 }
  );

  api.on(
    "before_prompt_build",
    async (event: any, ctx: any) => {
      if (cfg.enabled === false) return;

      let prompt: string = String(event?.prompt || "");
      if (!prompt.trim()) return;

      // If a user ever forwards the internal router block back to us, strip it so it doesn't pollute routing.
      // (Users often copy/paste to report bugs.)
      prompt = stripRouterLeak(prompt).content;
      // Slash/Control commands: avoid interfering.
      if (prompt.trim().startsWith("/")) return;

      // Skip trivial short prompts (greetings/tests) to reduce cost and leak risk.
      const minChars = typeof cfg.skipShortPromptsMinChars === "number" ? cfg.skipShortPromptsMinChars : 12;
      const compact = prompt.trim();
      const lower = compact.toLowerCase();
      const isGreeting =
        lower === "hi" ||
        lower === "hello" ||
        compact === "你好" ||
        compact === "你好啊" ||
        compact === "在吗" ||
        compact === "测试";
      if (isGreeting || compact.length < minChars) return;

      const includeWorkspace = cfg.includeWorkspaceSkills !== false;
      const includeGlobal = cfg.includeGlobalSkills !== false;
      const maxSkills = typeof cfg.maxSkills === "number" ? cfg.maxSkills : 12;
      const mode: "force" | "suggest" = cfg.mode === "suggest" ? "suggest" : "force";

      const roots: string[] = [];
      if (includeWorkspace && ctx?.workspaceDir) roots.push(path.join(String(ctx.workspaceDir), "skills"));
      if (includeGlobal) roots.push(path.join(os.homedir(), ".openclaw", "skills"));

      // Optional extraDirs (lowest priority) if configured.
      const extraDirs = api.config?.skills?.load?.extraDirs;
      if (Array.isArray(extraDirs)) {
        for (const d of extraDirs) roots.push(api.resolvePath(String(d)));
      }

      // Load and de-dup (workspace overrides global).
      const all: SkillMeta[] = [];
      for (const root of roots) {
        try {
          const list = await loadSkillsFromRoot(root);
          all.push(...list);
        } catch (e: any) {
          api.logger?.warn?.(`[${PLUGIN_ID}] Failed to scan skills root: ${root}`, { error: String(e?.message || e) });
        }
      }

      const byName = new Map<string, SkillMeta>();
      for (const s of all) {
        const key = normalizeSkillKey(s.name);
        // Keep the first seen (workspace first), then ignore lower priority duplicates.
        if (!byName.has(key)) byName.set(key, s);
      }

      let skills = Array.from(byName.values());

      // Respect per-agent skills filter if present.
      if (cfg.respectAgentSkillsFilter !== false) {
        const allowed = resolveAllowedSkillsForAgent(api.config, ctx?.agentId);
        if (allowed) {
          if (allowed.size === 0) return;
          skills = skills.filter((s) => allowed.has(s.name) || allowed.has(normalizeSkillKey(s.name)));
        }
      }

      // Keep router block compact.
      if (skills.length === 0) return;
      skills = skills.slice(0, Math.max(1, maxSkills));

      // Optional: LLM-based Top-K routing to further narrow the candidate set.
      const llmCfg = cfg.llmRouting;
      if (llmCfg?.enabled) {
        const routed = await routeWithLlm({
          api,
          agentId: ctx?.agentId,
          prompt: compact,
          skills,
          cfg: llmCfg,
        });
        if (routed && routed.topSkills.length > 0) {
          const keep = new Set(routed.topSkills);
          skills = skills.filter((s) => keep.has(s.name));
        }
      }

      if (skills.length === 0) return;
      const includeSubagents = cfg.includeSubagents !== false;
      const maxSubagents = Math.max(0, Math.min(20, Number(cfg.maxSubagents ?? 8)));
      const subagents = includeSubagents ? listSubagentsForAgent(api.config, ctx?.agentId, maxSubagents) : [];

      const routerBlock = buildRouterBlock({ skills, mode, subagents });
      api.logger?.debug?.(`[${PLUGIN_ID}] Inject router block`, {
        agentId: ctx?.agentId,
        skillsCount: skills.length,
      });

      return { prependContext: routerBlock };
    },
    { priority: 100 }
  );
}
