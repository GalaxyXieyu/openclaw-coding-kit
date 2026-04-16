#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const {
  ensureParentDir,
  fail,
  loadScenario,
  resolveStorageStatePath,
} = require('./web_cli_support');

const PRODUCT_CANVAS_ENTRY = path.resolve(__dirname, 'product_canvas.py');

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

function parseJson(raw, context) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${context} 不是合法 JSON: ${error instanceof Error ? error.message : String(error)}`);
  }
}

function loadManifest(manifestPath) {
  const resolvedPath = path.resolve(manifestPath);
  if (!fs.existsSync(resolvedPath)) {
    throw new Error(`MANIFEST_NOT_FOUND: ${resolvedPath}`);
  }
  return {
    path: resolvedPath,
    manifest: parseJson(fs.readFileSync(resolvedPath, 'utf8'), 'manifest'),
  };
}

function normalizeRoute(route) {
  return String(route ?? '').trim().replace(/^\/+/, '');
}

function scenarioOpenTarget(scenario) {
  const steps = Array.isArray(scenario?.steps) ? scenario.steps : [];
  const openStep = steps.find((step) => step && step.action === 'open');
  return String(openStep?.target ?? '').trim();
}

function scenarioHasPlaceholder(scenario) {
  const openTarget = scenarioOpenTarget(scenario);
  return Boolean(openTarget) && (openTarget.includes('__AUTO_') || /\[[^\]]+\]/.test(openTarget));
}

function pickScenarioRef(node) {
  const cardRefs = Array.isArray(node?.card?.scenario_refs) ? node.card.scenario_refs : [];
  const metaRefs = Array.isArray(node?.board_meta?.scenario_refs) ? node.board_meta.scenario_refs : [];
  const refs = cardRefs.length ? cardRefs : metaRefs;
  const preferred = refs.find((ref) => ref && ref.engine === 'web-playwright-cli' && ref.role !== 'entry');
  return preferred || refs.find((ref) => ref && ref.engine === 'web-playwright-cli') || null;
}

function nodeSearchBlob(node) {
  const aliases = Array.isArray(node?.aliases) ? node.aliases : [];
  return [
    node?.node_id,
    node?.title,
    node?.route,
    node?.route_key,
    ...aliases,
  ].join(' ').toLowerCase();
}

function cookieMatchesDomain(cookieDomain, hostname) {
  const normalized = String(cookieDomain ?? '').trim().replace(/^\./, '').toLowerCase();
  const host = String(hostname ?? '').trim().toLowerCase();
  if (!normalized || !host) {
    return false;
  }
  return host === normalized || host.endsWith(`.${normalized}`);
}

function cookieMatchesPath(cookiePath, pathname) {
  const normalizedCookiePath = String(cookiePath ?? '/').trim() || '/';
  const normalizedPathname = String(pathname ?? '/').trim() || '/';
  return normalizedPathname.startsWith(normalizedCookiePath);
}

function buildCookieHeader(storageStatePath, targetUrl) {
  const storageState = parseJson(fs.readFileSync(storageStatePath, 'utf8'), 'storage state');
  const cookies = Array.isArray(storageState?.cookies) ? storageState.cookies : [];
  const url = new URL(targetUrl);
  const now = Math.floor(Date.now() / 1000);
  const matched = cookies.filter((cookie) => {
    if (!cookie || typeof cookie !== 'object') {
      return false;
    }
    if (!cookieMatchesDomain(cookie.domain, url.hostname)) {
      return false;
    }
    if (!cookieMatchesPath(cookie.path, url.pathname)) {
      return false;
    }
    if (Number.isFinite(cookie.expires) && cookie.expires > 0 && cookie.expires <= now) {
      return false;
    }
    return Boolean(cookie.name);
  });
  return matched.map((cookie) => `${cookie.name}=${cookie.value}`).join('; ');
}

async function fetchJson(baseUrl, storageStatePath, requestPath, cache) {
  const url = new URL(requestPath, baseUrl).toString();
  if (cache.has(url)) {
    return cache.get(url);
  }

  const cookieHeader = buildCookieHeader(storageStatePath, url);
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      ...(cookieHeader ? { Cookie: cookieHeader } : {}),
    },
  });
  const raw = await response.text();
  const payload = raw.trim() ? parseJson(raw, `response:${requestPath}`) : null;
  if (!response.ok) {
    throw new Error(`FETCH_FAILED ${requestPath}: ${response.status} ${response.statusText}`);
  }
  cache.set(url, payload);
  return payload;
}

async function resolveDynamicRouteParams(route, context) {
  if (
    route === 'dashboard/tenants/[tenantId]'
    || route === 'dashboard/tenants/[tenantId]/livestock'
  ) {
    const payload = await fetchJson(context.baseUrl, context.storageStatePath, '/api/admin-proxy/tenants', context.cache);
    const tenant = Array.isArray(payload?.tenants) ? payload.tenants[0] : null;
    return tenant?.id ? { tenantId: tenant.id } : null;
  }

  if (route === 'dashboard/commerce/catalog/[productId]') {
    const payload = await fetchJson(context.baseUrl, context.storageStatePath, '/api/admin-proxy/supply/products', context.cache);
    const product = Array.isArray(payload?.products) ? payload.products[0] : null;
    return product?.id ? { productId: product.id } : null;
  }

  if (route === 'dashboard/commerce/community/[postId]') {
    const payload = await fetchJson(context.baseUrl, context.storageStatePath, '/api/admin-proxy/guiquan/community/posts', context.cache);
    const post = Array.isArray(payload?.posts) ? payload.posts[0] : null;
    return post?.id ? { postId: post.id } : null;
  }

  if (route === 'dashboard/commerce/marketplace/[listingId]') {
    const payload = await fetchJson(
      context.baseUrl,
      context.storageStatePath,
      '/api/admin-proxy/marketplace/listings?page=1&pageSize=100',
      context.cache,
    );
    const listing = Array.isArray(payload?.listings) ? payload.listings[0] : null;
    return listing?.id ? { listingId: listing.id } : null;
  }

  return null;
}

function replaceRouteParams(target, params) {
  let next = String(target ?? '');
  for (const [key, value] of Object.entries(params)) {
    const normalizedValue = String(value ?? '').trim();
    if (!normalizedValue) {
      continue;
    }
    next = next.replaceAll(`[${key}]`, normalizedValue);
    next = next.replaceAll(`__AUTO_${key.toUpperCase()}__`, normalizedValue);
  }
  return next;
}

function applySampleParamsToScenario(scenario, params) {
  const steps = Array.isArray(scenario?.steps) ? scenario.steps : [];
  const nextScenario = {
    ...scenario,
    context: {
      ...(scenario?.context && typeof scenario.context === 'object' ? scenario.context : {}),
      sample_route_params: params,
    },
    steps: steps.map((step) => {
      if (!step || step.action !== 'open') {
        return step;
      }
      return {
        ...step,
        target: replaceRouteParams(step.target, params),
      };
    }),
  };

  const nextTarget = scenarioOpenTarget(nextScenario);
  if (nextTarget) {
    nextScenario.context.sample_open_target = nextTarget;
  }

  const noteSegments = [];
  const existingNotes = String(nextScenario.context.notes ?? '').trim();
  if (existingNotes) {
    noteSegments.push(existingNotes);
  }
  noteSegments.push(
    `已解析动态参数: ${Object.entries(params).map(([key, value]) => `${key}=${value}`).join(', ')}`,
  );
  nextScenario.context.notes = noteSegments.join(' ').trim();
  return nextScenario;
}

function renderScenarioSpec(scenarioPath, specPath) {
  const result = spawnSync(
    'python3',
    [PRODUCT_CANVAS_ENTRY, 'render-scenario-spec', '--scenario', scenarioPath, '--output', specPath],
    {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      env: process.env,
    },
  );
  if (result.status !== 0) {
    throw new Error(`RENDER_SCENARIO_SPEC_FAILED: ${result.stderr.trim() || result.stdout.trim()}`);
  }
}

async function resolveNodeSample(node, options, cache) {
  const scenarioRef = pickScenarioRef(node);
  if (!scenarioRef?.scenario_path) {
    return {
      nodeId: String(node?.node_id ?? ''),
      route: String(node?.route ?? ''),
      status: 'no-scenario',
    };
  }

  const bundle = loadScenario(scenarioRef.scenario_path);
  if (!scenarioHasPlaceholder(bundle.scenario) && !options.force) {
    return {
      nodeId: String(node?.node_id ?? ''),
      route: String(node?.route ?? ''),
      scenarioId: bundle.scenario?.scenario_id ?? '',
      scenarioPath: bundle.path,
      status: 'already-resolved',
      openTarget: scenarioOpenTarget(bundle.scenario),
    };
  }

  const baseUrl = readOption('--base-url', '')
    || String(bundle.target?.base_url ?? bundle.target?.baseUrl ?? '')
    || options.baseUrl;
  if (!baseUrl) {
    return {
      nodeId: String(node?.node_id ?? ''),
      route: String(node?.route ?? ''),
      scenarioId: bundle.scenario?.scenario_id ?? '',
      scenarioPath: bundle.path,
      status: 'missing-base-url',
    };
  }

  const storageStatePath = resolveStorageStatePath({
    scenarioPath: bundle.path,
    storageStateInput: options.storageState || bundle.target?.storage_state || bundle.target?.storageState || '',
    authProfile: bundle.target?.auth_profile || bundle.target?.authProfile || bundle.scenario?.scenario_id || 'default',
  });

  if (!fs.existsSync(storageStatePath)) {
    return {
      nodeId: String(node?.node_id ?? ''),
      route: String(node?.route ?? ''),
      scenarioId: bundle.scenario?.scenario_id ?? '',
      scenarioPath: bundle.path,
      status: 'missing-storage-state',
      storageStatePath,
    };
  }

  const params = await resolveDynamicRouteParams(normalizeRoute(node?.route), {
    baseUrl,
    storageStatePath,
    cache,
  });
  if (!params) {
    return {
      nodeId: String(node?.node_id ?? ''),
      route: String(node?.route ?? ''),
      scenarioId: bundle.scenario?.scenario_id ?? '',
      scenarioPath: bundle.path,
      status: 'sample-not-found',
    };
  }

  const patchedScenario = applySampleParamsToScenario(bundle.scenario, params);
  const nextTarget = scenarioOpenTarget(patchedScenario);

  if (!options.dryRun) {
    ensureParentDir(bundle.path);
    fs.writeFileSync(bundle.path, `${JSON.stringify(patchedScenario, null, 2)}\n`, 'utf8');
    const specPath = scenarioRef.script_absolute_path
      ? path.resolve(scenarioRef.script_absolute_path)
      : path.resolve(bundle.path.replace(/\.json$/i, '.spec.ts'));
    renderScenarioSpec(bundle.path, specPath);
  }

  return {
    nodeId: String(node?.node_id ?? ''),
    route: String(node?.route ?? ''),
    scenarioId: patchedScenario?.scenario_id ?? '',
    scenarioPath: bundle.path,
    status: options.dryRun ? 'preview' : 'resolved',
    params,
    openTarget: nextTarget,
    storageStatePath,
  };
}

async function main() {
  const manifestInput = readOption('--manifest', '');
  if (!manifestInput) {
    fail('MANIFEST_REQUIRED', {
      message: '请传 --manifest <board.manifest.json>',
    });
  }

  const query = String(readOption('--query', '')).trim().toLowerCase();
  const dryRun = hasFlag('--dry-run');
  const force = hasFlag('--force');
  const reportPathInput = readOption('--json-output', '');
  const options = {
    baseUrl: readOption('--base-url', ''),
    storageState: readOption('--storage-state', ''),
    dryRun,
    force,
  };

  const { manifest, path: manifestPath } = loadManifest(manifestInput);
  const cache = new Map();
  const nodes = Array.isArray(manifest?.nodes) ? manifest.nodes : [];
  const targets = nodes.filter((node) => {
    if (!node?.board_meta?.requires_parameters) {
      return false;
    }
    if (!query) {
      return true;
    }
    return nodeSearchBlob(node).includes(query);
  });

  const results = [];
  for (const node of targets) {
    try {
      results.push(await resolveNodeSample(node, options, cache));
    } catch (error) {
      results.push({
        nodeId: String(node?.node_id ?? ''),
        route: String(node?.route ?? ''),
        status: 'error',
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }

  const summary = {
    ok: results.every((item) => item.status !== 'error'),
    manifestPath,
    totalCount: targets.length,
    resolvedCount: results.filter((item) => item.status === 'resolved').length,
    previewCount: results.filter((item) => item.status === 'preview').length,
    alreadyResolvedCount: results.filter((item) => item.status === 'already-resolved').length,
    unresolvedCount: results.filter((item) => !['resolved', 'preview', 'already-resolved'].includes(item.status)).length,
    results,
  };

  if (reportPathInput) {
    const reportPath = path.resolve(reportPathInput);
    ensureParentDir(reportPath);
    fs.writeFileSync(reportPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(summary, null, 2));
  if (!summary.ok) {
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch((error) => {
    fail('WEB_DYNAMIC_SAMPLES_FAILED', {
      message: error instanceof Error ? error.message : String(error),
    });
  });
}

module.exports = {
  applySampleParamsToScenario,
  buildCookieHeader,
  normalizeRoute,
  pickScenarioRef,
  replaceRouteParams,
  resolveDynamicRouteParams,
  scenarioHasPlaceholder,
  scenarioOpenTarget,
};
