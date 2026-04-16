const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

function readOption(name, fallback = '') {
  const index = process.argv.indexOf(name);
  if (index === -1) {
    return fallback;
  }
  return process.argv[index + 1] ?? fallback;
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function ensureParentDir(filePath) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
}

function fail(message, details) {
  const payload = {
    ok: false,
    error: message,
    details,
  };
  console.error(JSON.stringify(payload, null, 2));
  process.exit(1);
}

function parseJsonOutput(raw, context) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${context} 输出不是合法 JSON:\n${raw}\n${error instanceof Error ? error.message : String(error)}`);
  }
}

function loadScenario(scenarioPath) {
  const resolvedPath = path.resolve(scenarioPath);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`SCENARIO_NOT_FOUND: ${resolvedPath}`);
  }
  const raw = fs.readFileSync(resolvedPath, 'utf8').trim();
  const scenario = parseJsonOutput(raw, 'scenario');
  const target = scenario && typeof scenario.target === 'object' && !Array.isArray(scenario.target)
    ? scenario.target
    : {};
  const capture = scenario && typeof scenario.capture === 'object' && !Array.isArray(scenario.capture)
    ? scenario.capture
    : {};
  return {
    path: resolvedPath,
    scenario,
    target,
    capture,
  };
}

function pickText(...values) {
  for (const value of values) {
    const normalized = String(value ?? '').trim();
    if (normalized) {
      return normalized;
    }
  }
  return '';
}

function toInteger(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) {
    return undefined;
  }

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed)) {
    return undefined;
  }
  return Math.max(0, Math.round(parsed));
}

function pickInteger(...values) {
  for (const value of values) {
    const parsed = toInteger(value);
    if (parsed !== undefined) {
      return parsed;
    }
  }
  return undefined;
}

function pickBoolean(...values) {
  for (const value of values) {
    if (typeof value === 'boolean') {
      return value;
    }
    const normalized = String(value ?? '').trim().toLowerCase();
    if (!normalized) {
      continue;
    }
    if (['1', 'true', 'yes', 'on'].includes(normalized)) {
      return true;
    }
    if (['0', 'false', 'no', 'off'].includes(normalized)) {
      return false;
    }
  }
  return undefined;
}

function sanitizeFileToken(value, fallback = 'default') {
  const normalized = String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return normalized || fallback;
}

function resolveScenarioRelativePath(inputPath, scenarioPath) {
  if (!inputPath) {
    return '';
  }
  if (path.isAbsolute(inputPath)) {
    return path.resolve(inputPath);
  }
  if (scenarioPath) {
    return path.resolve(path.dirname(path.resolve(scenarioPath)), inputPath);
  }
  return path.resolve(inputPath);
}

function resolveStorageStatePath(options = {}) {
  const explicit = pickText(options.storageStateInput);
  if (explicit) {
    return resolveScenarioRelativePath(explicit, options.scenarioPath);
  }

  const profile = sanitizeFileToken(options.authProfile, 'default');
  return path.resolve('out', 'product-canvas', 'auth', `${profile}.session.json`);
}

function resolveCaptureOutputPath(options = {}) {
  const explicit = pickText(options.outputPathInput, options.captureOutputInput);
  if (!explicit) {
    return '';
  }
  return resolveScenarioRelativePath(explicit, options.scenarioPath);
}

function readWebTargetOptions(options = {}) {
  const scenarioBundle = options.scenarioPath ? loadScenario(options.scenarioPath) : null;
  const target = scenarioBundle?.target ?? {};
  const capture = scenarioBundle?.capture ?? {};

  const login = pickText(readOption('--login', ''), process.env.PRODUCT_CANVAS_LOGIN || '');
  const password = pickText(readOption('--password', ''), process.env.PRODUCT_CANVAS_PASSWORD || '');

  return {
    scenarioPath: scenarioBundle?.path ?? null,
    rawScenario: scenarioBundle?.scenario ?? null,
    target,
    capture,
    baseUrl: pickText(readOption('--base-url', ''), target.base_url, target.baseUrl),
    authSurface: pickText(readOption('--auth-surface', ''), target.auth_surface, target.authSurface),
    authProfile: pickText(readOption('--auth-profile', ''), target.auth_profile, target.authProfile),
    storageStateInput: pickText(readOption('--storage-state', ''), target.storage_state, target.storageState),
    waitSelectorInput: pickText(readOption('--wait-selector', '')),
    waitTimeoutMsInput: pickInteger(readOption('--timeout', ''), target.timeout_ms, target.timeoutMs),
    waitForTimeoutMsInput: pickInteger(readOption('--wait-for-timeout', '')),
    viewportSize: pickText(readOption('--viewport-size', ''), target.viewport_size, target.viewportSize, '1440,1000'),
    browserChannel: pickText(readOption('--channel', ''), target.browser_channel, target.browserChannel, 'chrome'),
    fullPage: hasFlag('--no-full-page')
      ? false
      : pickBoolean(target.full_page, target.fullPage) !== false,
    outputPathInput: pickText(readOption('--output', '')),
    captureOutputInput: pickText(capture.output),
    login,
    password,
  };
}

function deriveScenarioUrl(scenario, options = {}) {
  const baseUrl = pickText(options.baseUrl, scenario?.target?.base_url, scenario?.target?.baseUrl);
  if (!baseUrl) {
    throw new Error('BASE_URL_REQUIRED');
  }

  const openStep = Array.isArray(scenario?.steps)
    ? scenario.steps.find((step) => step && step.action === 'open')
    : null;
  const target = pickText(openStep?.target, scenario?.target?.url, scenario?.target?.target);
  if (!target) {
    return baseUrl;
  }
  if (/^https?:\/\//i.test(target)) {
    return target;
  }
  return new URL(target, baseUrl).toString();
}

function deriveWaitSelector(scenario, explicitSelector = '') {
  const cliSelector = pickText(explicitSelector);
  if (cliSelector) {
    return cliSelector;
  }

  const steps = Array.isArray(scenario?.steps) ? scenario.steps : [];
  for (const step of steps) {
    if (!step || step.action !== 'wait') {
      continue;
    }
    const selector = pickText(step.selector);
    if (selector) {
      return selector;
    }
    const text = pickText(step.text);
    if (text) {
      return `text=${text}`;
    }
  }

  const assertions = Array.isArray(scenario?.assertions) ? scenario.assertions : [];
  for (const assertion of assertions) {
    if (!assertion || typeof assertion !== 'object') {
      continue;
    }
    if (assertion.type === 'selector') {
      const selector = pickText(assertion.selector, assertion.value);
      if (selector) {
        return selector;
      }
    }
    if (assertion.type === 'text') {
      const text = pickText(assertion.value, assertion.text);
      if (text) {
        return `text=${text}`;
      }
    }
  }

  return '';
}

function deriveWaitForTimeoutMs(scenario, explicitMs) {
  if (explicitMs !== undefined) {
    return explicitMs;
  }

  const steps = Array.isArray(scenario?.steps) ? scenario.steps : [];
  let totalMs = 0;
  for (const step of steps) {
    if (!step || step.action !== 'wait') {
      continue;
    }
    const current = toInteger(step.ms);
    if (current !== undefined) {
      totalMs += current;
    }
  }
  return totalMs;
}

function deriveWaitTimeoutMs(scenario, explicitMs) {
  if (explicitMs !== undefined) {
    return explicitMs;
  }

  const target = scenario && typeof scenario.target === 'object' && !Array.isArray(scenario.target)
    ? scenario.target
    : {};

  return pickInteger(target.timeout_ms, target.timeoutMs, 20000);
}

function splitSetCookieHeader(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) {
    return [];
  }
  return normalized
    .split(/,(?=\s*[^;,=\s]+=[^;]+)/g)
    .map((part) => part.trim())
    .filter(Boolean);
}

function normalizeSameSite(value) {
  const normalized = String(value ?? '').trim().toLowerCase();
  if (!normalized) {
    return undefined;
  }
  if (normalized === 'lax') {
    return 'Lax';
  }
  if (normalized === 'strict') {
    return 'Strict';
  }
  if (normalized === 'none') {
    return 'None';
  }
  return undefined;
}

function parseSetCookieHeader(setCookieHeader, baseUrl) {
  const normalized = String(setCookieHeader ?? '').trim();
  if (!normalized) {
    return null;
  }

  const base = new URL(baseUrl);
  const parts = normalized.split(';').map((part) => part.trim()).filter(Boolean);
  const [nameValue, ...attributeParts] = parts;
  const separatorIndex = nameValue.indexOf('=');
  if (separatorIndex <= 0) {
    return null;
  }

  const name = nameValue.slice(0, separatorIndex).trim();
  const value = nameValue.slice(separatorIndex + 1).trim();
  if (!name) {
    return null;
  }

  const flags = new Set();
  const attributes = new Map();
  for (const part of attributeParts) {
    const index = part.indexOf('=');
    if (index === -1) {
      flags.add(part.toLowerCase());
      continue;
    }
    const key = part.slice(0, index).trim().toLowerCase();
    const attributeValue = part.slice(index + 1).trim();
    attributes.set(key, attributeValue);
  }

  let expires = -1;
  const maxAgeValue = attributes.get('max-age');
  if (maxAgeValue !== undefined) {
    const maxAge = Number(maxAgeValue);
    if (Number.isFinite(maxAge)) {
      expires = Math.floor(Date.now() / 1000) + Math.max(0, Math.round(maxAge));
    }
  } else if (attributes.has('expires')) {
    const expiresAt = Date.parse(attributes.get('expires'));
    if (Number.isFinite(expiresAt)) {
      expires = Math.floor(expiresAt / 1000);
    }
  }

  const cookie = {
    name,
    value,
    domain: attributes.get('domain') || base.hostname,
    path: attributes.get('path') || '/',
    expires,
    httpOnly: flags.has('httponly'),
    secure: flags.has('secure'),
  };

  const sameSite = normalizeSameSite(attributes.get('samesite'));
  if (sameSite) {
    cookie.sameSite = sameSite;
  }

  return cookie;
}

function buildCookieStorageState(setCookieHeaders, baseUrl) {
  const cookieMap = new Map();
  for (const header of setCookieHeaders) {
    const parsed = parseSetCookieHeader(header, baseUrl);
    if (!parsed) {
      continue;
    }
    const key = `${parsed.name}|${parsed.domain}|${parsed.path}`;
    cookieMap.set(key, parsed);
  }

  const cookies = [...cookieMap.values()].filter((cookie) => cookie.value !== '');
  return {
    cookies,
    origins: [],
  };
}

function extractSetCookieHeaders(headers) {
  if (headers && typeof headers.getSetCookie === 'function') {
    return headers.getSetCookie();
  }
  const combined = headers && typeof headers.get === 'function'
    ? headers.get('set-cookie')
    : '';
  return splitSetCookieHeader(combined);
}

async function bootstrapAdminStorageState(options = {}) {
  const baseUrl = pickText(options.baseUrl);
  const login = pickText(options.login);
  const password = pickText(options.password);
  const authSurface = pickText(options.authSurface, 'admin');
  const authProfile = pickText(options.authProfile, 'default');
  const storageStatePath = path.resolve(options.storageStatePath);

  if (!baseUrl) {
    throw new Error('BASE_URL_REQUIRED');
  }
  if (authSurface !== 'admin') {
    throw new Error(`UNSUPPORTED_AUTH_SURFACE: ${authSurface}`);
  }
  if (!login || !password) {
    throw new Error('LOGIN_AND_PASSWORD_REQUIRED');
  }

  const loginUrl = new URL('/api/auth/password-login', baseUrl).toString();
  const response = await fetch(loginUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      login,
      password,
    }),
  });

  const responseText = await response.text();
  let responseBody = null;
  if (responseText.trim()) {
    try {
      responseBody = JSON.parse(responseText);
    } catch {
      responseBody = null;
    }
  }

  if (!response.ok) {
    const error = new Error(`AUTH_REQUEST_FAILED: ${response.status}`);
    error.details = {
      status: response.status,
      statusText: response.statusText,
      body: responseBody || responseText.slice(0, 400),
    };
    throw error;
  }

  const setCookieHeaders = extractSetCookieHeaders(response.headers);
  const storageState = buildCookieStorageState(setCookieHeaders, baseUrl);
  const authCookie = storageState.cookies.find((cookie) => cookie.name === 'eggturtle.admin.access_token');
  if (!authCookie) {
    const error = new Error('AUTH_COOKIE_NOT_FOUND');
    error.details = {
      setCookieHeaders,
    };
    throw error;
  }

  ensureParentDir(storageStatePath);
  fs.writeFileSync(storageStatePath, `${JSON.stringify(storageState, null, 2)}\n`, 'utf8');

  return {
    ok: true,
    authSurface,
    authProfile,
    baseUrl,
    loginUrl,
    storageStatePath,
    cookiesWritten: storageState.cookies.map((cookie) => cookie.name),
    responseStatus: response.status,
    userSummary: responseBody && typeof responseBody === 'object'
      ? {
          userId: responseBody.user?.id ?? null,
          email: responseBody.user?.email ?? null,
          isSuperAdmin: responseBody.user?.isSuperAdmin ?? null,
        }
      : null,
  };
}

function runNpx(args, env = process.env) {
  return spawnSync('npx', args, {
    encoding: 'utf8',
    stdio: ['inherit', 'pipe', 'pipe'],
    env,
  });
}

module.exports = {
  bootstrapAdminStorageState,
  buildCookieStorageState,
  deriveScenarioUrl,
  deriveWaitForTimeoutMs,
  deriveWaitSelector,
  deriveWaitTimeoutMs,
  ensureParentDir,
  fail,
  hasFlag,
  loadScenario,
  parseSetCookieHeader,
  readOption,
  readWebTargetOptions,
  resolveCaptureOutputPath,
  resolveStorageStatePath,
  runNpx,
  splitSetCookieHeader,
};
