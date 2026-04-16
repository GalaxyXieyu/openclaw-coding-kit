#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { ensureParentDir, fail, loadScenario } = require('./web_cli_support');

const WEB_SCENARIO_SCRIPT = path.resolve(__dirname, 'web_scenario.js');

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

function toInteger(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.max(0, Math.round(parsed)) : fallback;
}

function sanitizeFileToken(value, fallback = 'scenario') {
  const normalized = String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return normalized || fallback;
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

function scenarioOpenTarget(scenario) {
  const steps = Array.isArray(scenario?.steps) ? scenario.steps : [];
  const openStep = steps.find((step) => step && step.action === 'open');
  return String(openStep?.target ?? '').trim();
}

function scenarioHasPlaceholder(scenario) {
  const openTarget = scenarioOpenTarget(scenario);
  if (!openTarget) {
    return false;
  }
  return openTarget.includes('__AUTO_') || /\[[^\]]+\]/.test(openTarget);
}

function scenarioHasResolvedDynamicTarget(node, scenario) {
  const requiresParameters = Boolean(node?.board_meta?.requires_parameters);
  if (!requiresParameters) {
    return false;
  }
  const openTarget = scenarioOpenTarget(scenario);
  if (!openTarget) {
    return false;
  }
  return !scenarioHasPlaceholder(scenario);
}

function nodeSearchBlob(node) {
  const aliases = Array.isArray(node?.aliases) ? node.aliases : [];
  return [
    node?.node_id,
    node?.title,
    node?.route,
    node?.route_key,
    ...(aliases || []),
  ].join(' ').toLowerCase();
}

function pickScenarioRef(node, { includeEntry = false } = {}) {
  const refs = Array.isArray(node?.card?.scenario_refs) ? node.card.scenario_refs : [];
  const preferred = refs.find((ref) => ref && ref.engine === 'web-playwright-cli' && ref.role !== 'entry');
  if (preferred) {
    return preferred;
  }
  if (includeEntry) {
    return refs.find((ref) => ref && ref.engine === 'web-playwright-cli') || null;
  }
  return null;
}

function shouldRunNode(node, scenario, options = {}) {
  const query = String(options.query ?? '').trim().toLowerCase();
  if (query && !nodeSearchBlob(node).includes(query)) {
    return { run: false, reason: 'query-filtered' };
  }

  const boardMeta = node?.board_meta && typeof node.board_meta === 'object' ? node.board_meta : {};
  const routeMode = String(boardMeta.route_mode ?? '').trim();
  const isDynamic = scenarioHasPlaceholder(scenario)
    || (Boolean(boardMeta.requires_parameters) && !scenarioHasResolvedDynamicTarget(node, scenario));

  if (!options.includeEntry && String(node?.group ?? '') === 'entry') {
    return { run: false, reason: 'entry-node' };
  }
  if (!options.includeRedirect && routeMode === 'redirect') {
    return { run: false, reason: 'redirect-only' };
  }
  if (!options.includeDynamic && isDynamic) {
    return { run: false, reason: 'dynamic-route' };
  }

  return { run: true, reason: '' };
}

function collectManifestScenarioTasks(manifest, options = {}) {
  const includeEntry = Boolean(options.includeEntry);
  const selected = [];
  const skipped = [];
  const nodes = Array.isArray(manifest?.nodes) ? manifest.nodes : [];

  for (const node of nodes) {
    const scenarioRef = pickScenarioRef(node, { includeEntry });
    if (!scenarioRef || !scenarioRef.scenario_path) {
      skipped.push({
        node_id: node?.node_id ?? '',
        route: node?.route ?? '',
        reason: 'no-web-scenario',
      });
      continue;
    }

    const bundle = loadScenario(scenarioRef.scenario_path);
    const decision = shouldRunNode(node, bundle.scenario, options);
    if (!decision.run) {
      skipped.push({
        node_id: node?.node_id ?? '',
        route: node?.route ?? '',
        scenario_id: bundle.scenario?.scenario_id ?? '',
        reason: decision.reason,
      });
      continue;
    }

    selected.push({
      nodeId: String(node?.node_id ?? ''),
      route: String(node?.route ?? ''),
      title: String(node?.title ?? ''),
      scenarioId: String(bundle.scenario?.scenario_id ?? ''),
      scenarioPath: bundle.path,
      outputPath: String(bundle.capture?.output ?? ''),
      openTarget: scenarioOpenTarget(bundle.scenario),
    });
  }

  const limit = toInteger(options.limit, 0);
  return {
    tasks: limit > 0 ? selected.slice(0, limit) : selected,
    skipped,
  };
}

function parseResultOutput(rawStdout) {
  const trimmed = String(rawStdout ?? '').trim();
  if (!trimmed) {
    return null;
  }
  try {
    return JSON.parse(trimmed);
  } catch {
    return null;
  }
}

function runScenarioTask(task, options = {}) {
  const args = [WEB_SCENARIO_SCRIPT, '--scenario', task.scenarioPath];
  if (options.refreshAuth) {
    args.push('--refresh-auth');
  }
  if (options.login) {
    args.push('--login', options.login);
  }
  if (options.password) {
    args.push('--password', options.password);
  }

  let perScenarioJsonPath = '';
  if (options.runDir) {
    perScenarioJsonPath = path.resolve(options.runDir, `${sanitizeFileToken(task.scenarioId)}.json`);
    ensureParentDir(perScenarioJsonPath);
    args.push('--json-output', perScenarioJsonPath);
  }

  const commandResult = spawnSync(process.execPath, args, {
    encoding: 'utf8',
    stdio: ['inherit', 'pipe', 'pipe'],
    env: process.env,
  });

  const parsed = parseResultOutput(commandResult.stdout)
    || (perScenarioJsonPath && fs.existsSync(perScenarioJsonPath)
      ? parseJson(fs.readFileSync(perScenarioJsonPath, 'utf8'), 'scenario result')
      : null);

  return {
    ok: Boolean(parsed?.ok) && commandResult.status === 0,
    status: commandResult.status,
    task,
    result: parsed,
    stdout: String(commandResult.stdout ?? '').trim(),
    stderr: String(commandResult.stderr ?? '').trim(),
    jsonOutputPath: perScenarioJsonPath,
  };
}

async function main() {
  const manifestPath = readOption('--manifest', '');
  const runDirInput = readOption('--run-dir', '');
  const reportPathInput = readOption('--json-output', '');
  if (!manifestPath) {
    fail('MANIFEST_REQUIRED', {
      message: '请传 --manifest <board.manifest.json>',
    });
  }

  const query = readOption('--query', '');
  const includeDynamic = hasFlag('--include-dynamic');
  const includeRedirect = hasFlag('--include-redirect');
  const includeEntry = hasFlag('--include-entry');
  const listOnly = hasFlag('--list-only');
  const failFast = hasFlag('--fail-fast');
  const limit = toInteger(readOption('--limit', ''), 0);
  const login = readOption('--login', process.env.PRODUCT_CANVAS_LOGIN || '');
  const password = readOption('--password', process.env.PRODUCT_CANVAS_PASSWORD || '');

  const { manifest, path: resolvedManifestPath } = loadManifest(manifestPath);
  const defaultRunDir = path.resolve(
    'out',
    'product-canvas',
    'runs',
    `web-batch-${new Date().toISOString().replace(/[:.]/g, '-').replace('T', '_').slice(0, 19)}`,
  );
  const runDir = path.resolve(runDirInput || defaultRunDir);
  ensureParentDir(path.join(runDir, 'placeholder'));

  const { tasks, skipped } = collectManifestScenarioTasks(manifest, {
    query,
    includeDynamic,
    includeRedirect,
    includeEntry,
    limit,
  });

  const summary = {
    ok: true,
    manifestPath: resolvedManifestPath,
    runDir,
    selectedCount: tasks.length,
    skippedCount: skipped.length,
    executedCount: 0,
    successCount: 0,
    failureCount: 0,
    skipped,
    results: [],
  };

  if (!listOnly) {
    let refreshAuthPending = hasFlag('--refresh-auth');
    for (const task of tasks) {
      const execution = runScenarioTask(task, {
        runDir,
        refreshAuth: refreshAuthPending,
        login,
        password,
      });
      refreshAuthPending = false;
      summary.results.push(execution);
      summary.executedCount += 1;
      if (execution.ok) {
        summary.successCount += 1;
      } else {
        summary.failureCount += 1;
        summary.ok = false;
        if (failFast) {
          break;
        }
      }
    }
  }

  if (listOnly) {
    summary.results = tasks.map((task) => ({ ok: true, task }));
  }

  if (reportPathInput) {
    const reportPath = path.resolve(reportPathInput);
    ensureParentDir(reportPath);
    fs.writeFileSync(reportPath, `${JSON.stringify(summary, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(summary, null, 2));
  if (!summary.ok && !listOnly) {
    process.exit(1);
  }
}

if (require.main === module) {
  main().catch((error) => {
    fail('WEB_SCENARIO_BATCH_FAILED', {
      message: error instanceof Error ? error.message : String(error),
    });
  });
}

module.exports = {
  collectManifestScenarioTasks,
  loadManifest,
  pickScenarioRef,
  scenarioHasPlaceholder,
  scenarioHasResolvedDynamicTarget,
  scenarioOpenTarget,
  shouldRunNode,
};
