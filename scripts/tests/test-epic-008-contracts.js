#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');

const FILES = {
  discovery: 'docs/audits/discoveries/EPIC-008-fundacao-operacional-observabilidade-discovery.md',
  product001: 'docs/product/platform/capabilities/PRODUCT-001-administrar-plataforma.md',
  epic: 'docs/product/platform/epics/EPIC-008-fundacao-operacional-observabilidade.md',
  feature032: 'docs/product/platform/features/FEATURE-032-automatizar-pipeline-de-qualidade.md',
  feature033: 'docs/product/platform/features/FEATURE-033-validar-saude-operacional-backend.md',
  feature034: 'docs/product/platform/features/FEATURE-034-rastrear-requisicoes-correlation-id.md',
  feature035: 'docs/product/platform/features/FEATURE-035-padronizar-logs-erros-tecnicos.md',
  feature036: 'docs/product/platform/features/FEATURE-036-preparar-eventos-internos-projections.md',
  us089: 'docs/product/platform/user-stories/US-089-executar-gates-oficiais-pr-master.md',
  us090: 'docs/product/platform/user-stories/US-090-validar-migrations-forma-reproduzivel.md',
  us091: 'docs/product/platform/user-stories/US-091-consultar-healthcheck-real.md',
  us092: 'docs/product/platform/user-stories/US-092-impedir-vazamento-healthcheck.md',
  us093: 'docs/product/platform/user-stories/US-093-propagar-correlation-id-http.md',
  us094: 'docs/product/platform/user-stories/US-094-correlacionar-erros-tecnicos.md',
  us095: 'docs/product/platform/user-stories/US-095-registrar-logs-estruturados-seguros.md',
  us096: 'docs/product/platform/user-stories/US-096-operar-falhas-runbook-minimo.md',
  us097: 'docs/product/platform/user-stories/US-097-definir-contrato-inicial-eventos-internos.md',
  us098: 'docs/product/platform/user-stories/US-098-proteger-projections-verdade-paralela.md',
  adr005: 'docs/architecture/adrs/ADR-005-event-bus-interno-eventos-dominio.md',
  adr015: 'docs/architecture/adrs/ADR-015-ci-cd-gates-qualidade.md',
  adr016: 'docs/architecture/adrs/ADR-016-observability-logging-correlation-id.md',
  plan: 'docs/implementation/plans/PLAN-015-epic-008-fundacao-operacional-observabilidade.md',
  backlog: 'docs/implementation/backlogs/PLAN-015-execution-backlog.md',
  workflow: '.github/workflows/quality.yml',
  runbookQuality: 'docs/operations/quality-gates-and-migrations.md',
};

const docs = Object.fromEntries(Object.entries(FILES).map(([key, rel]) => [key, read(rel)]));

function unidades(doc) {
  const resultado = [];
  let atual = '';
  const flush = () => {
    if (atual.trim()) resultado.push(atual.replace(/\s+/g, ' ').trim());
    atual = '';
  };
  for (const raw of doc.replace(/\r/g, '').split('\n')) {
    const linha = raw.trim();
    if (!linha) {
      flush();
      continue;
    }
    if (/^(#{1,6}\s|---$|- |\|)/.test(linha)) flush();
    atual = atual ? `${atual} ${linha}` : linha;
    if (/^\|/.test(linha)) flush();
  }
  flush();
  return resultado;
}

function assertTexto(doc, texto, contexto) {
  assert.ok(doc.includes(texto), `${contexto}: contrato ausente: ${texto}`);
}

function assertUnidade(doc, fragmentos, contexto) {
  const encontrada = unidades(doc).some((unidade) => fragmentos.every((item) => unidade.includes(item)));
  assert.ok(encontrada, `${contexto}: fragmentos fora da mesma clausula: ${fragmentos.join(' + ')}`);
}

function mutar(base, chave, origem, destino) {
  assert.ok(base[chave].includes(origem), `fixture de mutacao ausente em ${chave}: ${origem}`);
  return { ...base, [chave]: base[chave].replace(origem, destino) };
}

const contracts = {
  hierarchy(source) {
    assert.strictEqual(Object.keys(source).length, 25, 'a matriz deve conter 25 artefatos');
    for (const [key, rel] of Object.entries(FILES)) {
      if (['workflow', 'runbookQuality'].includes(key)) continue;
      const esperado = key === 'discovery' ? 'EPIC-008' : path.basename(rel).match(/^[A-Z]+-\d{3}/)[0];
      assert.ok(source[key].startsWith(`# ${esperado}`), `${rel}: H1 nao declara ${esperado}`);
    }
    for (const feature of ['FEATURE-032', 'FEATURE-033', 'FEATURE-034', 'FEATURE-035', 'FEATURE-036']) {
      assertTexto(source.epic, feature, 'EPIC-008');
    }
    assertTexto(source.product001, 'EPIC-008', 'PRODUCT-001');
    const rastreio = {
      feature032: 'EPIC-008', feature033: 'EPIC-008', feature034: 'EPIC-008',
      feature035: 'EPIC-008', feature036: 'EPIC-008',
      us089: 'FEATURE-032', us090: 'FEATURE-032',
      us091: 'FEATURE-033', us092: 'FEATURE-033',
      us093: 'FEATURE-034', us094: 'FEATURE-034',
      us095: 'FEATURE-035', us096: 'FEATURE-035',
      us097: 'FEATURE-036', us098: 'FEATURE-036',
    };
    for (const [key, parent] of Object.entries(rastreio)) assertTexto(source[key], parent, key);
  },

  gates(source) {
    for (const cmd of [
      'uv run pytest -q',
      'uv run ruff check .',
      'uv run black --check .',
      'uv run mypy src tests',
      'npm run docs:validate',
      'npm run docs:test',
      'npm run quality:migrations',
    ]) {
      assertTexto(source.plan, cmd, 'PLAN-015 gates');
      assertTexto(source.backlog, cmd, 'PLAN-015-EXEC gates');
    }
    for (const cmd of ['uv run pytest -q', 'uv run ruff check .', 'uv run black --check .', 'uv run mypy src tests', 'npm run quality:migrations']) {
      assertTexto(source.workflow, cmd, 'quality.yml');
    }
  },

  health(source) {
    for (const key of ['discovery', 'feature033', 'us091', 'plan']) {
      assertTexto(source[key], 'healthy', key);
      assertTexto(source[key], 'degraded', key);
      assertTexto(source[key], 'unhealthy', key);
      assertTexto(source[key], '/health', key);
    }
    assertUnidade(source.us091, ['HTTP', '`200`', '`503`'], 'US-091 HTTP');
    const us092 = source.us092.toLowerCase();
    for (const term of ['segredo', 'tenant', 'usuario', 'dsn', 'token', 'stack trace']) {
      assert.ok(us092.includes(term), `US-092 sem vazamento: contrato ausente: ${term}`);
    }
  },

  correlation(source) {
    for (const key of ['feature034', 'us093', 'adr016', 'plan']) {
      assertTexto(source[key], 'X-Correlation-ID', key);
    }
    assertTexto(source.us094, 'correlation ID', 'US-094');
    assertUnidade(source.us093, ['2xx', '4xx', '5xx'], 'US-093 status classes');
    assertUnidade(source.us094, ['tecnico', 'correlation ID'], 'US-094 erro tecnico');
  },

  events(source) {
    for (const field of ['event_id', 'event_type', 'event_version', 'occurred_at', 'tenant_id', 'correlation_id', 'payload']) {
      assertTexto(source.us097, field, 'US-097 envelope');
      assertTexto(source.adr005, field, 'ADR-005 envelope');
    }
    assertUnidade(source.us098, ['origem', 'versao', 'data_referencia'], 'US-098 projection metadata');
    for (const term of ['juros', 'saldo', 'quitacao', 'amortizacao', 'Motor']) {
      assertTexto(source.us098, term, 'US-098 anti calculo');
    }
  },

  scope(source) {
    for (const forbidden of ['Scheduler', 'broker externo', 'outbox completa', 'dashboards APM externos', 'frontend']) {
      assertTexto(source.plan, forbidden, 'fora do escopo');
    }
  },
};

const cases = [];
const test = (name, fn) => cases.push({ name, fn });

test('matriz completa e rastreabilidade Product -> EPIC -> Features -> US', () => contracts.hierarchy(docs));
test('gates oficiais incluem migrations via npm', () => contracts.gates(docs));
test('healthcheck declara estados, HTTP e ausencia de vazamento', () => contracts.health(docs));
test('correlation ID cobre 2xx, 4xx e 5xx', () => contracts.correlation(docs));
test('eventos e projections possuem contrato minimo sem calculo financeiro', () => contracts.events(docs));
test('escopo exclui infraestrutura nao prevista', () => contracts.scope(docs));

test('mutacao: remover quality:migrations do CI e rejeitado', () => {
  const altered = mutar(docs, 'workflow', 'npm run quality:migrations', 'uv run python scripts/validate_migrations.py');
  assert.throws(() => contracts.gates(altered));
});

test('mutacao: health sem estado unhealthy e rejeitado', () => {
  let altered = mutar(docs, 'us091', '`degraded` ou `unhealthy`', '`degraded`');
  altered = mutar(altered, 'us091', '`degraded` ou `unhealthy`.', '`degraded`.');
  assert.throws(() => contracts.health(altered));
});

test('mutacao: correlation ID apenas em 2xx e rejeitado', () => {
  const altered = mutar(docs, 'us093', '2xx, 4xx e 5xx', '2xx');
  assert.throws(() => contracts.correlation(altered));
});

test('mutacao: payload removido do envelope e rejeitado', () => {
  const altered = mutar(docs, 'us097', 'payload', 'body');
  assert.throws(() => contracts.events(altered));
});

function run() {
  let failures = 0;
  console.log('test-epic-008-contracts');
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

module.exports = { FILES, contracts, docs, run, unidades };
