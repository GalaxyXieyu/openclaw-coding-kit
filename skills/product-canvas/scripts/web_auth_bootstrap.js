#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const {
  bootstrapAdminStorageState,
  ensureParentDir,
  fail,
  readOption,
  resolveStorageStatePath,
} = require('./web_cli_support');

async function main() {
  const baseUrl = readOption('--base-url').trim();
  const authSurface = readOption('--auth-surface', 'admin').trim() || 'admin';
  const authProfile = readOption('--auth-profile', 'default').trim() || 'default';
  const jsonOutputPath = readOption('--json-output').trim();
  const storageStateInput = readOption('--storage-state').trim();
  const login = readOption('--login', process.env.PRODUCT_CANVAS_LOGIN || '').trim();
  const password = readOption('--password', process.env.PRODUCT_CANVAS_PASSWORD || '').trim();

  if (!baseUrl) {
    fail('BASE_URL_REQUIRED', {
      message: '请传 --base-url <https://host>',
    });
  }

  const storageStatePath = resolveStorageStatePath({
    storageStateInput,
    authProfile,
  });

  const result = await bootstrapAdminStorageState({
    baseUrl,
    authSurface,
    authProfile,
    storageStatePath,
    login,
    password,
  });

  if (jsonOutputPath) {
    const outputFile = path.resolve(jsonOutputPath);
    ensureParentDir(outputFile);
    fs.writeFileSync(outputFile, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  }

  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  fail('WEB_AUTH_BOOTSTRAP_FAILED', {
    message: error instanceof Error ? error.message : String(error),
    details: error && typeof error === 'object' ? error.details : undefined,
  });
});
