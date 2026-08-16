#!/usr/bin/env node
'use strict';

const assert = require('assert');
const crypto = require('crypto');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const manifestPath = path.join(root, 'docs/audits/evidence/frontend-mvp-imp-288-protected-baseline.json');
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const divergences = [];
const sha256 = (absolute) => crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');

const predecessorPath = path.join(root, manifest.predecessor.path);
assert.ok(fs.existsSync(predecessorPath), `${manifest.predecessor.path}: predecessor ausente`);
assert.strictEqual(sha256(predecessorPath), manifest.predecessor.sha256, 'manifesto verificado do IMP-287 foi reescrito');

for (const listName of ['mutableBaselinePaths', 'allowedNewPaths']) {
  assert.ok(manifest[listName].every((relative) => !relative.endsWith('/')), `${listName} deve usar somente caminhos exatos`);
  assert.strictEqual(new Set(manifest[listName]).size, manifest[listName].length, `${listName} nao pode conter duplicatas`);
}

const forbiddenRoots = [
  'src/',
  'migrations/',
  'tests/',
  'docs/product/',
  'docs/governance/registry/',
  'docs/governance/contracts/openapi/',
];
for (const forbidden of forbiddenRoots) {
  assert.ok(!manifest.mutableBaselinePaths.some((relative) => relative.startsWith(forbidden)), `allowlist mutavel nao pode incluir ${forbidden}`);
  assert.ok(!manifest.allowedNewPaths.some((relative) => relative.startsWith(forbidden)), `allowlist nova nao pode incluir ${forbidden}`);
}

const exactRoutes = new Set([
  'frontend/src/app/api/auth/login/route.ts',
  'frontend/src/app/api/auth/logout/route.ts',
]);
for (const relative of manifest.allowedNewPaths.filter((item) => item.startsWith('frontend/src/app/api/'))) {
  assert.ok(exactRoutes.has(relative), `${relative}: Route Handler nao autorizado`);
}
assert.deepStrictEqual(
  [...manifest.allowedNewPaths.filter((item) => item.startsWith('frontend/src/app/api/'))].sort(),
  [...exactRoutes].sort(),
  'allowlist deve conter somente login/logout BFF',
);

const immutableHistorical = [
  'docs/audits/evidence/frontend-mvp-imp-284-protected-baseline.json',
  'docs/audits/evidence/frontend-mvp-imp-285-protected-baseline.json',
  'docs/audits/evidence/frontend-mvp-imp-286-protected-baseline.json',
  'docs/audits/evidence/frontend-mvp-imp-287-protected-baseline.json',
  'docs/audits/reports/frontend-mvp-imp-284-scaffold-report-2026-08-12.md',
  'docs/audits/reports/frontend-mvp-imp-285-test-harness-report-2026-08-13.md',
  'docs/audits/reports/frontend-mvp-imp-286-design-foundation-report-2026-08-13.md',
  'docs/audits/reports/frontend-mvp-imp-287-openapi-client-report-2026-08-13.md',
  'frontend/src/lib/api/openapi.generated.ts',
];
for (const relative of immutableHistorical) {
  assert.ok(!manifest.mutableBaselinePaths.includes(relative), `${relative} deve permanecer historico`);
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
  if (!expectedPaths.has(relative)) divergences.push(`${relative}: caminho extra fora da allowlist do IMP-288`);
}

assert.strictEqual(divergences.length, 0, `escopo protegido do IMP-288 divergiu:\n${divergences.join('\n')}`);
console.log(`IMP-288 scope: predecessor verificado, ${protectedCount} arquivos protegidos e delta exato commitado/worktree, 0 divergencia.`);
