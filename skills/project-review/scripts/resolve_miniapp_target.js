#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

function readOption(name) {
  const index = process.argv.indexOf(name);
  if (index === -1) {
    return '';
  }
  return process.argv[index + 1] ?? '';
}

function hasProjectConfig(dirPath) {
  return fs.existsSync(path.join(dirPath, 'project.config.json'));
}

function runGit(cwd, args) {
  const result = spawnSync('git', args, {
    cwd,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
  });
  if (result.status !== 0) {
    return null;
  }
  return result.stdout.trim() || null;
}

function safeRealpath(targetPath) {
  try {
    return fs.realpathSync(targetPath);
  } catch {
    return targetPath;
  }
}

function resolveFromInput(inputPath) {
  const basePath = inputPath
    ? path.resolve(inputPath)
    : process.cwd();

  const directCandidates = [
    basePath,
    path.join(basePath, 'apps', 'miniapp'),
  ];

  for (const candidate of directCandidates) {
    if (hasProjectConfig(candidate)) {
      return safeRealpath(candidate);
    }
  }

  let current = basePath;
  while (true) {
    if (hasProjectConfig(current)) {
      return safeRealpath(current);
    }

    const nestedCandidate = path.join(current, 'apps', 'miniapp');
    if (hasProjectConfig(nestedCandidate)) {
      return safeRealpath(nestedCandidate);
    }

    const parent = path.dirname(current);
    if (parent === current) {
      break;
    }
    current = parent;
  }

  return null;
}

function resolveProjectRoot(appRoot) {
  const gitCommonDirRaw = runGit(appRoot, ['rev-parse', '--git-common-dir']);
  if (!gitCommonDirRaw) {
    return null;
  }

  const gitCommonDir = safeRealpath(path.resolve(appRoot, gitCommonDirRaw));
  if (path.basename(gitCommonDir) === '.git') {
    return path.dirname(gitCommonDir);
  }
  return gitCommonDir;
}

function main() {
  const inputPath = readOption('--path').trim();
  const appRoot = resolveFromInput(inputPath);

  if (!appRoot) {
    console.error(JSON.stringify({
      ok: false,
      error: 'MINIAPP_PATH_NOT_FOUND',
      message: '无法从输入路径或当前目录定位 miniapp。请显式传入项目根目录、worktree 根目录或 apps/miniapp 目录。',
      inputPath: inputPath || null,
      cwd: process.cwd(),
    }, null, 2));
    process.exit(1);
  }

  const worktreeRoot = runGit(appRoot, ['rev-parse', '--show-toplevel'])
    || path.resolve(appRoot, '..', '..');
  const projectRoot = resolveProjectRoot(appRoot) || safeRealpath(worktreeRoot);

  console.log(JSON.stringify({
    ok: true,
    inputPath: inputPath || null,
    cwd: process.cwd(),
    appRoot,
    worktreeRoot: safeRealpath(worktreeRoot),
    projectRoot: safeRealpath(projectRoot),
  }, null, 2));
}

main();
