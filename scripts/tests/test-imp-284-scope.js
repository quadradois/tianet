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
  'docs/audits/evidence/frontend-mvp-imp-284-protected-baseline.json',
);
const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
const divergences = [];

for (const [relative, expected] of Object.entries(manifest.files)) {
  const absolute = path.join(root, relative);
  if (!fs.existsSync(absolute)) {
    divergences.push(`${relative}: ausente`);
    continue;
  }
  const actual = crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
  if (actual !== expected) divergences.push(`${relative}: ${actual} != ${expected}`);
}

const baselinePaths = new Set(manifest.baselineWorktreePaths);
const isAllowedImp284 = (relative) => manifest.allowedImp284Paths.some((allowed) => (
  allowed.endsWith('/') ? relative.startsWith(allowed) : relative === allowed
));
const status = childProcess.execFileSync(
  'git',
  ['status', '--porcelain=v1', '--untracked-files=all'],
  { cwd: root, encoding: 'utf8' },
);
for (const line of status.split(/\r?\n/).filter(Boolean)) {
  const relative = line.slice(3).replace(/\\/g, '/');
  if (!baselinePaths.has(relative) && !isAllowedImp284(relative)) {
    divergences.push(`${relative}: caminho novo/modificado fora da allowlist do IMP-284`);
  }
}

assert.strictEqual(
  divergences.length,
  0,
  `arquivos preexistentes protegidos divergiram:\n${divergences.join('\n')}`,
);
console.log(`IMP-284 scope: ${Object.keys(manifest.files).length} arquivos protegidos e inventario do worktree, 0 divergencia.`);
