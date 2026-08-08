#!/usr/bin/env node
'use strict';

/**
 * Testes da família Identifiers (SPEC-002 CB-008).
 *
 *     node scripts/tests/test-identifiers.js
 *
 * Sem framework — assert e execução direta, como em test-validator.js: o
 * validador roda no pre-commit e não deve arrastar dependências.
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');

const {
  verificarIdentificadores,
  carregarRegistry,
  coletarIds,
  idDoTitulo,
  REGISTRY_REL,
} = require('../identifier-check.js');

const RAIZ = path.resolve(__dirname, '..', '..');

const casos = [];
const teste = (nome, fn) => casos.push({ nome, fn });

/**
 * Monta um repositório mínimo em diretório temporário: um Registry e os
 * documentos informados. Permite exercitar cada regra isoladamente, sem
 * depender do estado do repositório real.
 */
function repoTemporario(registry, documentos) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'idcheck-'));
  const dirReg = path.join(base, path.dirname(REGISTRY_REL));
  fs.mkdirSync(dirReg, { recursive: true });
  fs.writeFileSync(path.join(base, REGISTRY_REL), JSON.stringify(registry, null, 2));
  for (const [rel, conteudo] of Object.entries(documentos)) {
    const abs = path.join(base, rel);
    fs.mkdirSync(path.dirname(abs), { recursive: true });
    fs.writeFileSync(abs, conteudo);
  }
  return base;
}

function rodar(registry, documentos) {
  const base = repoTemporario(registry, documentos);
  const res = { errors: [], warnings: [], ok: [] };
  try {
    verificarIdentificadores({ root: base, results: res });
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
  return res;
}

const NS_BASE = {
  namespaces: {
    ADR: {
      prefixo: 'ADR', nome: 'Architectural Decision Record', classe: 'DOCUMENT',
      governadoPor: 'AMP-001', regraNumeracao: 'AMP', status: 'ACTIVE',
      validador: 'docs:validate/identifiers',
    },
    TASK: {
      prefixo: 'TASK', nome: 'Unidade operacional', classe: 'OPERATIONAL',
      governadoPor: 'git', regraNumeracao: 'max+1', status: 'ACTIVE',
      validador: 'docs:validate/identifiers',
    },
    DECISION: {
      prefixo: 'DECISION', nome: 'Nomenclatura anterior a ADR', classe: 'DOCUMENT',
      governadoPor: '—', regraNumeracao: 'nao emitir', status: 'LEGACY',
      sucessor: 'ADR', validador: 'docs:validate/identifiers',
    },
    US: {
      prefixo: 'US', nome: 'User Story', classe: 'DOCUMENT',
      governadoPor: 'sequencial', regraNumeracao: 'ultimo + 1', status: 'ACTIVE',
      validador: 'docs:validate/identifiers',
    },
  },
};

// --- Unidades ---------------------------------------------------------------

teste('coletarIds agrupa por namespace', () => {
  const ids = coletarIds('Ver ADR-018 e ADR-002, além de TASK-097.');
  assert.deepStrictEqual([...ids.get('ADR')].sort(), ['ADR-002', 'ADR-018']);
  assert.deepStrictEqual([...ids.get('TASK')], ['TASK-097']);
});

teste('coletarIds ignora siglas técnicas que casam a gramática', () => {
  const ids = coletarIds('Codificado em UTF-8 conforme RFC-123.');
  assert.ok(!ids.has('UTF'), 'UTF-8 não é identificador de governança');
  assert.ok(!ids.has('RFC'));
});

teste('idDoTitulo lê o ID emitido pelo documento', () => {
  assert.deepStrictEqual(idDoTitulo('# ADR-018: Identidade externa\n\ntexto'), {
    ns: 'ADR', numero: 18, id: 'ADR-018',
  });
});

teste('idDoTitulo devolve null quando o H1 não traz ID', () => {
  assert.strictEqual(idDoTitulo('# Relatório de alinhamento\n\ntexto'), null);
});

teste('carregarRegistry devolve null quando o arquivo não existe', () => {
  assert.strictEqual(carregarRegistry(os.tmpdir()), null);
});

// --- CB-002: namespace inexistente ------------------------------------------

teste('CB-002: namespace ausente do Registry é ERRO (regra 5.2)', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nVer XPTO-001.' });
  assert.ok(
    res.errors.some((e) => e.includes('XPTO') && e.includes('ausente do Registry')),
    'esperava erro de namespace desconhecido, obtive:\n' + res.errors.join('\n')
  );
});

teste('CB-002: namespace registrado não gera erro', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nVer TASK-097.' });
  assert.strictEqual(res.errors.length, 0, res.errors.join('\n'));
});

// --- CB-003: emissão em namespace LEGACY ------------------------------------

teste('CB-003: emitir novo ID em namespace LEGACY é ERRO (regra 5.3)', () => {
  const res = rodar(NS_BASE, { 'docs/nova.md': '# DECISION-002: nova decisão\n\ntexto' });
  assert.ok(
    res.errors.some((e) => e.includes('DECISION-002') && e.includes('LEGACY')),
    'esperava erro de emissão em LEGACY, obtive:\n' + res.errors.join('\n')
  );
});

teste('CB-003: o erro aponta o namespace sucessor', () => {
  const res = rodar(NS_BASE, { 'docs/nova.md': '# DECISION-002: nova\n\ntexto' });
  assert.ok(res.errors.some((e) => e.includes('ADR')), 'a mensagem deve indicar o sucessor');
});

// --- CB-004: qualificador não é colisão (AC-003) ----------------------------

teste('CB-004: TASK-092 e TASK-092-A convivem sem erro', () => {
  const res = rodar(NS_BASE, {
    'docs/x.md': '# ADR-018: ok\n\nVer TASK-092, TASK-092-A e TASK-092-B.',
  });
  assert.strictEqual(res.errors.length, 0, res.errors.join('\n'));
});

teste('CB-004: o qualificador não vira namespace novo', () => {
  const ids = coletarIds('TASK-049-fix concluída');
  assert.deepStrictEqual([...ids.keys()], ['TASK']);
  assert.deepStrictEqual([...ids.get('TASK')], ['TASK-049-fix']);
});

// --- CB-005: LEGACY referenciado é aviso ------------------------------------

teste('CB-005: citar DECISION-001 existente gera AVISO, não erro', () => {
  const res = rodar(NS_BASE, {
    'docs/x.md': '# ADR-018: ok\n\nRegistro oficial da DECISION-001 — stack.',
  });
  assert.strictEqual(res.errors.length, 0, 'citar LEGACY não deve ser erro');
  assert.ok(
    res.warnings.some((w) => w.includes('LEGACY') && w.includes('DECISION')),
    'esperava aviso de LEGACY referenciado'
  );
});

// --- Regras 5.4, 5.6, 5.7 ---------------------------------------------------

teste('regra 5.4: número com menos de 3 dígitos gera aviso', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nVer ADR-1 antiga.' });
  assert.ok(res.warnings.some((w) => w.includes('gramática') && w.includes('ADR-1')));
});

teste('regra 5.4: padrão glob (DOMAIN-02*) não é tratado como identificador', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      DOMAIN: {
        prefixo: 'DOMAIN', nome: 'Dominio', classe: 'DOCUMENT',
        governadoPor: 'sequencial', regraNumeracao: 'ultimo + 1', status: 'ACTIVE',
        validador: 'docs:validate/identifiers',
      },
    },
  };
  const res = rodar(registry, { 'docs/x.md': '# ADR-018: ok\n\nArquivos `DOMAIN-02*.md`.' });
  assert.ok(
    !res.warnings.some((w) => w.includes('gramática')),
    'glob não deve gerar aviso de gramática: ' + res.warnings.join('\n')
  );
});

teste('regra 5.6: namespace registrado e não usado gera aviso', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nsem outras citações' });
  assert.ok(res.warnings.some((w) => w.includes('nenhum documento utiliza')));
});

teste('regra 5.7: buraco na sequência de namespace sequencial gera aviso', () => {
  const res = rodar(NS_BASE, {
    'docs/a.md': '# US-001: primeira\n\ntexto',
    'docs/c.md': '# US-003: terceira\n\ntexto',
  });
  assert.ok(
    res.warnings.some((w) => w.includes('US') && w.includes('002')),
    'esperava aviso do número 002 ausente'
  );
});

teste('regra 5.7 não se aplica a namespace governado pelo Git', () => {
  const res = rodar(NS_BASE, {
    'docs/a.md': '# TASK-001: primeira\n\ntexto',
    'docs/c.md': '# TASK-099: nonagésima nona\n\ntexto',
  });
  assert.ok(
    !res.warnings.some((w) => w.startsWith('TASK:') && w.includes('ausente na sequência')),
    'TASK é governada pelo Git (DA-098-001), não pela sequência de documentos'
  );
});

// --- Registry real ----------------------------------------------------------

teste('CB-001/CB-006: o Registry real declara os seis campos em todo namespace', () => {
  const reg = carregarRegistry(RAIZ);
  assert.ok(reg && !reg.__erro, 'Registry deve existir e ser JSON válido');
  const obrigatorios = ['prefixo', 'nome', 'classe', 'governadoPor', 'regraNumeracao', 'status', 'validador'];
  for (const [nome, cfg] of Object.entries(reg.namespaces)) {
    for (const campo of obrigatorios) {
      assert.ok(campo in cfg, `namespace ${nome} não declara "${campo}" (DA-098-005)`);
    }
  }
  assert.ok(Object.keys(reg.namespaces).length >= 24, 'esperava ao menos os 24 namespaces inventariados');
});

teste('o Registry real marca TASK como governada pelo Git (DA-098-001)', () => {
  const reg = carregarRegistry(RAIZ);
  assert.strictEqual(reg.namespaces.TASK.governadoPor, 'git');
});

teste('o Registry real delega ADR ao AMP-001 (DA-098-002)', () => {
  const reg = carregarRegistry(RAIZ);
  assert.strictEqual(reg.namespaces.ADR.governadoPor, 'AMP-001');
  assert.ok(!('ultimo' in reg.namespaces.ADR), 'o Registry não deve manter contador de ADR');
});

teste('o Registry real marca DECISION como LEGACY (DA-098-004)', () => {
  const reg = carregarRegistry(RAIZ);
  assert.strictEqual(reg.namespaces.DECISION.status, 'LEGACY');
  assert.strictEqual(reg.namespaces.DECISION.sucessor, 'ADR');
});

teste('CB-007: o repositório real passa sem erros de identificador', () => {
  const res = { errors: [], warnings: [], ok: [] };
  verificarIdentificadores({ root: RAIZ, results: res });
  assert.strictEqual(res.errors.length, 0, 'erros no repositório real:\n' + res.errors.join('\n'));
});

// --- Execução ---------------------------------------------------------------

let falhas = 0;
console.log('test-identifiers — SPEC-002');
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
