import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { afterEach, test } from 'node:test';

const require = createRequire(import.meta.url);
const support = require('../skills/product-canvas/scripts/web_cli_support.js');

const originalArgv = [...process.argv];

afterEach(() => {
  process.argv = [...originalArgv];
});

function setArgv(args) {
  process.argv = ['node', 'web_cli_support.js', ...args];
}

function createScenarioFile(payload) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'product-canvas-web-'));
  const scenarioPath = path.join(tempDir, 'scenario.json');
  fs.writeFileSync(scenarioPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8');
  return {
    scenarioPath,
    tempDir,
    cleanup() {
      fs.rmSync(tempDir, { recursive: true, force: true });
    },
  };
}

test('readWebTargetOptions reads scenario target defaults', () => {
  const fixture = createScenarioFile({
    scenario_id: 'admin-dashboard',
    engine: 'web-playwright-cli',
    target: {
      base_url: 'https://admin.example.com',
      auth_surface: 'admin',
      auth_profile: 'prod-admin',
      storage_state: '../auth/prod-admin.session.json',
      timeout_ms: 45000,
      browser_channel: 'chrome',
      viewport_size: '1440,1000',
      full_page: true,
    },
    capture: {
      output: '../screenshots/admin-dashboard.png',
    },
  });

  try {
    setArgv([]);
    const options = support.readWebTargetOptions({ scenarioPath: fixture.scenarioPath });

    assert.equal(options.baseUrl, 'https://admin.example.com');
    assert.equal(options.authSurface, 'admin');
    assert.equal(options.authProfile, 'prod-admin');
    assert.equal(options.storageStateInput, '../auth/prod-admin.session.json');
    assert.equal(options.waitTimeoutMsInput, 45000);
    assert.equal(options.browserChannel, 'chrome');
    assert.equal(options.viewportSize, '1440,1000');
    assert.equal(options.captureOutputInput, '../screenshots/admin-dashboard.png');
    assert.equal(options.fullPage, true);
  } finally {
    fixture.cleanup();
  }
});

test('resolveStorageStatePath uses scenario-relative explicit path', () => {
  const fixture = createScenarioFile({
    scenario_id: 'admin-dashboard',
    engine: 'web-playwright-cli',
  });

  try {
    const resolved = support.resolveStorageStatePath({
      scenarioPath: fixture.scenarioPath,
      storageStateInput: '../auth/prod-admin.session.json',
      authProfile: 'ignored-profile',
    });

    assert.equal(resolved, path.resolve(fixture.tempDir, '../auth/prod-admin.session.json'));
  } finally {
    fixture.cleanup();
  }
});

test('resolveStorageStatePath derives output from auth profile when explicit path missing', () => {
  const resolved = support.resolveStorageStatePath({
    authProfile: 'EggTurtle Prod Admin',
  });

  assert.equal(
    resolved,
    path.resolve('out', 'product-canvas', 'auth', 'eggturtle-prod-admin.session.json'),
  );
});

test('deriveScenarioUrl joins base url with open step target', () => {
  const url = support.deriveScenarioUrl({
    target: {
      base_url: 'https://admin.example.com',
    },
    steps: [
      {
        action: 'open',
        target: '/dashboard',
      },
    ],
  });

  assert.equal(url, 'https://admin.example.com/dashboard');
});

test('deriveWaitSelector prefers selector assertion and falls back to text assertion', () => {
  const selector = support.deriveWaitSelector({
    assertions: [
      {
        type: 'selector',
        selector: 'text=平台概况',
      },
    ],
  });
  const textSelector = support.deriveWaitSelector({
    assertions: [
      {
        type: 'text',
        value: '用户总数',
      },
    ],
  });

  assert.equal(selector, 'text=平台概况');
  assert.equal(textSelector, 'text=用户总数');
});

test('parseSetCookieHeader parses admin auth cookie into Playwright storage format', () => {
  const cookie = support.parseSetCookieHeader(
    'eggturtle.admin.access_token=token-123; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=3600',
    'https://admin.example.com',
  );

  assert.equal(cookie.name, 'eggturtle.admin.access_token');
  assert.equal(cookie.value, 'token-123');
  assert.equal(cookie.domain, 'admin.example.com');
  assert.equal(cookie.path, '/');
  assert.equal(cookie.httpOnly, true);
  assert.equal(cookie.secure, true);
  assert.equal(cookie.sameSite, 'Lax');
  assert.ok(cookie.expires > Math.floor(Date.now() / 1000));
});

test('buildCookieStorageState ignores empty legacy clear cookies', () => {
  const storageState = support.buildCookieStorageState([
    'eggturtle.admin.access_token=token-123; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=3600',
    'eggturtle.admin.session=; Expires=Thu, 01 Jan 1970 00:00:00 GMT; Path=/; HttpOnly; Secure; SameSite=Lax',
  ], 'https://admin.example.com');

  assert.equal(storageState.cookies.length, 1);
  assert.equal(storageState.cookies[0].name, 'eggturtle.admin.access_token');
});
