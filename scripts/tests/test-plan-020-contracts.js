#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');

const FILES = {
  plan: 'docs/implementation/plans/PLAN-020-fechamento-certificacao-backend-mvp.md',
  backlog: 'docs/implementation/backlogs/PLAN-020-execution-backlog.md',
  registry: 'docs/governance/registry/identifier-registry.json',
  packageJson: 'package.json',
};

const docs = Object.fromEntries(Object.entries(FILES).map(([key, rel]) => [key, read(rel)]));

const EXPECTED_IMPS = Array.from({ length: 20 }, (_, index) => `IMP-${254 + index}`);
const REQUIRED_IMP_FIELDS = [
  'Objetivo',
  'Componentes afetados',
  'Dependencias',
  'Criterios de conclusao',
  'Suite minima',
  'Status',
];
const REQUIRED_GATES = [
  'uv run pytest -q',
  'uv run ruff check .',
  'uv run black --check .',
  'uv run mypy src tests',
  'npm run docs:validate',
  'npm run docs:test',
  'node scripts/tests/test-plan-020-contracts.js',
  'npm run quality:migrations',
];

function assertTexto(doc, texto, contexto) {
  assert.ok(doc.includes(texto), `${contexto}: contrato ausente: ${texto}`);
}

function impBlocks(backlog) {
  const headings = [...backlog.matchAll(/^### (IMP-(\d{3})) -/gm)];
  return headings.map((heading, index) => {
    const next = index + 1 < headings.length ? headings[index + 1].index : backlog.indexOf('\n---', heading.index);
    const end = next === -1 ? backlog.length : next;
    return {
      id: heading[1],
      number: Number(heading[2]),
      text: backlog.slice(heading.index, end),
    };
  });
}

const contracts = {
  filesAndRegistry(source) {
    assertTexto(source.plan, '# PLAN-020 - Fechamento e Certificacao do Backend MVP', 'PLAN-020 H1');
    assertTexto(source.backlog, '# PLAN-020-EXEC - Backlog de Fechamento e Certificacao do Backend MVP', 'PLAN-020-EXEC H1');

    const registry = JSON.parse(source.registry);
    assert.ok(registry.namespaces.PLAN.ultimo >= 20, 'Registry PLAN.ultimo deve incluir PLAN-020');
  },

  noNewFunctionalEpic(source) {
    assertTexto(source.plan, 'Ele nao cria novo EPIC funcional', 'PLAN sem EPIC funcional novo');
    assertTexto(source.plan, 'Nao ha novo EPIC funcional, nova Capability, frontend', 'fora do escopo PLAN');
    assertTexto(source.backlog, 'sem criar novo EPIC funcional e sem iniciar\nfrontend', 'backlog sem EPIC/frontend');
    assert.ok(!/\bEPIC-011\b/.test(`${source.plan}\n${source.backlog}`), 'PLAN-020 nao deve emitir EPIC-011');
  },

  traceabilityMatrix(source) {
    for (let number = 1; number <= 10; number += 1) {
      const epic = `EPIC-${String(number).padStart(3, '0')}`;
      assertTexto(source.plan, epic, 'matriz backend MVP');
    }

    for (const flow of ['F1', 'F2', 'F3', 'F4', 'F5', 'F6']) {
      assert.ok(new RegExp(`^## ${flow} -`, 'm').test(source.plan), `fluxo E2E ${flow} ausente`);
    }
  },

  impRange(source) {
    const blocks = impBlocks(source.backlog);
    const ids = blocks.map((block) => block.id);
    assert.deepStrictEqual(ids, EXPECTED_IMPS, 'Backlog deve conter IMP-254..IMP-273 uma unica vez e em ordem');

    for (const block of blocks) {
      for (const field of REQUIRED_IMP_FIELDS) {
        assertTexto(block.text, `**${field}:**`, `${block.id} campo obrigatorio`);
      }
      assert.match(block.text, /\*\*Status:\*\* (?:Planejado|Concluido)\./, `${block.id} status invalido`);

      const dependencyLine = block.text.match(/^- \*\*Dependencias:\*\* (.+)$/m)?.[1] ?? '';
      for (const ref of dependencyLine.matchAll(/IMP-(\d{3})(?:\.\.IMP-(\d{3}))?/g)) {
        const start = Number(ref[1]);
        const end = Number(ref[2] ?? ref[1]);
        assert.ok(start >= 254 && end <= 273, `${block.id} depende de item fora do PLAN-020: ${ref[0]}`);
        assert.ok(end < block.number, `${block.id} depende de item futuro: ${ref[0]}`);
      }
    }
  },

  imp254Contract(source) {
    const block = impBlocks(source.backlog).find((item) => item.id === 'IMP-254');
    assert.ok(block, 'IMP-254 ausente');
    assertTexto(block.text, 'teste detecta ausencia de PLAN-020', 'IMP-254 criterios');
    assertTexto(block.text, '`IMP-254..IMP-273` incompleta', 'IMP-254 range');
    assertTexto(block.text, 'dependencia futura', 'IMP-254 dependencia futura');
    assertTexto(block.text, 'novo EPIC funcional\n  indevido', 'IMP-254 novo EPIC');
    assertTexto(block.text, 'remocao dos gates finais', 'IMP-254 gates finais');
    assertTexto(block.text, 'ausencia da propria suite no\n  `npm run docs:test`', 'IMP-254 docs:test');
    assertTexto(block.text, 'node scripts/tests/test-plan-020-contracts.js', 'IMP-254 suite');
  },

  gates(source) {
    for (const gate of REQUIRED_GATES) {
      assertTexto(source.plan, gate, 'gates PLAN-020');
      assertTexto(source.backlog, gate, 'gates PLAN-020-EXEC');
    }

    const packageJson = JSON.parse(source.packageJson);
    assertTexto(
      packageJson.scripts['docs:test'],
      'node scripts/tests/test-plan-020-contracts.js',
      'package.json docs:test',
    );
  },
};

function validateAll(source) {
  contracts.filesAndRegistry(source);
  contracts.noNewFunctionalEpic(source);
  contracts.traceabilityMatrix(source);
  contracts.impRange(source);
  contracts.imp254Contract(source);
  contracts.gates(source);
}

const cases = [];
const test = (name, fn) => cases.push({ name, fn });

test('PLAN-020, backlog e registry estao governados', () => contracts.filesAndRegistry(docs));
test('PLAN-020 nao cria EPIC funcional, Capability ou frontend', () => contracts.noNewFunctionalEpic(docs));
test('matriz cobre EPIC-001..EPIC-010 e fluxos F1..F6', () => contracts.traceabilityMatrix(docs));
test('backlog contem IMP-254..IMP-273 em ordem e sem dependencias futuras', () => contracts.impRange(docs));
test('IMP-254 protege range, gates, EPIC indevido e integracao no docs:test', () => contracts.imp254Contract(docs));
test('gates finais incluem a suite PLAN-020 e docs:test executa a suite', () => contracts.gates(docs));
test('contrato completo do PLAN-020 passa', () => validateAll(docs));

test('mutacao: remover IMP-273 do backlog e rejeitado', () => {
  const start = docs.backlog.indexOf('### IMP-273 -');
  const end = docs.backlog.indexOf('\n---', start);
  assert.ok(start >= 0 && end > start, 'fixture IMP-273 ausente');
  const altered = { ...docs, backlog: docs.backlog.slice(0, start) + docs.backlog.slice(end) };
  assert.throws(() => contracts.impRange(altered));
});

test('mutacao: duplicar IMP-254 e rejeitado', () => {
  const firstBlock = impBlocks(docs.backlog)[0].text;
  const altered = { ...docs, backlog: docs.backlog.replace(firstBlock, `${firstBlock}\n${firstBlock}`) };
  assert.throws(() => contracts.impRange(altered));
});

test('mutacao: dependencia futura e rejeitada', () => {
  const altered = {
    ...docs,
    backlog: docs.backlog.replace('**Dependencias:** IMP-254.', '**Dependencias:** IMP-273.'),
  };
  assert.throws(() => contracts.impRange(altered));
});

test('mutacao: remover suite PLAN-020 do docs:test e rejeitado', () => {
  const packageJson = JSON.parse(docs.packageJson);
  packageJson.scripts['docs:test'] = packageJson.scripts['docs:test']
    .replace(' && node scripts/tests/test-plan-020-contracts.js', '');
  const altered = { ...docs, packageJson: JSON.stringify(packageJson) };
  assert.throws(() => contracts.gates(altered));
});

test('mutacao: remover gate final e rejeitado', () => {
  const altered = {
    ...docs,
    plan: docs.plan.replaceAll(
      'node scripts/tests/test-plan-020-contracts.js',
      'node scripts/tests/test-plan-999-contracts.js',
    ),
  };
  assert.throws(() => contracts.gates(altered));
});

test('mutacao: emitir EPIC-011 indevido e rejeitado', () => {
  const altered = { ...docs, plan: `${docs.plan}\n\nEPIC-011 - Novo escopo funcional indevido\n` };
  assert.throws(() => contracts.noNewFunctionalEpic(altered));
});

function run() {
  let failures = 0;
  console.log('test-plan-020-contracts');
  console.log('='.repeat(50));
  for (const item of cases) {
    try {
      item.fn();
      console.log(`  [PASS] ${item.name}`);
    } catch (error) {
      failures += 1;
      console.log(`  [FAIL] ${item.name}`);
      console.log(`         ${error.message}`);
    }
  }
  console.log('='.repeat(50));
  console.log(`Resumo: ${cases.length - failures}/${cases.length} teste(s) passaram.`);
  return failures;
}

if (require.main === module) process.exit(run() ? 1 : 0);

module.exports = { FILES, contracts, docs, run };
