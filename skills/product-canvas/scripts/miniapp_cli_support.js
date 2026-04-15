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

function runPnpm(autoMiniprogramRoot, args, env = process.env) {
  return spawnSync('pnpm', ['--dir', autoMiniprogramRoot, ...args], {
    encoding: 'utf8',
    stdio: ['inherit', 'pipe', 'pipe'],
    env,
  });
}

function parseJsonOutput(raw, context) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw new Error(`${context} 输出不是合法 JSON:\n${raw}\n${error instanceof Error ? error.message : String(error)}`);
  }
}

function readJsonFile(filePath, context) {
  return parseJsonOutput(fs.readFileSync(filePath, 'utf8').trim(), context);
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

function readResultPayload(commandResult, fallbackPath, context) {
  if (fallbackPath && fs.existsSync(fallbackPath)) {
    return readJsonFile(fallbackPath, context);
  }

  const raw = commandResult.stdout.trim() || commandResult.stderr.trim();
  if (!raw) {
    throw new Error(`${context} 没有输出`);
  }
  return parseJsonOutput(raw, context);
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

function toPort(value) {
  const normalized = String(value ?? '').trim();
  if (!normalized) {
    return undefined;
  }

  const parsed = Number(normalized);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    return undefined;
  }
  return parsed;
}

function pickPort(...values) {
  for (const value of values) {
    const parsed = toPort(value);
    if (parsed !== undefined) {
      return parsed;
    }
  }
  return undefined;
}

function readScenarioTargetConfig(scenarioPath) {
  if (!scenarioPath) {
    return {
      rawScenario: null,
      target: {},
      inputPath: '',
      targetName: '',
      idePort: undefined,
      automatorPort: undefined,
      label: '',
    };
  }

  const rawScenario = readJsonFile(scenarioPath, 'scenario');
  const target = rawScenario && typeof rawScenario.target === 'object' && !Array.isArray(rawScenario.target)
    ? rawScenario.target
    : {};

  return {
    rawScenario,
    target,
    inputPath: pickText(
      target.path_input,
      target.pathInput,
      target.path,
      target.project_root,
      target.projectRoot,
      target.worktree_root,
      target.worktreeRoot,
      target.app_root,
      target.appRoot,
    ),
    targetName: pickText(target.target_name, target.targetName, target.name),
    idePort: pickPort(target.ide_port, target.idePort),
    automatorPort: pickPort(target.automator_port, target.automatorPort),
    label: pickText(target.label),
  };
}

function readMiniappTargetOptions(options = {}) {
  const scenarioPath = options.scenarioPath ? path.resolve(options.scenarioPath) : '';
  const scenarioTarget = readScenarioTargetConfig(scenarioPath);

  return {
    scenarioPath: scenarioPath || null,
    scenarioTarget: scenarioTarget.target,
    inputPath: pickText(readOption('--path', ''), scenarioTarget.inputPath),
    targetName: pickText(readOption('--target-name', ''), scenarioTarget.targetName),
    idePort: pickPort(readOption('--ide-port', ''), scenarioTarget.idePort),
    automatorPort: pickPort(readOption('--automator-port', ''), scenarioTarget.automatorPort),
    label: pickText(readOption('--label', ''), scenarioTarget.label),
  };
}

function appendBrokerTargetArgs(args, targetOptions) {
  if (targetOptions.targetName) {
    args.push('--name', targetOptions.targetName);
  }
  if (targetOptions.idePort !== undefined) {
    args.push('--ide-port', String(targetOptions.idePort));
  }
  if (targetOptions.automatorPort !== undefined) {
    args.push('--automator-port', String(targetOptions.automatorPort));
  }
  if (targetOptions.label) {
    args.push('--label', targetOptions.label);
  }
}

function buildScenarioEnv(baseEnv, resolvedTarget, targetOptions) {
  const env = {
    ...baseEnv,
    MINIAPP_PROJECT_ROOT: resolvedTarget.appRoot,
  };

  if (targetOptions.idePort !== undefined) {
    env.WECHAT_DEVTOOLS_IDE_PORT = String(targetOptions.idePort);
  }
  if (targetOptions.automatorPort !== undefined) {
    env.WECHAT_DEVTOOLS_AUTOMATOR_PORT = String(targetOptions.automatorPort);
  }
  if (targetOptions.label) {
    env.WECHAT_DEVTOOLS_LABEL = targetOptions.label;
  }

  return env;
}

module.exports = {
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
};
