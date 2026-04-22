#!/usr/bin/env node

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

function resolveAutoMiniprogramRoot() {
  const explicit = readOption('--auto-miniprogram-root').trim();
  const fromEnv = process.env.AUTO_MINIPROGRAM_ROOT?.trim() || '';
  const candidate = explicit || fromEnv || '/Volumes/DATABASE/code/auto-miniprogram';
  return path.resolve(candidate);
}

function runNodeScript(scriptPath, args) {
  return spawnSync(process.execPath, [scriptPath, ...args], {
    encoding: 'utf8',
    stdio: ['inherit', 'pipe', 'pipe'],
  });
}

function runPnpm(autoMiniprogramRoot, args) {
  return spawnSync('pnpm', ['--dir', autoMiniprogramRoot, ...args], {
    encoding: 'utf8',
    stdio: ['inherit', 'pipe', 'pipe'],
  });
}

function parseJsonOutput(raw, context) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${context} 输出不是合法 JSON:\n${raw}\n${error instanceof Error ? error.message : String(error)}`);
  }
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

function main() {
  const skillRoot = path.resolve(__dirname, '..');
  const resolverScript = path.join(skillRoot, 'scripts', 'resolve_miniapp_target.js');
  const autoMiniprogramRoot = resolveAutoMiniprogramRoot();
  const inputPath = readOption('--path').trim();
  const jsonOutputPath = readOption('--json-output').trim();
  const screenshotOutput = readOption('--output').trim();

  if (!fs.existsSync(resolverScript)) {
    fail('RESOLVER_SCRIPT_NOT_FOUND', { resolverScript });
  }

  if (!fs.existsSync(path.join(autoMiniprogramRoot, 'package.json'))) {
    fail('AUTO_MINIPROGRAM_ROOT_NOT_FOUND', {
      autoMiniprogramRoot,
      message: '找不到 auto-miniprogram 仓库，请显式传 --auto-miniprogram-root 或设置 AUTO_MINIPROGRAM_ROOT。',
    });
  }

  const resolveArgs = inputPath ? ['--path', inputPath] : [];
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
