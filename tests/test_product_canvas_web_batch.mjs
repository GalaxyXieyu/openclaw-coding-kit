import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { afterEach, test } from 'node:test';

const require = createRequire(import.meta.url);
const batch = require('../skills/product-canvas/scripts/web_scenario_batch.js');

function makeScenario(tempDir, name, payload) {
  const scenarioPath = path.join(tempDir, `${name}.json`);
  fs.writeFileSync(scenarioPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  return scenarioPath;
}

function makeManifest(tempDir) {
  const loginScenario = makeScenario(tempDir, 'login', {
    scenario_id: 'login',
    engine: 'web-playwright-cli',
    steps: [{ action: 'open', target: '/login' }],
    capture: { output: '../screenshots/login.png' },
  });
  const dashboardScenario = makeScenario(tempDir, 'dashboard', {
    scenario_id: 'dashboard',
    engine: 'web-playwright-cli',
    steps: [{ action: 'open', target: '/dashboard' }],
    capture: { output: '../screenshots/dashboard.png' },
  });
  const redirectScenario = makeScenario(tempDir, 'settings', {
    scenario_id: 'settings',
    engine: 'web-playwright-cli',
    steps: [{ action: 'open', target: '/dashboard/settings' }],
    capture: { output: '../screenshots/settings.png' },
  });
  const dynamicScenario = makeScenario(tempDir, 'tenant-detail', {
    scenario_id: 'tenant-detail',
    engine: 'web-playwright-cli',
    steps: [{ action: 'open', target: '/dashboard/tenants/__AUTO_TENANTID__' }],
    capture: { output: '../screenshots/tenant-detail.png' },
  });

  return {
    nodes: [
      {
        node_id: 'admin-login',
        title: '后台登录',
        route: 'login',
        group: 'entry',
        board_meta: {
          route_mode: 'screen',
          requires_parameters: false,
        },
        card: {
          scenario_refs: [
            { scenario_id: 'login', scenario_path: loginScenario, engine: 'web-playwright-cli', role: 'target' },
          ],
        },
      },
      {
        node_id: 'admin-dashboard',
        title: '平台概况',
        route: 'dashboard',
        group: 'admin',
        board_meta: {
          route_mode: 'screen',
          requires_parameters: false,
        },
        card: {
          scenario_refs: [
            { scenario_id: 'dashboard', scenario_path: dashboardScenario, engine: 'web-playwright-cli', role: 'target' },
          ],
        },
      },
      {
        node_id: 'admin-settings',
        title: '设置入口',
        route: 'dashboard/settings',
        group: 'settings',
        board_meta: {
          route_mode: 'redirect',
          requires_parameters: false,
        },
        card: {
          scenario_refs: [
            { scenario_id: 'settings', scenario_path: redirectScenario, engine: 'web-playwright-cli', role: 'target' },
          ],
        },
      },
      {
        node_id: 'admin-tenant-detail',
        title: '用户详情',
        route: 'dashboard/tenants/[tenantId]',
        group: 'users',
        board_meta: {
          route_mode: 'screen',
          requires_parameters: true,
        },
        card: {
          scenario_refs: [
            { scenario_id: 'tenant-detail', scenario_path: dynamicScenario, engine: 'web-playwright-cli', role: 'target' },
          ],
        },
      },
    ],
  };
}

test('scenarioHasPlaceholder detects auto placeholders', () => {
  assert.equal(
    batch.scenarioHasPlaceholder({
      steps: [{ action: 'open', target: '/dashboard/tenants/__AUTO_TENANTID__' }],
    }),
    true,
  );
  assert.equal(
    batch.scenarioHasPlaceholder({
      steps: [{ action: 'open', target: '/dashboard' }],
    }),
    false,
  );
});

test('collectManifestScenarioTasks selects only stable default nodes', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'web-batch-'));
  try {
    const manifest = makeManifest(tempDir);
    const report = batch.collectManifestScenarioTasks(manifest, {});

    assert.equal(report.tasks.length, 1);
    assert.equal(report.tasks[0].nodeId, 'admin-dashboard');
    assert.deepEqual(
      report.skipped.map((item) => [item.node_id, item.reason]),
      [
        ['admin-login', 'entry-node'],
        ['admin-settings', 'redirect-only'],
        ['admin-tenant-detail', 'dynamic-route'],
      ],
    );
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});

test('collectManifestScenarioTasks respects include flags and query', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'web-batch-'));
  try {
    const manifest = makeManifest(tempDir);
    const report = batch.collectManifestScenarioTasks(manifest, {
      includeEntry: true,
      includeRedirect: true,
      includeDynamic: true,
      query: 'tenant',
    });

    assert.equal(report.tasks.length, 1);
    assert.equal(report.tasks[0].nodeId, 'admin-tenant-detail');
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});

test('resolved dynamic scenarios run by default once placeholders are replaced', () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'web-batch-'));
  try {
    const manifest = makeManifest(tempDir);
    const dynamicRef = manifest.nodes[3].card.scenario_refs[0];
    fs.writeFileSync(
      dynamicRef.scenario_path,
      `${JSON.stringify({
        scenario_id: 'tenant-detail',
        engine: 'web-playwright-cli',
        steps: [{ action: 'open', target: '/dashboard/tenants/t-demo' }],
        capture: { output: '../screenshots/tenant-detail.png' },
      }, null, 2)}\n`,
      'utf8',
    );

    const report = batch.collectManifestScenarioTasks(manifest, {});
    assert.equal(report.tasks.length, 2);
    assert.deepEqual(
      report.tasks.map((item) => item.nodeId),
      ['admin-dashboard', 'admin-tenant-detail'],
    );
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
});
