#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const {
  appendBrokerTargetArgs,
  buildScenarioEnv,
  ensureParentDir,
  fail,
  hasFlag,
  parseJsonOutput,
  readMiniappTargetOptions,
  readOption,
  readResultPayload,
  resolveAutoMiniprogramRoot,
  runNodeScript,
  runPnpm,
} = require('./miniapp_cli_support');

function main() {
  const skillRoot = path.resolve(__dirname, '..');
  const resolverScript = path.join(skillRoot, 'scripts', 'resolve_miniapp_target.js');
  const autoMiniprogramRoot = resolveAutoMiniprogramRoot();
  const scenarioPath = readOption('--scenario').trim();
  const inputPath = readOption('--path').trim();
  const jsonOutputPath = readOption('--json-output').trim();
  const screenshotOutput = readOption('--output').trim();
  const internalJsonOutput = jsonOutputPath
    ? `${path.resolve(jsonOutputPath)}.runner.json`
    : path.resolve('out', 'product-canvas', 'tmp', `${Date.now()}-scenario-runner.json`);

  if (!scenarioPath) {
    fail('SCENARIO_PATH_REQUIRED', {
      message: '请传 --scenario <scenario.json>',
    });
  }

  const resolvedScenarioPath = path.resolve(scenarioPath);
  if (!fs.existsSync(resolvedScenarioPath)) {
    fail('SCENARIO_NOT_FOUND', { scenarioPath: resolvedScenarioPath });
  }

  if (!fs.existsSync(resolverScript)) {
    fail('RESOLVER_SCRIPT_NOT_FOUND', { resolverScript });
  }

  if (!fs.existsSync(path.join(autoMiniprogramRoot, 'package.json'))) {
    fail('AUTO_MINIPROGRAM_ROOT_NOT_FOUND', {
      autoMiniprogramRoot,
      message: '找不到 auto-miniprogram 仓库，请显式传 --auto-miniprogram-root 或设置 AUTO_MINIPROGRAM_ROOT。',
    });
  }

  const targetOptions = readMiniappTargetOptions({ scenarioPath: resolvedScenarioPath });
  const resolvePath = targetOptions.inputPath || inputPath;
  const resolveArgs = resolvePath ? ['--path', resolvePath] : [];
  const resolveResult = runNodeScript(resolverScript, resolveArgs);
  if (resolveResult.status !== 0) {
    fail('MINIAPP_TARGET_RESOLVE_FAILED', resolveResult.stderr.trim() || resolveResult.stdout.trim());
  }

  const resolvedTarget = parseJsonOutput(resolveResult.stdout.trim(), 'resolve_miniapp_target');
  let brokerProbe = null;

  if (!hasFlag('--skip-probe')) {
    const probeArgs = [
      'run',
      '--silent',
      'broker:probe',
      '--',
      '--path',
      resolvedTarget.worktreeRoot || resolvedTarget.appRoot,
      '--json',
      '--no-screenshot',
    ];
    appendBrokerTargetArgs(probeArgs, targetOptions);
    if (hasFlag('--build')) {
      probeArgs.push('--build');
    }
    if (hasFlag('--reconnect')) {
      probeArgs.push('--reconnect');
    }

    const probeResult = runPnpm(autoMiniprogramRoot, probeArgs, process.env);
    try {
      brokerProbe = readResultPayload(probeResult, '', 'broker:probe');
    } catch (error) {
      fail('BROKER_PROBE_PARSE_FAILED', {
        message: error instanceof Error ? error.message : String(error),
        stdout: probeResult.stdout.trim(),
        stderr: probeResult.stderr.trim(),
      });
    }
    if (probeResult.status !== 0 || !brokerProbe.ok) {
      fail('BROKER_PROBE_FAILED', {
        brokerProbe,
      });
    }
  }

  const scenarioArgs = [
    'run',
    '--silent',
    'devtools:scenario',
    '--',
    '--scenario',
    resolvedScenarioPath,
    '--json-output',
    internalJsonOutput,
  ];

  if (screenshotOutput) {
    scenarioArgs.push('--output', path.resolve(screenshotOutput));
  }
  if (hasFlag('--reconnect')) {
    scenarioArgs.push('--reconnect');
  }

  const commandResult = runPnpm(
    autoMiniprogramRoot,
    scenarioArgs,
    buildScenarioEnv(process.env, resolvedTarget, targetOptions),
  );

  let runnerResult;
  try {
    runnerResult = readResultPayload(commandResult, internalJsonOutput, 'devtools:scenario');
  } catch (error) {
    fail('SCENARIO_RUN_PARSE_FAILED', {
      message: error instanceof Error ? error.message : String(error),
      stdout: commandResult.stdout.trim(),
      stderr: commandResult.stderr.trim(),
      internalJsonOutput,
    });
  }

  const result = {
    ok: resolvedTarget.ok && Boolean(runnerResult.ok),
    autoMiniprogramRoot,
    scenarioPath: resolvedScenarioPath,
    targetOptions: {
      inputPath: resolvePath || null,
      targetName: targetOptions.targetName || null,
      idePort: targetOptions.idePort ?? null,
      automatorPort: targetOptions.automatorPort ?? null,
      label: targetOptions.label || null,
      scenarioPath: targetOptions.scenarioPath,
    },
    resolvedTarget,
    brokerProbe,
    runnerResult,
  };

  if (jsonOutputPath) {
    const outputFile = path.resolve(jsonOutputPath);
    ensureParentDir(outputFile);
    fs.writeFileSync(outputFile, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(result, null, 2));

  if (fs.existsSync(internalJsonOutput)) {
    fs.rmSync(internalJsonOutput, { force: true });
  }

  if (commandResult.status !== 0 || !result.ok) {
    process.exit(1);
  }
}

main();
