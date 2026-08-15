#!/usr/bin/env node
'use strict';

const assert = require('assert');
const crypto = require('crypto');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const manifestPath = path.join(root, 'docs/audits/evidence/frontend-mvp-imp-303-protected-baseline.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const divergences = [];
const sha256 = (absolute) => crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
const parseStatusPath = (line) => line.replace(/^.{2}\s?/, '').replace(/\\/g, '/');

assert.strictEqual(manifest.baselineCount, 401, 'baseline IMP-303 deve conter 401 paths');
assert.strictEqual(manifest.mutableBaselinePaths.length, 66, 'allowlist mutavel IMP-303 deve ter 66 paths');
assert.strictEqual(manifest.protectedBaselineCount, 335, 'IMP-303 deve proteger 335 paths');
assert.strictEqual(manifest.allowedNewPaths.length, 3, 'allowlist nova IMP-303 deve ter 3 paths');
assert.strictEqual(manifest.expectedFinalCount, 404, 'inventario final IMP-303 deve ter 404 paths');

const predecessorPath = path.join(root, manifest.predecessor.path);
assert.ok(fs.existsSync(predecessorPath), `${manifest.predecessor.path}: predecessor ausente`);
assert.strictEqual(sha256(predecessorPath), manifest.predecessor.sha256, 'manifesto verificado do IMP-302 foi reescrito');

for (const listName of ['mutableBaselinePaths', 'allowedNewPaths']) {
  assert.ok(manifest[listName].every((relative) => !relative.endsWith('/')), `${listName} deve usar somente caminhos exatos`);
  assert.strictEqual(new Set(manifest[listName]).size, manifest[listName].length, `${listName} nao pode conter duplicatas`);
}

for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/']) {
  assert.ok(!manifest.mutableBaselinePaths.some((relative) => relative.startsWith(forbidden)), `allowlist mutavel nao pode incluir ${forbidden}`);
  assert.ok(!manifest.allowedNewPaths.some((relative) => relative.startsWith(forbidden)), `allowlist nova nao pode incluir ${forbidden}`);
}

for (const immutable of [
  'frontend/package-lock.json',
  'frontend/src/lib/api/openapi.generated.ts',
  'frontend/src/lib/bff/backend.server.ts',
  'frontend/src/lib/bff/context.server.ts',
  'frontend/src/lib/bff/session.server.ts',
  'docs/governance/registry/identifier-registry.json',
  'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json',
]) {
  assert.ok(!manifest.mutableBaselinePaths.includes(immutable), `${immutable} deve permanecer imutavel`);
  assert.ok(!manifest.allowedNewPaths.includes(immutable), `${immutable} nao pode ser reemitido`);
}

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
], 'IMP-303 nao pode criar Route Handler publico novo');

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
const worktreePaths = new Set(status.split(/\r?\n/).filter(Boolean).map(parseStatusPath));
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
  if (!expectedPaths.has(relative)) divergences.push(`${relative}: caminho extra fora da allowlist IMP-303`);
}

assert.strictEqual(protectedCount, manifest.protectedBaselineCount, 'contagem protegida IMP-303');
assert.strictEqual(actualPaths.size, manifest.expectedFinalCount, 'contagem do delta final IMP-303');
assert.strictEqual(divergences.length, 0, `escopo protegido IMP-303 divergiu:\n${divergences.join('\n')}`);
console.log(`IMP-303 scope: predecessor verificado, ${protectedCount} arquivos protegidos e delta exato commitado/worktree (${actualPaths.size} paths), 0 divergencia.`);
