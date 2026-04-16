#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const {
  bootstrapAdminStorageState,
  deriveScenarioUrl,
  deriveWaitForTimeoutMs,
  deriveWaitSelector,
  deriveWaitTimeoutMs,
  ensureParentDir,
  fail,
  hasFlag,
  readWebTargetOptions,
  resolveCaptureOutputPath,
  resolveStorageStatePath,
  runNpx,
} = require('./web_cli_support');

async function main() {
  const scenarioPath = process.argv.includes('--scenario')
    ? process.argv[process.argv.indexOf('--scenario') + 1]
    : '';
  const jsonOutputPath = process.argv.includes('--json-output')
    ? process.argv[process.argv.indexOf('--json-output') + 1]
    : '';

  if (!scenarioPath || !String(scenarioPath).trim()) {
    fail('SCENARIO_PATH_REQUIRED', {
      message: '请传 --scenario <scenario.json>',
    });
  }

  const options = readWebTargetOptions({
    scenarioPath: String(scenarioPath).trim(),
  });
  const scenario = options.rawScenario;
  if (!scenario) {
    fail('SCENARIO_LOAD_FAILED', { scenarioPath });
  }

  if (scenario.engine !== 'web-playwright-cli') {
    fail('UNSUPPORTED_SCENARIO_ENGINE', {
      scenarioPath: options.scenarioPath,
      engine: scenario.engine,
      expected: 'web-playwright-cli',
    });
  }

  if (!options.baseUrl) {
    fail('BASE_URL_REQUIRED', {
      scenarioPath: options.scenarioPath,
      message: 'scenario.target.base_url 或 --base-url 必填',
    });
  }

  const storageStatePath = resolveStorageStatePath({
    scenarioPath: options.scenarioPath,
    storageStateInput: options.storageStateInput,
    authProfile: options.authProfile || scenario.scenario_id,
  });
  const outputPath = resolveCaptureOutputPath({
    scenarioPath: options.scenarioPath,
    outputPathInput: options.outputPathInput,
    captureOutputInput: options.captureOutputInput,
  });

  if (!outputPath) {
    fail('CAPTURE_OUTPUT_REQUIRED', {
      scenarioPath: options.scenarioPath,
      message: 'scenario.capture.output 或 --output 必填',
    });
  }

  let authBootstrap = null;
  const needBootstrap = hasFlag('--refresh-auth') || !fs.existsSync(storageStatePath);
  if (needBootstrap && options.authSurface === 'admin') {
    authBootstrap = await bootstrapAdminStorageState({
      baseUrl: options.baseUrl,
      authSurface: options.authSurface,
      authProfile: options.authProfile || scenario.scenario_id,
      storageStatePath,
      login: options.login,
      password: options.password,
    }).catch((error) => {
      fail('ADMIN_AUTH_BOOTSTRAP_FAILED', {
        message: error instanceof Error ? error.message : String(error),
        details: error && typeof error === 'object' ? error.details : undefined,
      });
    });
  }

  if (!fs.existsSync(storageStatePath)) {
    fail('STORAGE_STATE_NOT_FOUND', {
      storageStatePath,
      message: '未找到登录态文件。可传 --login/--password 触发首次 bootstrap，或显式传 --storage-state。',
    });
  }

  const scenarioUrl = deriveScenarioUrl(scenario, { baseUrl: options.baseUrl });
  const waitSelector = deriveWaitSelector(scenario, options.waitSelectorInput);
  const waitForTimeoutMs = deriveWaitForTimeoutMs(scenario, options.waitForTimeoutMsInput);
  const timeoutMs = deriveWaitTimeoutMs(scenario, options.waitTimeoutMsInput);

  ensureParentDir(outputPath);
  ensureParentDir(storageStatePath);

  const args = [
    'playwright',
    'screenshot',
    '--channel',
    options.browserChannel,
    '--load-storage',
    storageStatePath,
    '--save-storage',
    storageStatePath,
    '--viewport-size',
    options.viewportSize,
    '--timeout',
    String(timeoutMs),
  ];

  if (options.fullPage) {
    args.push('--full-page');
  }
  if (waitSelector) {
    args.push('--wait-for-selector', waitSelector);
  }
  if (waitForTimeoutMs > 0) {
    args.push('--wait-for-timeout', String(waitForTimeoutMs));
  }

  args.push(scenarioUrl, outputPath);

  const commandResult = runNpx(args);
  const result = {
    ok: commandResult.status === 0 && fs.existsSync(outputPath),
    scenarioId: scenario.scenario_id || null,
    scenarioPath: options.scenarioPath,
    url: scenarioUrl,
    outputPath,
    storageStatePath,
    waitSelector: waitSelector || null,
    waitForTimeoutMs,
    timeoutMs,
    browserChannel: options.browserChannel,
    viewportSize: options.viewportSize,
    authBootstrap,
    command: ['npx', ...args],
    stdout: commandResult.stdout.trim(),
    stderr: commandResult.stderr.trim(),
  };

  if (jsonOutputPath && String(jsonOutputPath).trim()) {
    const outputFile = path.resolve(String(jsonOutputPath).trim());
    ensureParentDir(outputFile);
    fs.writeFileSync(outputFile, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(result, null, 2));

  if (!result.ok) {
    process.exit(1);
  }
}

main().catch((error) => {
  fail('WEB_SCENARIO_RUNNER_FAILED', {
    message: error instanceof Error ? error.message : String(error),
  });
});
