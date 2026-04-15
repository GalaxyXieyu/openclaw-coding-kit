#!/usr/bin/env node

const path = require('node:path');
const fs = require('node:fs');
const {
  appendBrokerTargetArgs,
  ensureParentDir,
  fail,
  hasFlag,
  parseJsonOutput,
  readMiniappTargetOptions,
  readOption,
  resolveAutoMiniprogramRoot,
  runNodeScript,
  runPnpm,
} = require('./miniapp_cli_support');

function main() {
  const skillRoot = path.resolve(__dirname, '..');
  const resolverScript = path.join(skillRoot, 'scripts', 'resolve_miniapp_target.js');
  const autoMiniprogramRoot = resolveAutoMiniprogramRoot();
  const inputPath = readOption('--path').trim();
  const scenarioPath = readOption('--scenario').trim();
  const jsonOutputPath = readOption('--json-output').trim();
  const screenshotOutput = readOption('--output').trim();

  const resolvedScenarioPath = scenarioPath ? path.resolve(scenarioPath) : '';
  if (resolvedScenarioPath && !fs.existsSync(resolvedScenarioPath)) {
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
  const brokerArgs = [
    'run',
    '--silent',
    'broker:probe',
    '--',
    '--path',
    resolvedTarget.worktreeRoot || resolvedTarget.appRoot,
    '--json',
  ];
  appendBrokerTargetArgs(brokerArgs, targetOptions);

  if (screenshotOutput) {
    brokerArgs.push('--output', path.resolve(screenshotOutput));
  }
  if (hasFlag('--build')) {
    brokerArgs.push('--build');
  }
  if (hasFlag('--reconnect')) {
    brokerArgs.push('--reconnect');
  }
  if (hasFlag('--no-screenshot')) {
    brokerArgs.push('--no-screenshot');
  }

  const probeResult = runPnpm(autoMiniprogramRoot, brokerArgs);
  const rawProbeOutput = probeResult.stdout.trim() || probeResult.stderr.trim();
  if (!rawProbeOutput) {
    fail('BROKER_PROBE_NO_OUTPUT', { autoMiniprogramRoot, brokerArgs });
  }

  const brokerProbe = parseJsonOutput(rawProbeOutput, 'broker:probe');
  const result = {
    ok: resolvedTarget.ok && Boolean(brokerProbe.ok),
    autoMiniprogramRoot,
    scenarioPath: resolvedScenarioPath || null,
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
  };

  if (jsonOutputPath) {
    const outputFile = path.resolve(jsonOutputPath);
    ensureParentDir(outputFile);
    fs.writeFileSync(outputFile, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(result, null, 2));

  if (probeResult.status !== 0 || !result.ok) {
    process.exit(1);
  }
}

main();
