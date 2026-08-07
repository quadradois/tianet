#!/usr/bin/env node
'use strict';

/**
 * Testes do validador de consistência arquitetural (SPEC-001 CA-007).
 *
 * O validador bloqueia commits: é software de produção e precisa de proteção
 * contra regressão. Sem framework — apenas `assert` e execução direta, para não
 * introduzir dependência num passo que roda no pre-commit.
 *
 *     node scripts/tests/test-validator.js
 */

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const {
  normalizarCaminho,
  recursoDe,
  extrairEndpoints,
  secaoApi,
  blocosImp,
  extrairRotasDoCodigo,
  compararPlanoEBacklog,
  compararCodigosHttp,
} = require('../contract-check.js');

const RAIZ = path.resolve(__dirname, '..', '..');
const FIXTURES = path.join(__dirname, 'fixtures');

const casos = [];
const teste = (nome, fn) => casos.push({ nome, fn });

const doc = (arquivo) => ({
  rel: `fixtures/${arquivo}`,
  texto: fs.readFileSync(path.join(FIXTURES, arquivo), 'utf8'),
});

const doGit = (commit, caminho) => ({
  rel: `${commit}:${path.basename(caminho)}`,
  texto: execSync(`git show ${commit}:${caminho}`, {
    encoding: 'utf8',
    cwd: RAIZ,
    maxBuffer: 1e7,
  }),
});

const comparar = (plano, backlog) => {
  const res = { errors: [], warnings: [] };
  compararPlanoEBacklog(plano, backlog, res);
  return res;
};

// --- Unidades de extração -------------------------------------------------

teste('normalizarCaminho reduz qualquer placeholder a {}', () => {
  assert.strictEqual(normalizarCaminho('/devedores/{id}'), '/devedores/{}');
  assert.strictEqual(normalizarCaminho('/devedores/{devedor_id}'), '/devedores/{}');
  assert.strictEqual(normalizarCaminho('/a/{x}/b/{y}'), '/a/{}/b/{}');
});

teste('normalizarCaminho descarta query string e barra final', () => {
  assert.strictEqual(normalizarCaminho('/devedores?documento={cpf}'), '/devedores');
  assert.strictEqual(normalizarCaminho('/devedores/'), '/devedores');
});

teste('recursoDe ignora placeholders e devolve o último segmento nomeado', () => {
  assert.strictEqual(recursoDe('/carteiras/{}/devedores/{}'), 'devedores');
  assert.strictEqual(recursoDe('/carteiras/{}/devedores/{}/inativar'), 'inativar');
});

teste('extrairEndpoints aceita crase entre método e caminho', () => {
  const semCrase = extrairEndpoints('- `GET /credit/devedores/{id}` — consulta');
  const comCrase = extrairEndpoints('- **Objetivo:** GET `/credit/devedores/{id}` (US-021)');
  assert.deepStrictEqual([...semCrase.keys()], [...comCrase.keys()]);
});

teste('secaoApi isola a seção e para no próximo cabeçalho', () => {
  const s = secaoApi(doc('plan-ok.md').texto);
  assert.ok(s.includes('/credit/carteiras/{carteira_id}/devedores'));
  assert.ok(!s.includes('Estratégia de Testes'));
});

teste('blocosImp separa cada IMP', () => {
  const b = blocosImp(doc('plan-exec-ok.md').texto);
  assert.deepStrictEqual(b.map((x) => x.id), ['IMP-900', 'IMP-901', 'IMP-902']);
});

// --- CA-003: placeholder ---------------------------------------------------

teste('CA-003: diferença apenas de placeholder não é divergência', () => {
  const a = extrairEndpoints('- `GET /credit/devedores/{id}`');
  const b = extrairEndpoints('- `GET /credit/devedores/{devedor_id}`');
  assert.deepStrictEqual([...a.keys()], [...b.keys()]);
});

// --- CA-004: prefixo -------------------------------------------------------

teste('CA-004: bounded context divergente é detectado', () => {
  const res = comparar(doc('plan-divergente.md'), doc('plan-exec-ok.md'));
  assert.ok(
    res.errors.some((e) => e.includes('Bounded context divergente')),
    'esperava erro de bounded context, obtive:\n' + res.errors.join('\n')
  );
});

teste('prefixo omitido no backlog não é divergência (CA-002)', () => {
  const res = comparar(doc('plan-ok.md'), doc('plan-exec-ok.md'));
  assert.strictEqual(
    res.errors.length,
    0,
    'esperava zero erros, obtive:\n' + res.errors.join('\n')
  );
});

// --- CA-005 / CA-006: falsos positivos -------------------------------------

teste('CA-005: rota citada só no Histórico de Versões é ignorada', () => {
  const eps = extrairEndpoints(doc('plan-ok.md').texto);
  const chaves = [...eps.keys()].join(' ');
  assert.ok(
    !chaves.includes('GET /devedores/{}'),
    'a rota do histórico vazou para a extração: ' + chaves
  );
});

teste('CA-006: fragmento em crase sem método é ignorado', () => {
  const eps = extrairEndpoints('- POST `/x/{id}/inativar` e `/reativar` (US-025/026)');
  assert.deepStrictEqual([...eps.keys()], ['POST /x/{}/inativar']);
});

teste('CA-006: bloco de citação (>) não declara endpoint', () => {
  const eps = extrairEndpoints('> Nota: nenhuma rota oficial em GET /devedores/{id}.');
  assert.strictEqual(eps.size, 0);
});

teste('linha de tabela não declara endpoint', () => {
  const eps = extrairEndpoints('| 1.1.0 | 07/08 | rotas de GET /devedores/{id} corrigidas |');
  assert.strictEqual(eps.size, 0);
});

// --- Regras 1.1 a 1.3 ------------------------------------------------------

teste('regra 1.2: forma estrutural distinta no mesmo recurso é erro', () => {
  const res = comparar(doc('plan-ok.md'), doc('plan-exec-divergente.md'));
  assert.ok(
    res.errors.some((e) => e.includes('Contrato HTTP inconsistente') && e.includes('devedores')),
    'esperava erro de contrato inconsistente, obtive:\n' + res.errors.join('\n')
  );
});

teste('regra 1.3: endpoint no backlog ausente do plano é erro (bidirecional)', () => {
  const res = comparar(doc('plan-ok.md'), doc('plan-exec-divergente.md'));
  assert.ok(
    res.errors.some((e) => e.includes('DELETE')),
    'esperava erro para o DELETE fora do plano, obtive:\n' + res.errors.join('\n')
  );
});

teste('direção plano→backlog permanece aviso, não erro', () => {
  const res = comparar(doc('plan-ok.md'), doc('plan-exec-divergente.md'));
  assert.ok(res.warnings.some((w) => w.includes('sem IMP correspondente')));
});

// --- Fase 3: códigos HTTP --------------------------------------------------

teste('Fase 3: código no backlog ausente do plano é erro', () => {
  const plano = { rel: 'p', texto: '# 6. API\n\n- `GET /x` (200);\n\nErros: 404.' };
  const backlog = { rel: 'b', texto: '## IMP-001 — X\n\n- **Objetivo:** GET `/x` (200; 409).' };
  const res = { errors: [], warnings: [] };
  compararCodigosHttp(plano, backlog, res);
  assert.ok(res.errors.some((e) => e.includes('409')));
});

// --- Fase 2: extração do código -------------------------------------------

teste('Fase 2: decoradores são lidos com o prefixo do APIRouter', () => {
  const arquivo = path.join(RAIZ, 'src', 'emprestimo', 'presentation', 'api', 'devedores_routes.py');
  if (!fs.existsSync(arquivo)) return; // ambiente sem o código-fonte
  const rotas = extrairRotasDoCodigo(arquivo);
  assert.ok(rotas.size >= 7, `esperava ao menos 7 rotas, obtive ${rotas.size}`);
  for (const ep of rotas.values()) {
    assert.ok(
      ep.caminho.startsWith('/credit/'),
      `prefixo do APIRouter não aplicado em ${ep.caminho}`
    );
  }
});

// --- CA-001 / CA-002: o caso real ------------------------------------------

const PLANO = 'docs/implementation/plans/PLAN-003-epic-002-cadastro-de-devedores.md';
const BACKLOG = 'docs/implementation/backlogs/PLAN-003-execution-backlog.md';

teste('CA-001: o commit 256a99b (origem da DR-001) falha', () => {
  const res = comparar(doGit('256a99b', PLANO), doGit('256a99b', BACKLOG));
  assert.ok(
    res.errors.length > 0,
    'o validador não detectou a divergência que originou a DR-001'
  );
});

teste('CA-002: o HEAD atual passa', () => {
  const res = comparar(doGit('HEAD', PLANO), doGit('HEAD', BACKLOG));
  assert.strictEqual(
    res.errors.length,
    0,
    'falso positivo no HEAD:\n' + res.errors.join('\n')
  );
});

// --- Execução --------------------------------------------------------------

let falhas = 0;
console.log('test-validator — SPEC-001');
console.log('='.repeat(50));
for (const { nome, fn } of casos) {
  try {
    fn();
    console.log(`  [PASS] ${nome}`);
  } catch (e) {
    falhas++;
    console.log(`  [FAIL] ${nome}`);
    console.log(`         ${e.message.split('\n').join('\n         ')}`);
  }
}
console.log('='.repeat(50));
console.log(`Resumo: ${casos.length - falhas}/${casos.length} teste(s) passaram.`);
process.exit(falhas ? 1 : 0);
