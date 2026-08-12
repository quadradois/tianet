#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');

const FILES = {
  discovery: 'docs/audits/discoveries/EPIC-009-configuracoes-financeiras-calendario-operacional-discovery.md',
  product009: 'docs/product/credit/capabilities/PRODUCT-009-administrar-configuracoes-financeiras.md',
  epic: 'docs/product/credit/epics/EPIC-009-configuracoes-financeiras-calendario-operacional.md',
  feature037: 'docs/product/credit/features/FEATURE-037-administrar-modalidades-financeiras.md',
  feature038: 'docs/product/credit/features/FEATURE-038-parametrizar-politicas-financeiras.md',
  feature039: 'docs/product/credit/features/FEATURE-039-administrar-calendario-financeiro-operacional.md',
  feature040: 'docs/product/credit/features/FEATURE-040-gerir-vigencias-configuracoes-financeiras.md',
  feature041: 'docs/product/credit/features/FEATURE-041-consultar-capturar-configuracao-financeira.md',
  us099: 'docs/product/credit/user-stories/US-099-definir-modalidade-financeira-permitida.md',
  us100: 'docs/product/credit/user-stories/US-100-validar-modalidade-por-tenant-carteira.md',
  us101: 'docs/product/credit/user-stories/US-101-criar-configuracao-financeira-rascunho.md',
  us102: 'docs/product/credit/user-stories/US-102-validar-parametros-financeiros-permitidos.md',
  us103: 'docs/product/credit/user-stories/US-103-administrar-calendario-financeiro.md',
  us104: 'docs/product/credit/user-stories/US-104-resolver-periodo-por-data-referencia.md',
  us105: 'docs/product/credit/user-stories/US-105-aprovar-configuracao-financeira.md',
  us106: 'docs/product/credit/user-stories/US-106-programar-ativacao-configuracao-financeira.md',
  us107: 'docs/product/credit/user-stories/US-107-ativar-substituir-configuracao-sem-retroatividade.md',
  us108: 'docs/product/credit/user-stories/US-108-auditar-historico-configuracao-financeira.md',
  us109: 'docs/product/credit/user-stories/US-109-consultar-configuracao-vigente-data-referencia.md',
  us110: 'docs/product/credit/user-stories/US-110-capturar-snapshot-configuracao-contratual.md',
  us111: 'docs/product/credit/user-stories/US-111-impedir-regra-financeira-livre-apis.md',
  us112: 'docs/product/credit/user-stories/US-112-impedir-calculo-financeiro-configuracoes.md',
  plan: 'docs/implementation/plans/PLAN-017-epic-009-configuracoes-financeiras-calendario-operacional.md',
  backlog: 'docs/implementation/backlogs/PLAN-017-execution-backlog.md',
  registry: 'docs/governance/registry/identifier-registry.json',
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
      if (key === 'registry') continue;
      const esperado = key === 'discovery' ? 'EPIC-009' : path.basename(rel).match(/^[A-Z]+-\d{3}/)[0];
      assert.ok(source[key].startsWith(`# ${esperado}`), `${rel}: H1 nao declara ${esperado}`);
    }
    assertTexto(source.product009, 'EPIC-009', 'PRODUCT-009');
    for (const feature of ['FEATURE-037', 'FEATURE-038', 'FEATURE-039', 'FEATURE-040', 'FEATURE-041']) {
      assertTexto(source.epic, feature, 'EPIC-009');
    }
    const rastreio = {
      feature037: 'PRODUCT-009', feature038: 'PRODUCT-009', feature039: 'PRODUCT-009',
      feature040: 'PRODUCT-009', feature041: 'PRODUCT-009',
      us099: 'FEATURE-037', us100: 'FEATURE-037',
      us101: 'FEATURE-038', us102: 'FEATURE-038',
      us103: 'FEATURE-039', us104: 'FEATURE-039',
      us105: 'FEATURE-040', us106: 'FEATURE-040', us107: 'FEATURE-040', us108: 'FEATURE-040',
      us109: 'FEATURE-041', us110: 'FEATURE-041', us111: 'FEATURE-041', us112: 'FEATURE-041',
    };
    for (const [key, parent] of Object.entries(rastreio)) assertTexto(source[key], parent, key);
    for (const us of ['US-099', 'US-100']) assertTexto(source.feature037, us, 'FEATURE-037');
    for (const us of ['US-101', 'US-102']) assertTexto(source.feature038, us, 'FEATURE-038');
    for (const us of ['US-103', 'US-104']) assertTexto(source.feature039, us, 'FEATURE-039');
    for (const us of ['US-105', 'US-106', 'US-107', 'US-108']) assertTexto(source.feature040, us, 'FEATURE-040');
    for (const us of ['US-109', 'US-110', 'US-111', 'US-112']) assertTexto(source.feature041, us, 'FEATURE-041');
  },

  registry(source) {
    const registry = JSON.parse(source.registry);
    assert.ok(registry.namespaces.PRODUCT.ultimo >= 9, 'Registry PRODUCT deve incluir PRODUCT-009');
    assert.ok(registry.namespaces.EPIC.ultimo >= 9, 'Registry EPIC deve incluir EPIC-009');
    assert.ok(registry.namespaces.FEATURE.ultimo >= 41, 'Registry FEATURE deve incluir FEATURE-041');
    assert.ok(registry.namespaces.US.ultimo >= 112, 'Registry US deve incluir US-112');
    assert.ok(registry.namespaces.PLAN.ultimo >= 17, 'Registry PLAN deve incluir PLAN-017');
  },

  planBacklog(source) {
    assertTexto(source.plan, 'PLAN-017', 'PLAN');
    assertTexto(source.backlog, 'PLAN-017-EXEC', 'PLAN-017-EXEC');
    for (let id = 201; id <= 224; id += 1) assertTexto(source.backlog, `IMP-${id}`, 'IMP sequence');
    assertTexto(source.backlog, 'IMP-201 - Criar suites documentais e contratuais do EPIC-009', 'IMP-201');
    assertTexto(source.backlog, 'IMP-224 - Recertificar EPIC-009 com suite completa', 'IMP-224');
    assertTexto(source.backlog, 'suites antes de codigo', 'PLAN-017-EXEC history');
    for (const cmd of [
      'uv run pytest -q',
      'uv run ruff check .',
      'uv run black --check .',
      'uv run mypy src tests',
      'npm run docs:validate',
      'npm run docs:test',
      'npm run quality:migrations',
    ]) {
      assertTexto(source.plan, cmd, 'PLAN-017 gates');
      assertTexto(source.backlog, cmd, 'PLAN-017-EXEC gates');
    }
  },

  boundary(source) {
    for (const key of ['discovery', 'product009', 'epic', 'plan']) {
      assertTexto(source[key], 'Motor Financeiro', key);
      assertTexto(source[key], 'calculo', key);
    }
    assertUnidade(source.discovery, ['Configuracoes', 'parametriza', 'Motor calcula'], 'DA-901');
    assertUnidade(source.plan, ['Configuracoes parametriza', 'Motor calcula'], 'PLAN D1');
    assertUnidade(source.plan, ['Configuracoes nao chama o Motor', 'Motor nao consulta Configuracoes diretamente'], 'PLAN D2');
    assertUnidade(source.us112, ['Configuracoes nao chama Motor', 'antecipar saldo ou memoria'], 'US-112');
    assertUnidade(source.backlog, ['nao ha calculo financeiro fora do Motor', 'chamada direta Configuracoes -> Motor'], 'IMP-223');
  },

  snapshots(source) {
    for (const key of ['discovery', 'plan', 'backlog']) {
      assertTexto(source[key], 'ConfiguracaoFinanceiraVigenteV1', key);
      assertTexto(source[key], 'SnapshotConfiguracaoContratualV1', key);
    }
    assertUnidade(source.discovery, ['campos materiais', 'exceto `consultada_em`'], 'Discovery snapshot');
    assertUnidade(source.feature041, ['snapshot exclui `consultada_em`', '`capturado_em`'], 'FEATURE-041 snapshot');
    assertUnidade(source.us110, ['exceto', '`consultada_em`'], 'US-110 sem consultada_em');
    assertUnidade(source.us110, ['`capturado_em`', 'autor', 'motivo', 'origem', 'versao', 'hash'], 'US-110 snapshot metadata');
    assertUnidade(source.plan, ['snapshots imutaveis', 'origem', 'versao', '`capturado_em`', 'hash'], 'PLAN gates snapshot');
    assertUnidade(source.backlog, ['snapshot preserva origem', 'versao', '`capturado_em`'], 'IMP-207 snapshot');
  },

  statesAndHttp(source) {
    for (const state of ['rascunho', 'ativa', 'programada', 'substituida', 'inativa']) {
      assertTexto(source.discovery, state, `Discovery estado ${state}`);
      assertTexto(source.backlog, state, `Backlog estado ${state}`);
    }
    assertUnidade(source.epic, ['rascunho', 'ativa', 'programada'], 'EPIC estados consumiveis');
    assertUnidade(source.us109, ['ausencia de configuracao aplicavel', '`404`'], 'US-109 404');
    assertUnidade(source.us109, ['conflito de vigencia', '`409`'], 'US-109 409');
    assertUnidade(source.us104, ['ausencia de calendario aplicavel', '`404`'], 'US-104 404');
    assertUnidade(source.us104, ['conflito de calendario aplicavel', '`409`'], 'US-104 409');
    for (const status of ['`400`', '`401`', '`403`', '`404`', '`409`']) assertTexto(source.plan, status, 'PLAN HTTP');
    assertUnidade(source.backlog, ['payload malformado', '400', 'RBAC responde 401/403'], 'IMP-221 HTTP');
  },

  guardrails(source) {
    assertUnidade(source.us111, ['impedir regra financeira livre', 'APIs consumidoras'], 'US-111');
    assertUnidade(source.us112, ['impedir calculo financeiro definitivo', 'Configuracoes'], 'US-112');
    assertUnidade(source.plan, ['sem regra financeira livre em APIs consumidoras'], 'PLAN guardrail regra livre');
    assertUnidade(source.plan, ['sem `float` monetario'], 'PLAN guardrail float');
    assertUnidade(source.backlog, ['Criar guardrail anti-calculo', 'Configuracoes Financeiras'], 'IMP-202');
    assertUnidade(source.backlog, ['guardrail contra regra financeira livre', 'APIs consumidoras'], 'IMP-203');
  },
};

const cases = [];
const test = (name, fn) => cases.push({ name, fn });

test('matriz completa e rastreabilidade Product -> EPIC -> Features -> US -> PLAN', () => contracts.hierarchy(docs));
test('registry governa IDs PRODUCT/EPIC/FEATURE/US/PLAN emitidos', () => contracts.registry(docs));
test('PLAN-017 e backlog declaram IMP-201..IMP-224 e gates oficiais', () => contracts.planBacklog(docs));
test('fronteira Configuracoes parametriza e Motor calcula permanece bloqueante', () => contracts.boundary(docs));
test('snapshot contratual exclui consultada_em e preserva capturado_em/hash', () => contracts.snapshots(docs));
test('estados, vigencia e contratos HTTP 400/401/403/404/409 ficam preservados', () => contracts.statesAndHttp(docs));
test('guardrails anti-calculo, anti-float e anti-regra livre estao no plano', () => contracts.guardrails(docs));

test('mutacao: remover FEATURE-041 do Epic e rejeitado', () => {
  const altered = mutar(docs, 'epic', 'FEATURE-041 - Consultar e Capturar Configuracao Financeira', 'FEATURE-999 - Ausente');
  assert.throws(() => contracts.hierarchy(altered));
});

test('mutacao: reduzir PLAN ultimo no registry e rejeitado', () => {
  const registry = JSON.parse(docs.registry);
  registry.namespaces.PLAN.ultimo = 16;
  const altered = {
    ...docs,
    registry: JSON.stringify(registry),
  };
  assert.throws(() => contracts.registry(altered));
});

test('mutacao: permitir chamada direta Configuracoes -> Motor e rejeitado', () => {
  const altered = mutar(docs, 'plan', 'Configuracoes nao chama o Motor', 'Configuracoes chama o Motor');
  assert.throws(() => contracts.boundary(altered));
});

test('mutacao: incluir consultada_em no snapshot e rejeitado', () => {
  const altered = mutar(docs, 'us110', 'exceto\n  `consultada_em`', 'incluindo\n  `consultada_em`');
  assert.throws(() => contracts.snapshots(altered));
});

test('mutacao: trocar 409 de conflito de vigencia por 400 e rejeitado', () => {
  const altered = mutar(docs, 'us109', 'conflito de vigencia retorna `409`', 'conflito de vigencia retorna `400`');
  assert.throws(() => contracts.statesAndHttp(altered));
});

test('mutacao: remover guardrail anti-regra livre do PLAN e rejeitado', () => {
  const altered = mutar(docs, 'plan', 'sem regra financeira livre em APIs consumidoras', 'com regra financeira livre em APIs consumidoras');
  assert.throws(() => contracts.guardrails(altered));
});

function run() {
  let failures = 0;
  console.log('test-epic-009-contracts');
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
