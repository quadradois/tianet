#!/usr/bin/env node
'use strict';

const assert = require('assert');
const crypto = require('crypto');
const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', '..');
const manifestPath = path.join(
  root,
  'docs/audits/evidence/frontend-mvp-imp-285-protected-baseline.json',
);
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const divergences = [];
const sha256 = (absolute) => crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');

const predecessorPath = path.join(root, manifest.predecessor.path);
assert.ok(fs.existsSync(predecessorPath), `${manifest.predecessor.path}: predecessor ausente`);
assert.strictEqual(
  sha256(predecessorPath),
  manifest.predecessor.sha256,
  'manifesto certificado do IMP-284 foi reescrito',
);

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

for (const forbidden of ['src/', 'migrations/', 'tests/', 'docs/product/', 'docs/governance/registry/', 'docs/governance/contracts/openapi/']) {
  assert.ok(
    !manifest.mutableBaselinePaths.some((relative) => relative.startsWith(forbidden)),
    `allowlist mutavel nao pode incluir ${forbidden}`,
  );
  assert.ok(
    !manifest.allowedNewPaths.some((relative) => relative.startsWith(forbidden)),
    `allowlist nova nao pode incluir ${forbidden}`,
  );
}

const baselinePaths = new Set(Object.keys(manifest.files));
const isAllowedNew = (relative) => manifest.allowedNewPaths.some((allowed) => (
  allowed.endsWith('/') ? relative.startsWith(allowed) : relative === allowed
));
const status = childProcess.execFileSync(
  'git',
  ['status', '--porcelain=v1', '--untracked-files=all'],
  { cwd: root, encoding: 'utf8' },
);
for (const line of status.split(/\r?\n/).filter(Boolean)) {
  const relative = line.slice(3).replace(/\\/g, '/');
  if (!baselinePaths.has(relative) && !isAllowedNew(relative)) {
    divergences.push(`${relative}: caminho novo/modificado fora da allowlist do IMP-285`);
  }
}

assert.strictEqual(
  divergences.length,
  0,
  `escopo protegido do IMP-285 divergiu:\n${divergences.join('\n')}`,
);
console.log(
  `IMP-285 scope: predecessor verificado, ${protectedCount} arquivos protegidos e inventario do worktree, 0 divergencia.`,
);
