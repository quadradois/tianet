#!/usr/bin/env node
'use strict';

const assert = require('assert');
const crypto = require('crypto');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const manifestPath = path.join(root, 'docs/audits/evidence/frontend-mvp-imp-289-protected-baseline.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const divergences = [];
const sha256 = (absolute) => crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');

assert.strictEqual(manifest.baselineCount, 116, 'baseline IMP-289 deve conter 116 paths');
assert.strictEqual(manifest.mutableBaselinePaths.length, 13, 'allowlist mutavel IMP-289 deve ter 13 paths');
assert.strictEqual(manifest.protectedBaselineCount, 103, 'IMP-289 deve proteger 103 paths');
assert.strictEqual(manifest.allowedNewPaths.length, 34, 'allowlist nova IMP-289 deve ter 34 paths');
assert.strictEqual(manifest.expectedFinalCount, 150, 'inventario final IMP-289 deve ter 150 paths');

const predecessorPath = path.join(root, manifest.predecessor.path);
assert.ok(fs.existsSync(predecessorPath), `${manifest.predecessor.path}: predecessor ausente`);
assert.strictEqual(sha256(predecessorPath), manifest.predecessor.sha256, 'manifesto verificado do IMP-288 foi reescrito');

for (const listName of ['mutableBaselinePaths', 'allowedNewPaths']) {
  assert.ok(manifest[listName].every((relative) => !relative.endsWith('/')), `${listName} deve usar somente caminhos exatos`);
  assert.strictEqual(new Set(manifest[listName]).size, manifest[listName].length, `${listName} nao pode conter duplicatas`);
}

for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/']) {
  assert.ok(!manifest.mutableBaselinePaths.some((relative) => relative.startsWith(forbidden)), `allowlist mutavel nao pode incluir ${forbidden}`);
  assert.ok(!manifest.allowedNewPaths.some((relative) => relative.startsWith(forbidden)), `allowlist nova nao pode incluir ${forbidden}`);
}
assert.ok(!manifest.mutableBaselinePaths.includes('frontend/package-lock.json'), 'IMP-289 nao altera lockfile');

const routeRoot = path.join(root, 'frontend/src/app/api');
const routeFiles = [];
const pending = [routeRoot];
while (pending.length) {
  const current = pending.pop();
  for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
    const absolute = path.join(current, entry.name);
    if (entry.isDirectory()) pending.push(absolute);
    else if (entry.name === 'route.ts') routeFiles.push(path.relative(root, absolute).replace(/\\/g, '/'));
  }
}
assert.deepStrictEqual(routeFiles.sort(), [
  'frontend/src/app/api/auth/bootstrap/route.ts',
  'frontend/src/app/api/auth/login/route.ts',
  'frontend/src/app/api/auth/logout/route.ts',
], 'somente login, logout e bootstrap podem ser Route Handlers');

for (const relative of [
  'docs/audits/evidence/frontend-mvp-imp-288-protected-baseline.json',
  'docs/audits/reports/frontend-mvp-imp-288-session-bff-report-2026-08-13.md',
  'frontend/package-lock.json',
  'frontend/src/lib/api/openapi.generated.ts',
  'frontend/src/lib/bff/backend.server.ts',
  'frontend/src/lib/bff/session.server.ts',
]) {
  assert.ok(!manifest.mutableBaselinePaths.includes(relative), `${relative} deve permanecer imutavel`);
  assert.ok(!manifest.allowedNewPaths.includes(relative), `${relative} nao pode ser reemitido`);
}

const mutable = new Set(manifest.mutableBaselinePaths);
let protectedCount = 0;
for (const [relative, expected] of Object.entries(manifest.files)) {
  if (mutable.has(relative)) continue;
  protectedCount += 1;
  const absolute = path.join(root, relative);
  if (!fs.existsSync(absolute)) {
    divergences.push(`${relative}: ausente`);
    continue;
  }
  const actual = sha256(absolute);
  if (actual !== expected) divergences.push(`${relative}: ${actual} != ${expected}`);
}

const status = childProcess.execFileSync('git', ['status', '--porcelain=v1', '--untracked-files=all'], { cwd: root, encoding: 'utf8' });
const worktreePaths = new Set(status.split(/\r?\n/).filter(Boolean).map((line) => line.slice(3).replace(/\\/g, '/')));
const committedDelta = childProcess.execFileSync('git', ['diff', '--name-only', `${manifest.head}...HEAD`], { cwd: root, encoding: 'utf8' });
const actualPaths = new Set([
  ...committedDelta.split(/\r?\n/).filter(Boolean).map((line) => line.replace(/\\/g, '/')),
  ...worktreePaths,
]);
const expectedPaths = new Set([...Object.keys(manifest.files), ...manifest.allowedNewPaths]);

for (const relative of expectedPaths) {
  if (!actualPaths.has(relative)) divergences.push(`${relative}: ausente do inventario final`);
}
for (const relative of actualPaths) {
  if (!expectedPaths.has(relative)) divergences.push(`${relative}: caminho extra fora da allowlist do IMP-289`);
}

assert.strictEqual(divergences.length, 0, `escopo protegido do IMP-289 divergiu:\n${divergences.join('\n')}`);
console.log(`IMP-289 scope: predecessor verificado, ${protectedCount} arquivos protegidos e delta exato commitado/worktree, 0 divergencia.`);
