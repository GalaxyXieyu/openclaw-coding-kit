import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createRequire } from 'node:module';
import { afterEach, test } from 'node:test';

const require = createRequire(import.meta.url);
const support = require('../skills/product-canvas/scripts/miniapp_cli_support.js');

const originalArgv = [...process.argv];

afterEach(() => {
  process.argv = [...originalArgv];
});

function setArgv(args) {
  process.argv = ['node', 'miniapp_cli_support.js', ...args];
}

function createScenarioTargetFile(target) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'product-canvas-miniapp-'));
  const scenarioPath = path.join(tempDir, 'scenario.json');
  fs.writeFileSync(
    scenarioPath,
    `${JSON.stringify({ scenario_id: 'demo', target }, null, 2)}\n`,
    'utf8',
  );
  return {
    scenarioPath,
    cleanup() {
      fs.rmSync(tempDir, { recursive: true, force: true });
    },
  };
}

test('readMiniappTargetOptions reads scenario target defaults', () => {
  const fixture = createScenarioTargetFile({
    project_root: '/tmp/demo-project',
    target_name: 'live-target',
    ide_port: 37768,
    automator_port: 60323,
    label: 'demo-live',
  });

  try {
    setArgv([]);
    const options = support.readMiniappTargetOptions({ scenarioPath: fixture.scenarioPath });

    assert.equal(options.inputPath, '/tmp/demo-project');
    assert.equal(options.targetName, 'live-target');
    assert.equal(options.idePort, 37768);
    assert.equal(options.automatorPort, 60323);
    assert.equal(options.label, 'demo-live');
    assert.equal(options.scenarioPath, fixture.scenarioPath);
  } finally {
    fixture.cleanup();
  }
});

test('readMiniappTargetOptions prefers CLI overrides over scenario target defaults', () => {
  const fixture = createScenarioTargetFile({
    project_root: '/tmp/demo-project',
    target_name: 'scenario-target',
    ide_port: 37768,
    automator_port: 60323,
    label: 'scenario-live',
  });

  try {
    setArgv([
      '--path',
      '/tmp/cli-project',
      '--target-name',
      'cli-target',
      '--ide-port',
      '41000',
      '--automator-port',
      '42000',
      '--label',
      'cli-live',
    ]);
    const options = support.readMiniappTargetOptions({ scenarioPath: fixture.scenarioPath });

    assert.equal(options.inputPath, '/tmp/cli-project');
    assert.equal(options.targetName, 'cli-target');
    assert.equal(options.idePort, 41000);
    assert.equal(options.automatorPort, 42000);
    assert.equal(options.label, 'cli-live');
  } finally {
    fixture.cleanup();
  }
});

test('appendBrokerTargetArgs only appends provided overrides', () => {
  const args = ['run', 'broker:probe'];

  support.appendBrokerTargetArgs(args, {
    targetName: 'main-live-37768',
    idePort: 37768,
    automatorPort: 60323,
    label: 'eggturtle-live',
  });

  assert.deepEqual(args, [
    'run',
    'broker:probe',
    '--name',
    'main-live-37768',
    '--ide-port',
    '37768',
    '--automator-port',
    '60323',
    '--label',
    'eggturtle-live',
  ]);
});

test('buildScenarioEnv injects explicit runtime overrides', () => {
  const env = support.buildScenarioEnv(
    { EXISTING_FLAG: '1' },
    { appRoot: '/tmp/demo/apps/miniapp' },
    {
      idePort: 37768,
      automatorPort: 60323,
      label: 'eggturtle-live',
    },
  );

  assert.equal(env.EXISTING_FLAG, '1');
  assert.equal(env.MINIAPP_PROJECT_ROOT, '/tmp/demo/apps/miniapp');
  assert.equal(env.WECHAT_DEVTOOLS_IDE_PORT, '37768');
  assert.equal(env.WECHAT_DEVTOOLS_AUTOMATOR_PORT, '60323');
  assert.equal(env.WECHAT_DEVTOOLS_LABEL, 'eggturtle-live');
});
